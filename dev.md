# Development Setup

## Development Cycle

**1. Setup Python environment (root directory):**
```bash
cd /path/to/chat-ui-11
uv venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
uv pip install -r requirements.txt
```

**2. Start backend (Terminal 1):**
```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
# Note: No --reload flag to avoid auto-reload issues
```

**3. Build frontend (Terminal 2):**
```bash
cd frontend
npm run build
```

**Key Points:**
- Use `uv` for faster Python package management
- Don't use `uvicorn --reload` - causes problems
- Don't use `npm run dev` - has WebSocket issues
- Use `npm run build` instead for production build
- Backend serves on port 8000, frontend builds to `/dist`

The built frontend files are served by the FastAPI backend, so you only need the uvicorn server running.