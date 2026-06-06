# ============================================================
# Gonanku - Migrate skema ke Supabase / Postgres production
# Pakai SEKALI saat setup awal, lalu setiap ada migration baru.
# ============================================================
# Pemakaian:
#   .\migrate.ps1
# Membaca DATABASE_URL dari .env.production.

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "==> Gonanku Migration to Production DB" -ForegroundColor Cyan
Write-Host ""

# Validasi .env.production ada
if (-not (Test-Path ".env.production")) {
    Write-Host "ERROR: .env.production tidak ditemukan." -ForegroundColor Red
    Write-Host "  Copy .env.production.example -> .env.production, isi nilainya, lalu jalankan ulang."
    exit 1
}

# Baca DATABASE_URL dari .env.production
$DB_LINE = Get-Content .env.production | Where-Object { $_ -match "^DATABASE_URL=" } | Select-Object -First 1
if (-not $DB_LINE) {
    Write-Host "ERROR: DATABASE_URL tidak ada di .env.production" -ForegroundColor Red
    exit 1
}
$DB_URL = $DB_LINE -replace "^DATABASE_URL=", ""

if ($DB_URL -match "SUPABASE_PASSWORD|refxxxxx") {
    Write-Host "ERROR: DATABASE_URL masih placeholder. Isi nilai sebenarnya dulu." -ForegroundColor Red
    exit 1
}

Write-Host "Target DB: $($DB_URL -replace ':[^:@]+@', ':****@')" -ForegroundColor Gray
Write-Host ""

# Set env vars sementara
$env:DATABASE_URL = $DB_URL
$env:FLASK_APP = "run.py"

Write-Host "==> flask db upgrade..." -ForegroundColor Cyan
flask db upgrade
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Migrasi gagal." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "==> Selesai. Skema berhasil dibuat di Supabase." -ForegroundColor Green
Write-Host ""
Write-Host "Langkah berikutnya:"
Write-Host "  Buat akun pemilik vault:"
Write-Host "    flask buat-pengguna email@kamu.id 'Nama Kamu' kata_sandi_panjang"
Write-Host ""
