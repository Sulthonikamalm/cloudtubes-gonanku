#!/bin/bash
# ============================================================
# Gonanku - Deploy ke Google Cloud Run (Cloud Shell / Linux)
# ============================================================
# Pemakaian (di Cloud Shell):
#   ./deploy.sh
#
# Prasyarat:
#   1. gcloud sudah authenticated (Cloud Shell otomatis sudah)
#   2. .env.production di-upload ke folder yang sama dengan script ini
#   3. Project GCP sudah di-set: gcloud config set project gonanku-app
#   4. Artifact Registry "gonanku-repo" sudah dibuat (sudah ✅)
# ============================================================

set -e  # Stop kalau ada error

# ---------- KONFIGURASI ----------
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
REGION="asia-southeast1"
SERVICE="gonanku-app"
REPO="gonanku-repo"
TAG="v$(date +%Y%m%d%H%M%S)"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/gonanku:${TAG}"

echo ""
echo "============================================================"
echo "  Gonanku - Deploy ke Cloud Run"
echo "============================================================"
echo "  Project : ${PROJECT_ID}"
echo "  Region  : ${REGION}"
echo "  Service : ${SERVICE}"
echo "  Image   : ${IMAGE}"
echo ""

# Validasi project
if [ -z "${PROJECT_ID}" ]; then
    echo "ERROR: gcloud project belum di-set."
    echo "  Jalankan: gcloud config set project gonanku-app"
    exit 1
fi

# Validasi .env.production
if [ ! -f .env.production ]; then
    echo "ERROR: .env.production tidak ditemukan di folder ini."
    echo "  Upload file .env.production dari laptop ke Cloud Shell dulu."
    exit 1
fi

# ---------- BUILD ----------
echo "==> [1/3] Build image via Cloud Build (~3-5 menit)..."
gcloud builds submit --tag "${IMAGE}" --region="${REGION}"

# ---------- BANGUN ENV VARS FILE (format YAML untuk --env-vars-file) ----------
echo ""
echo "==> [2/3] Bangun env vars dari .env.production..."

ENV_FILE=$(mktemp)
# Parse .env.production -> YAML aman terhadap koma/karakter spesial
while IFS='=' read -r key value; do
    # Skip baris kosong dan komentar
    [[ -z "$key" || "$key" =~ ^# ]] && continue
    # Trim whitespace
    key=$(echo "$key" | xargs)
    value=$(echo "$value" | xargs)
    # Escape double-quote di value
    value="${value//\"/\\\"}"
    echo "${key}: \"${value}\"" >> "${ENV_FILE}"
done < .env.production

# ---------- DEPLOY ----------
echo "==> [3/3] Deploy ke Cloud Run..."
gcloud run deploy "${SERVICE}" \
    --image "${IMAGE}" \
    --region "${REGION}" \
    --platform managed \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 1 \
    --timeout 600 \
    --port 8080 \
    --concurrency 80 \
    --env-vars-file "${ENV_FILE}"

DEPLOY_EXIT=$?
rm -f "${ENV_FILE}"

if [ ${DEPLOY_EXIT} -ne 0 ]; then
    echo "ERROR: Deploy gagal."
    exit 1
fi

# ---------- INFO ----------
URL=$(gcloud run services describe "${SERVICE}" --region="${REGION}" --format="value(status.url)")

echo ""
echo "============================================================"
echo "  DEPLOY BERHASIL"
echo "============================================================"
echo "  Service URL : ${URL}"
echo "  Health      : ${URL}/health"
echo "  Login       : ${URL}/login"
echo ""
echo "Cek log realtime:"
echo "  gcloud run services logs tail ${SERVICE} --region=${REGION}"
echo ""
