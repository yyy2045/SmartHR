FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src ./src

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV DB_HOST=localhost
ENV DB_PORT=3306
ENV DB_USER=smarthr
ENV DB_PASSWORD=smarthr123
ENV DB_NAME=smarthr
ENV REDIS_HOST=localhost
ENV REDIS_PORT=6379
ENV CHROMA_HOST=localhost
ENV CHROMA_PORT=8000

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Run
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001"]