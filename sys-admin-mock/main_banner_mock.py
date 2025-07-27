# main.py
import os
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel, Field
from typing import List, Optional
from pathlib import Path

# ------------------------------------------------------------------------------
# 1. Initialize FastAPI App
# ------------------------------------------------------------------------------
app = FastAPI(
    title="System Admin Banner API",
    description="A mock API that provides system banner messages for display in the chat UI.",
    version="1.0.0",
)

# ------------------------------------------------------------------------------
# 2. Pydantic Models for Response
# ------------------------------------------------------------------------------

class BannerMessage(BaseModel):
    message: str = Field(..., description="The banner message to display")
    id: Optional[str] = Field(None, description="Unique identifier for the message")

class BannerResponse(BaseModel):
    messages: List[BannerMessage] = Field(..., description="List of banner messages to display")

# ------------------------------------------------------------------------------
# 3. Authentication Helper
# ------------------------------------------------------------------------------

def verify_api_key(x_api_key: str = Header(...)):
    """
    Simple API key verification. In a real system, this would check against
    a secure store. For the mock, we accept any non-empty key.
    """
    if not x_api_key or x_api_key.strip() == "":
        raise HTTPException(
            status_code=401,
            detail="API key is required"
        )
    # For mock purposes, accept any non-empty key
    return x_api_key

# ------------------------------------------------------------------------------
# 4. Banner Message Loading
# ------------------------------------------------------------------------------

def load_banner_messages() -> List[BannerMessage]:
    """
    Load banner messages from messages.txt file.
    Each line in the file becomes a separate banner message.
    """
    messages_file = Path(__file__).parent / "messages.txt"
    messages = []
    
    try:
        if messages_file.exists():
            with open(messages_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for i, line in enumerate(lines):
                    line = line.strip()
                    if line:  # Only add non-empty lines
                        messages.append(BannerMessage(
                            message=line,
                            id=f"banner_{i+1}"
                        ))
        else:
            # Return default message if file doesn't exist
            messages.append(BannerMessage(
                message="System status: All services operational",
                id="banner_default"
            ))
    except Exception as e:
        print(f"Error loading banner messages: {e}")
        # Return error message as banner
        messages.append(BannerMessage(
            message="Error loading system messages",
            id="banner_error"
        ))
    
    return messages

# ------------------------------------------------------------------------------
# 5. API Endpoints
# ------------------------------------------------------------------------------

@app.get(
    "/banner",
    response_model=BannerResponse,
    summary="Get banner messages for display"
)
async def get_banner_messages(api_key: str = Depends(verify_api_key)):
    """
    Returns a list of banner messages to display at the top of the chat UI.
    Each message should be displayed as a separate full-width banner.
    
    Requires API key in X-API-Key header.
    """
    print(f"Banner request received with API key: {api_key[:10]}..." if len(api_key) > 10 else api_key)
    
    messages = load_banner_messages()
    
    print(f"Returning {len(messages)} banner messages")
    
    return BannerResponse(messages=messages)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "sys-admin-banner"}

# ------------------------------------------------------------------------------
# 6. Run the App
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    # To run this file:
    # 1. Install the necessary packages: pip install "fastapi[all]"
    # 2. Run the server: uvicorn main:app --reload --port 8002
    # 3. Open your browser to http://127.0.0.1:8002/docs to see the interactive API documentation.
    uvicorn.run(app, host="0.0.0.0", port=8002)