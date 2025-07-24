FROM fedora:latest

# Install system dependencies
RUN dnf update -y && \
    dnf install -y python3 python3-pip curl git && \
    dnf clean all

# Install uv for Python package management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Create virtual environment and install dependencies
RUN cd backend && \
    uv venv && \
    . .venv/bin/activate && \
    uv pip install -r requirements.txt

# Create logs directory
RUN mkdir -p backend/logs

# Make MCP servers executable
RUN chmod +x backend/mcp/*/main.py

# Expose port
EXPOSE 8000

# Set environment variables
ENV PYTHONPATH=/app/backend
ENV PATH="/app/backend/.venv/bin:$PATH"

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/config || exit 1

# Start the application
WORKDIR /app/backend
CMD [".venv/bin/python", "main.py"]