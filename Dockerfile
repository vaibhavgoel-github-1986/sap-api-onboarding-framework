FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (if needed for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy ONLY dependency file first (for better Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
# Using --no-cache-dir to reduce image size
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY __init__.py __main__.py agent_executor.py ./

# Expose the port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/.well-known/agent-card.json || exit 1

# Run the application
CMD ["python", "__main__.py"]
