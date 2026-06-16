# syntax=docker/dockerfile:1.7
FROM python:3.12-slim

WORKDIR /app

ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG APT_MIRROR=https://mirrors.tuna.tsinghua.edu.cn
ARG PYTORCH_INDEX_URL=https://mirror.sjtu.edu.cn/pytorch-wheels/cpu
ARG TORCH_VERSION=2.6.0+cpu
ENV PIP_INDEX_URL=${PIP_INDEX_URL}
ENV PIP_TRUSTED_HOST="pypi.tuna.tsinghua.edu.cn mirror.sjtu.edu.cn"
ENV PIP_DEFAULT_TIMEOUT=180
ENV PIP_RETRIES=10
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN sed -i "s|http://deb.debian.org/debian|${APT_MIRROR}/debian|g; s|http://deb.debian.org/debian-security|${APT_MIRROR}/debian-security|g" /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --default-timeout=180 --retries=10 \
    --index-url ${PYTORCH_INDEX_URL} \
    torch==${TORCH_VERSION}

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --default-timeout=180 --retries=10 -r requirements.txt

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
