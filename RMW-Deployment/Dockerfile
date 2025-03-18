# Start met een lichte Python image
FROM python:3.9-slim

# Werkdirectory instellen
WORKDIR /app

# Kopieer de vereisten en installeer dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopieer de rest van de app
COPY . .

# Expose de poort 9000 (optioneel, puur informatief)
EXPOSE 9000

# Start de FastAPI-app met Uvicorn op poort 9000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000"]
