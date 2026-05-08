FROM python:3.10-slim

WORKDIR /app

# Install dependencies first (layer cached unless requirements change)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY *.py .

EXPOSE 8080

# Fly.io expects the app to bind to 0.0.0.0:8080
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8080"]
