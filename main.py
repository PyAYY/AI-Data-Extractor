import base64
import os
from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
import instructor
from openai import OpenAI
from pydantic import BaseModel, Field

app = FastAPI()

# Enable CORS so your GitHub Pages domain can talk to your local API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to your actual GitHub Pages URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple API Key security (In production, validate these against your PostgreSQL/Stripe database)
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

# Placeholder master admin key & active user keys
ADMIN_KEY = os.getenv("ADMIN_KEY", "admin-secret-master-key")
VALID_USER_KEYS = {os.getenv("TEST_USER_KEY", "user-sample-key-123")}

def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key == ADMIN_KEY or api_key in VALID_USER_KEYS:
        return api_key
    raise HTTPException(status_code=403, detail="Invalid or missing API Key")

# Extraction Schema
class InvoiceData(BaseModel):
    vendor_name: str = Field(description="The name of the company issuing the invoice")
    invoice_total: float = Field(description="The final total amount charged")
    is_paid: bool = Field(description="True if the invoice indicates it has been paid")
    line_items: list[str] = Field(description="List of individual items or services billed")

# Setup Instructor with local Ollama
client = instructor.from_openai(
    OpenAI(base_url="http://localhost:11434/v1", api_key="ollama"),
    mode=instructor.Mode.JSON
)

class ExtractRequest(BaseModel):
    image_base64: str

@app.post("/api/extract", response_model=InvoiceData)
def extract_invoice(payload: ExtractRequest, api_key: str = Depends(verify_api_key)):
    try:
        response = client.chat.completions.create(
            model="qwen2.5-vl",
            response_model=InvoiceData,
            temperature=0.0,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract the vendor name, total amount, payment status, and line items from this document."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{payload.image_base64}"}}
                    ]
                }
            ]
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Administrative endpoint to generate new user keys after Stripe payment webhook triggers
@app.post("/api/admin/generate-key")
def generate_key(admin_secret: str):
    if admin_secret != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    import secrets
    new_key = f"usr_{secrets.token_hex(16)}"
    VALID_USER_KEYS.add(new_key)
    return {"status": "success", "api_key": new_key}