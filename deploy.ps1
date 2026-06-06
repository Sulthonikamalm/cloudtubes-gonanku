# ============================================================
# Gonanku - Deploy ke Google Cloud Run
# ============================================================
# Pemakaian:
#   .\deploy.ps1
#
# Prasyarat:
#   1. gcloud CLI sudah login (gcloud auth login)
#   2. Project GCP sudah dibuat dan billing aktif
#   3. .env.production sudah diisi
#   4. Artifact Registry repo "gonanku-repo" sudah dibuat
#   5. .\migrate.ps1 sudah dijalankan minimal sekali
# ============================================================

$ErrorActionPreference = "Stop"

# ---------- KONFIGURASI ----------
$PROJECT_ID  = (gcloud config get-value project 2>$null)
$REGION      = "asia-southeast1"
$SERVICE     = "gonanku-app"
$REPO        = "gonanku-repo"
$TAG         = "v$(Get-Date -Format 'yyyyMMddHHmmss')"
$IMAGE       = "$REGION-docker.pkg.dev/$PROJECT_ID/$REPO/gonanku:$TAG"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Gonanku - Deploy ke Cloud Run" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Project : $PROJECT_ID"
Write-Host "  Region  : $REGION"
Write-Host "  Service : $SERVICE"
Write-Host "  Image   : $IMAGE"
Write-Host ""

# Validasi project sudah di-set
if (-not $PROJECT_ID) {
    Write-Host "ERROR: gcloud project belum di-set." -ForegroundColor Red
    Write-Host "  Jalankan: gcloud config set project NAMA_PROJECT"
    exit 1
}

# Validasi .env.production ada
if (-not (Test-Path ".env.production")) {
    Write-Host "ERROR: .env.production tidak ditemukan." -ForegroundColor Red
    Write-Host "  Copy .env.production.example -> .env.production dan isi."
    exit 1
}

# ---------- BUILD ----------
Write-Host "==> [1/3] Build image via Cloud Build (akan upload code, tunggu ~3-5 menit)..." -ForegroundColor Cyan
gcloud builds submit --tag $IMAGE --region=$REGION
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Build gagal." -ForegroundColor Red
    exit 1
}

# ---------- ENV VARS dari .env.production ----------
Write-Host ""
Write-Host "==> [2/3] Bangun env vars dari .env.production..." -ForegroundColor Cyan

$envContent = Get-Content .env.production | Where-Object { $_ -and -not $_.StartsWith("#") -and $_.Contains("=") }
$envFile = New-TemporaryFile

# Tulis ulang ke format YAML untuk --env-vars-file (aman terhadap koma di dalam value).
"" | Out-File -FilePath $envFile -Encoding utf8
foreach ($line in $envContent) {
    $idx = $line.IndexOf("=")
    $k = $line.Substring(0, $idx).Trim()
    $v = $line.Substring($idx + 1).Trim()
    # Escape kutip ganda untuk YAML
    $v = $v -replace '"', '\"'
    "$k`: `"$v`"" | Out-File -FilePath $envFile -Encoding utf8 -Append
}

# ---------- DEPLOY ----------
Write-Host "==> [3/3] Deploy ke Cloud Run..." -ForegroundColor Cyan
gcloud run deploy $SERVICE `
    --image $IMAGE `
    --region $REGION `
    --platform managed `
    --allow-unauthenticated `
    --memory 512Mi `
    --cpu 1 `
    --min-instances 0 `
    --max-instances 1 `
    --timeout 600 `
    --port 8080 `
    --concurrency 80 `
    --env-vars-file $envFile

$deployCode = $LASTEXITCODE
Remove-Item $envFile -Force

if ($deployCode -ne 0) {
    Write-Host "ERROR: Deploy gagal." -ForegroundColor Red
    exit 1
}

# ---------- INFO ----------
$URL = (gcloud run services describe $SERVICE --region=$REGION --format="value(status.url)")

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  DEPLOY BERHASIL" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  Service URL : $URL" -ForegroundColor Yellow
Write-Host "  Health      : $URL/health" -ForegroundColor Yellow
Write-Host "  Login       : $URL/login" -ForegroundColor Yellow
Write-Host ""
Write-Host "Cek log realtime:" -ForegroundColor Gray
Write-Host "  gcloud run services logs tail $SERVICE --region=$REGION" -ForegroundColor Gray
Write-Host ""
