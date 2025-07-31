# Use Fedora as base image
FROM fedora:latest

# Set working directory
WORKDIR /app

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install system dependencies including Python and Node.js
RUN dnf update -y && dnf install -y \
    python3 \
    python3-pip \
    nodejs \
    npm \
    curl \
    && dnf clean all

# Copy and install Python dependencies first (for caching)
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy and install frontend dependencies (for caching)
COPY frontend/package*.json ./frontend/
WORKDIR /app/frontend
ENV NPM_CONFIG_CACHE=/app/.npm
RUN npm ci

# Build frontend
COPY frontend/ .
RUN npm run build

# Switch back to app directory and copy backend code
WORKDIR /app
COPY backend/ ./backend/

# Copy other necessary files
COPY llmconfig.yml .
COPY docs/ ./docs/
COPY scripts/ ./scripts/
COPY test/ ./test/

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Set environment variables
ENV PYTHONPATH=/app
ENV NODE_ENV=production

# Start the application
CMD ["python3", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]