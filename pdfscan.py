import base64
import instructor
from openai import OpenAI
from pydantic import BaseModel, Field

class InvoiceData(BaseModel):
    vendor_name: str = Field(description="The name of the company issuing the invoice")
    invoice_total: float = Field(description="The final total amount charged")
    is_paid: bool = Field(description="True if the invoice indicates it has been paid")
    line_items: list[str] = Field(description="List of individual items or services billed")

# Point the OpenAI client to Ollama's local port
client = instructor.from_openai(
    OpenAI(
        base_url="http://localhost:11434/v1", 
        api_key="ollama" # Required field, but the value is ignored by Ollama
    ),
    mode=instructor.Mode.JSON
)

def encode_image_to_base64(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

image_path = "scanned_invoice_page_1.jpg"
base64_image = encode_image_to_base64(image_path)

# Execute the request against your Ollama instance
structured_response = client.chat.completions.create(
    model="llama3.2-vision", # Ensure this matches your exact Ollama tag (e.g., qwen2.5-vl, llama3.2-vision)
    response_model=InvoiceData,
    temperature=0.0,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text", 
                    "text": "Extract the vendor name, total amount, payment status, and line items from this document."
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    }
                }
            ]
        }
    ]
)

print(f"Vendor: {structured_response.vendor_name}")
print(f"Total: ${structured_response.invoice_total}")
print(f"Paid Status: {structured_response.is_paid}")
print(f"Items: {structured_response.line_items}")