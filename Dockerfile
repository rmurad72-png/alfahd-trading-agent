# 🐆 الفهد — Docker Image for Railway
FROM python:3.11-slim

WORKDIR /app

# Install system deps (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app (forces rebuild when files change)
COPY . .

# Verify main.py exists (fails build if missing)
RUN test -f /app/main.py || (echo "ERROR: main.py not found!" && exit 1)

# Run the bot
CMD ["python", "main.py"]
