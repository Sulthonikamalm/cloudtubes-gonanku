FROM python:3.11-slim

# Hindari .pyc, log realtime, mode unbuffered.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# psycopg2-binary butuh libpq + build tools minimal; setelah install, hapus dev libs.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Install dependency lebih dulu agar layer cache efektif.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Hapus build tools setelah dependency terinstall (image lebih ringan).
RUN apt-get purge -y gcc libpq-dev \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY . .

# Cloud Run mengirim port lewat env PORT (default 8080).
ENV PORT=8080
EXPOSE 8080

# Healthcheck ringan: cek endpoint /health setiap 30 detik.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://127.0.0.1:${PORT}/health || exit 1

# 1 worker, 4 thread: hemat untuk Cloud Run instance kecil.
# Timeout 600s memberi ruang untuk bulk upload (max 15 foto × ~10s vision call).
CMD exec gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 600 run:app
