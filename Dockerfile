# Use Ubuntu as base image (better Playwright support)
FROM ubuntu:24.04

# Set working directory
WORKDIR /app

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install system dependencies including Python and Node.js
RUN apt-get update && apt-get install -y     python3     python3-pip     python3-venv     nodejs     npm     curl     hostname     sudo     && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install uv for better Python dependency management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mkdir -p /root/.local/bin
ENV PATH="/root/.local/bin:$PATH"

# Copy requirements first
COPY requirements.txt .

# Copy and install frontend dependencies (for caching)
COPY frontend/package*.json ./frontend/
WORKDIR /app/frontend
ENV NPM_CONFIG_CACHE=/app/.npm
# Install all dependencies including devDependencies needed for build
RUN npm ci --include=dev

# Build frontend
COPY frontend/ .
# build and delete the node_modules
RUN  npm run build && rm -rf node_modules

# Switch back to app directory and copy backend code
WORKDIR /app
COPY backend/ ./backend/

# Copy other necessary files
COPY backend/configfiles/llmconfig.yml ./backend/configfiles/
COPY docs/ ./docs/
COPY scripts/ ./scripts/
COPY test/ ./test/

# Create logs directory for the backend
RUN mkdir -p /app/backend/logs

# Configure sudo for appuser (needed for Playwright browser installation)
RUN echo "appuser ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

# Set up uv for appuser
RUN mkdir -p /home/appuser/.local/bin && \
    if [ -f "/root/.local/bin/uv" ]; then cp /root/.local/bin/uv /home/appuser/.local/bin/; fi && \
    mkdir -p /home/appuser/.cache && \
    chown -R appuser:appuser /home/appuser/.local /home/appuser/.cache

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Set up Python environment as appuser
ENV PATH="/home/appuser/.local/bin:$PATH"
RUN /home/appuser/.local/bin/uv python install 3.12
RUN /home/appuser/.local/bin/uv venv venv --python 3.12
ENV VIRTUAL_ENV=/app/venv
ENV PATH="/app/venv/bin:$PATH"

# Install Python dependencies using uv
RUN /home/appuser/.local/bin/uv pip install -r requirements.txt

# Expose port
EXPOSE 8000

# Set environment variables
ENV PYTHONPATH=/app
ENV NODE_ENV=production

# Start the application
CMD ["python3", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]