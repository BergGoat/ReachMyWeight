FROM python:3.9-slim

# Installeer afhankelijkheden en de Docker CLI
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    docker.io \
    ca-certificates \
    curl \
    gnupg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Installeer Python-afhankelijkheden met specifieke versies
RUN pip install --no-cache-dir fastapi==0.95.1 pydantic==1.10.8 uvicorn httpx

# Kopieer de redeploy.py naar de container
COPY redeploy.py .

# Start de redeploy-service met uvicorn op poort 8080
CMD ["uvicorn", "redeploy:app", "--host", "0.0.0.0", "--port", "8080"]
