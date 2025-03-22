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

# Installeer Python-afhankelijkheden (bijvoorbeeld FastAPI en uvicorn)
RUN pip install --no-cache-dir fastapi uvicorn

# Kopieer de redeploy.py naar de container
COPY redeploy.py .

# Start de redeploy-service met uvicorn op poort 9000
CMD ["uvicorn", "redeploy:app", "--host", "0.0.0.0", "--port", "9000"]
