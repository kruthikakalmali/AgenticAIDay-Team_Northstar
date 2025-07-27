# Use official Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy files
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run the app with uvicorn
CMD ["uvicorn", "exposefeed:app", "--host", "0.0.0.0", "--port", "8080"]
