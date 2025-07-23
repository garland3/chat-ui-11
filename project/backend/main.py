
from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import RedirectResponse
import uvicorn
import yaml
import json
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Load configurations
with open("llmconfig.yml", "r") as f:
    llm_config = yaml.safe_load(f)

with open("mcp.json", "r") as f:
    mcp_config = json.load(f)

# Middleware for authentication
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if os.getenv("DEBUG_MODE") == "true":
        request.state.user = "test@test.com"
        return await call_next(request)

    if "x-email-header" not in request.headers:
        return RedirectResponse(url="/auth")
    
    request.state.user = request.headers["x-email-header"]
    response = await call_next(request)
    return response

@app.get("/auth")
async def auth_redirect():
    return {"message": "Please authenticate through the reverse proxy."}

@app.get("/")
async def read_root():
    return {"message": "Hello, World!"}

# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Message text was: {data}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
