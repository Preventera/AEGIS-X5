FROM python:3.12-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir ".[dashboard]"

# Copy full project
COPY . .

# Expose API port
EXPOSE 4000

# Default: run the API
CMD ["uvicorn", "aegis.api.app:create_api", "--factory", "--host", "0.0.0.0", "--port", "4000"]
