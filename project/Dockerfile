FROM fedora:latest

# Install Python and uv
RUN dnf -y install python3 && \
    curl -LsSf https://astral.sh/uv/install.sh | sh

# Set up the working directory
WORKDIR /app

# Copy the backend code
COPY backend/ /app/backend/

# Install Python dependencies
RUN uv pip install --system -r backend/requirements.txt

# Copy the rest of the project
COPY . .

# Expose the port
EXPOSE 8000

# Start the application
CMD ["uv", "run", "python", "backend/main.py"]