# 🐆 الفهد — Docker Image for Railway
FROM python:3.11-slim

WORKDIR /app

# Install system deps (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends     gcc     libpq-dev     && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Run the bot
# Copy app
COPY . .

# ✅ أضف هذا السطر (لإجبار rebuild + للتأكد من وجود الملفات)
RUN ls -la /app && test -f /app/main.py

# Run the bot
CMD ["python", "main.py"]
CMD ["python", "main.py"]
