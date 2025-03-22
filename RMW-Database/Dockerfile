# Start with light version of Python
FROM python:3.9-slim

# Setup work directory
WORKDIR /app

# Copy requirements file first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code and SQL file
COPY main.py .
COPY RMW.sql .

# Create a persistent volume for the database
VOLUME /app/db

# Expose port 9200
EXPOSE 9200

# Start the FastAPI app with Uvicorn on port 9200
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9200"] 