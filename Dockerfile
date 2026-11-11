# Dockerfile
# Production Container for EcoPredict AI Platform (Case 23)

FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (including libgomp1 for LightGBM OpenMP support)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies list
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source tree
COPY . .

# Initialize and seed database if not exists
RUN python core/seeder.py && python ai/pipeline.py

EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
