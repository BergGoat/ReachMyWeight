# Start with light version of Python
FROM python:3.9-slim

# Setup work directory
WORKDIR /app

# Copy requirements file first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY main.py .

# Expose port 9000
EXPOSE 9000

# Start the FastAPI app with Uvicorn on port 9000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000"] 