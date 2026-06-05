FROM python:3.11-slim

# Hindari file .pyc dan aktifkan log langsung tampil.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependency lebih dulu agar layer cache efektif.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run mengirim port lewat env PORT (default 8080).
ENV PORT=8080
EXPOSE 8080

# 1 worker, 4 thread: hemat untuk Cloud Run instance kecil.
# Timeout 600s memberi ruang untuk bulk upload (max 15 foto × ~10s vision call).
CMD exec gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 600 run:app
