FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create necessary directories
RUN mkdir -p templates static/css

# Add template files - you should create these
COPY templates/ templates/
COPY static/ static/

EXPOSE 8000

CMD ["uvicorn", "rmw_api_frontend:app", "--host", "0.0.0.0", "--port", "8000"] 