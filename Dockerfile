FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1

# Create non-root user, install dependencies, and cleanup in a single layer
RUN groupadd -r seedshield && \
    useradd -r -g seedshield seedshield && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    libncurses5-dev \
    xclip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install package in one layer
COPY setup.py pyproject.toml README.md ./
COPY seedshield seedshield/
RUN pip install --no-cache-dir -e . && \
    chown -R seedshield:seedshield /app

USER seedshield
ENTRYPOINT ["seedshield"]