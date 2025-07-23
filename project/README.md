# Chat UI

A simple chat application with a FastAPI backend and a vanilla JavaScript frontend.

## Project Structure

- `backend/`: Contains the FastAPI application.
- `frontend/`: Contains the HTML, CSS, and JavaScript for the client-side application.
- `llmconfig.yml`: Configuration for LLMs.
- `mcp.json`: Configuration for MCP servers.
- `.env`: Environment variables.
- `Dockerfile`: For containerizing the application.

## Getting Started

### Prerequisites

- Python 3.10+
- `uv` package manager

### Installation

1. Clone the repository.
2. Navigate to the `project` directory.
3. Create a virtual environment: `uv venv`
4. Install dependencies: `uv pip install -r backend/requirements.txt`

### Running the application

1. Start the backend server: `uv run uvicorn backend.main:app --reload`
2. Open `frontend/index.html` in your web browser.

## Docker

To build and run the application with Docker, use the following commands:

```bash
docker build -t chat-ui .
docker run -p 8000:8000 chat-ui
```
