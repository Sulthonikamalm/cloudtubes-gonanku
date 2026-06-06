# 🚀 Panduan Deploy Gonanku — Cloud Run + Supabase

Tutorial lengkap dari nol sampai aplikasi jalan di production. **Total waktu: ~45 menit**, **biaya: Rp 0**.

---

## 📋 Daftar isi

1. [Yang harus kamu siapkan dulu (checklist)](#1-yang-harus-kamu-siapkan-dulu-checklist)
2. [Fase A — Setup Supabase (DB)](#2-fase-a--setup-supabase-db)
3. [Fase B — Setup Telegram Bot + Channel](#3-fase-b--setup-telegram-bot--channel)
4. [Fase C — Setup GCP Project](#4-fase-c--setup-gcp-project)
5. [Fase D — Konfigurasi `.env.production` di laptop](#5-fase-d--konfigurasi-envproduction-di-laptop)
6. [Fase E — Migrasi skema ke Supabase](#6-fase-e--migrasi-skema-ke-supabase)
7. [Fase F — Deploy ke Cloud Run](#7-fase-f--deploy-ke-cloud-run)
8. [Fase G — Verifikasi production](#8-fase-g--verifikasi-production)
9. [Troubleshooting umum](#9-troubleshooting-umum)
10. [Re-deploy setelah update code](#10-re-deploy-setelah-update-code)
11. [Cara hapus semua resource (kalau demo selesai)](#11-cara-hapus-semua-resource)

---

## 1. Yang harus kamu siapkan dulu (checklist)

Sebelum mulai, pastikan punya:

- [ ] **Akun Google** dengan billing GCP enabled (sudah punya — kamu sudah pasang budget alert Rp 100k ✅)
- [ ] **Akun Supabase** — daftar di https://supabase.com pakai Google login
- [ ] **Akun Telegram** aktif di HP
- [ ] **3 Groq API key** (sudah ada di `.env` lokal kamu)
- [ ] **gcloud CLI** terinstall di laptop — cek dengan `gcloud --version`
  - Belum punya? Download: https://cloud.google.com/sdk/docs/install
- [ ] **Python 3.11+** dan **pip** sudah terinstall (untuk migrasi DB dari laptop)

---

## 2. Fase A — Setup Supabase (DB)

### A.1 Buat project
1. Buka **https://supabase.com** → Sign in dengan Google
2. Klik **New project**
3. Isi:
   - **Name**: `gonanku`
   - **Database Password**: klik **Generate** — **SIMPAN PASSWORD INI** di tempat aman (Notepad, password manager)
   - **Region**: pilih `Southeast Asia (Singapore)` (paling dekat ke Jakarta)
   - **Pricing Plan**: `Free`
4. Klik **Create new project**
5. Tunggu ~2 menit, status berubah jadi hijau

### A.2 Ambil Connection String
1. Di project Supabase, klik ikon ⚙️ **Project Settings** (sidebar kiri bawah)
2. Klik **Database**
3. Scroll ke **Connection string**
4. **PENTING**: pilih tab **URI** lalu mode **Transaction** (port **6543**, bukan 5432)
5. URL akan terlihat seperti:
   ```
   postgresql://postgres.abcdefghij:[YOUR-PASSWORD]@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres
   ```
6. Ganti `[YOUR-PASSWORD]` dengan password yang kamu generate di A.1
7. **Copy URL lengkap** — akan dipakai di Fase D

> ✅ **Selesai Fase A**. Database PostgreSQL kamu siap di Supabase.

---

## 3. Fase B — Setup Telegram Bot + Channel

### B.1 Buat Bot
1. Buka Telegram, chat dengan **@BotFather**
2. Kirim `/newbot`
3. Beri nama bot: `Gonanku Vault Bot` (atau apa pun)
4. Beri username: `gonanku_vault_bot` (harus akhiran `bot`, unik global)
5. BotFather kasih **token** seperti `1234567890:ABCdef...`
6. **SIMPAN TOKEN INI**

### B.2 Buat Private Channel
1. Telegram → New Channel
2. Tipe: **Private** (penting — supaya hanya kamu dan bot yang akses)
3. Nama: `Gonanku Vault` (atau apa pun)
4. Setelah jadi, **tambah bot kamu sebagai admin**:
   - Channel → Settings → Administrators → Add Administrator
   - Cari `@gonanku_vault_bot`, kasih akses **Post Messages**

### B.3 Ambil Chat ID
1. Kirim 1 pesan apa saja di channel kamu (mis. "test")
2. Di browser, buka:
   ```
   https://api.telegram.org/bot<TOKEN_KAMU>/getUpdates
   ```
   Ganti `<TOKEN_KAMU>` dengan token dari B.1
3. Cari `"chat":{"id":-100xxxxxxxxxx, ...` — itu **Chat ID** (selalu mulai dengan `-100`)
4. **SIMPAN CHAT ID INI**

> ✅ **Selesai Fase B**. Telegram bot + channel siap.

---

## 4. Fase C — Setup GCP Project

Buka **PowerShell** di folder proyek Gonanku.

### C.1 Login & buat project
```powershell
# Login (akan buka browser)
gcloud auth login

# Buat project baru — ganti ID jadi unik kamu
$PROJECT_ID = "gonanku-prod-2026"
gcloud projects create $PROJECT_ID --name="Gonanku"

# Set sebagai project aktif
gcloud config set project $PROJECT_ID
```

### C.2 Link ke billing account
```powershell
# Ganti dengan billing account ID kamu (sudah ada: 01A770-22235C-497805)
gcloud billing projects link $PROJECT_ID --billing-account=01A770-22235C-497805
```

### C.3 Aktifkan API yang dibutuhkan
```powershell
gcloud services enable `
    run.googleapis.com `
    cloudbuild.googleapis.com `
    artifactregistry.googleapis.com
```

Tunggu ~30 detik sampai semua selesai.

### C.4 Buat Artifact Registry (tempat simpan Docker image)
```powershell
gcloud artifacts repositories create gonanku-repo `
    --repository-format=docker `
    --location=asia-southeast1 `
    --description="Gonanku container images"
```

### C.5 Configure Docker auth
```powershell
gcloud auth configure-docker asia-southeast1-docker.pkg.dev --quiet
```

> ✅ **Selesai Fase C**. GCP siap menerima deploy.

---

## 5. Fase D — Konfigurasi `.env.production` di laptop

### D.1 Copy template
```powershell
cd "C:\Documents\KULIAH\SEMESTER 6\PROJECT\PROJECTCLOUDTUBES"
Copy-Item .env.production.example .env.production
```

### D.2 Generate SECRET_KEY baru
```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```
Copy hasilnya (64 karakter hex).

### D.3 Edit `.env.production`
Buka file `.env.production` dengan editor (VS Code, Notepad), isi:

```env
APP_NAME=Gonanku
APP_ENV=production
SECRET_KEY=<paste hasil dari D.2>

DATABASE_URL=<paste connection string Supabase dari A.2>

TELEGRAM_BOT_TOKEN=<token dari B.1>
TELEGRAM_CHAT_ID=<chat id dari B.3, format -100xxxxxxxxxx>

GROQ_API_KEY=<key 1 dari .env lama>
GROQ_API_KEY_2=<key 2>
GROQ_API_KEY_3=<key 3>
```

**Simpan file**. File ini sudah masuk `.gitignore` — tidak akan ter-commit ke Git.

> ⚠️ **Verifikasi sebelum lanjut**:
> - DATABASE_URL **tidak boleh** masih ada `SUPABASE_PASSWORD` atau `refxxxxx`
> - SECRET_KEY harus 64 karakter (bukan placeholder)
> - TELEGRAM_CHAT_ID mulai dengan `-100`

---

## 6. Fase E — Migrasi skema ke Supabase

Cuma sekali, dari laptop kamu.

### E.1 Pastikan dependency Python terpasang
```powershell
pip install -r requirements.txt
```

### E.2 Jalankan migrasi
```powershell
.\migrate.ps1
```

Script akan:
1. Baca `DATABASE_URL` dari `.env.production`
2. Connect ke Supabase
3. Jalankan `flask db upgrade` → buat 7 tabel + index

**Expected output**:
```
==> Gonanku Migration to Production DB
Target DB: postgresql://postgres.xxxxx:****@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres
==> flask db upgrade...
INFO  [alembic.runtime.migration] Running upgrade  -> d494b5cbd835, skema awal gonanku
==> Selesai. Skema berhasil dibuat di Supabase.
```

### E.3 Buat akun pemilik vault
```powershell
$env:DATABASE_URL = (Get-Content .env.production | Select-String "^DATABASE_URL=").Line.Substring(13)
$env:FLASK_APP = "run.py"
flask buat-pengguna email@kamu.id "Nama Kamu" sandi_minimal_8_karakter
```

### E.4 Verifikasi di Supabase Console
1. Buka Supabase project → **Table Editor**
2. Harus muncul 7 tabel: `pengguna`, `kategori`, `tag`, `berkas`, `berkas_tag`, `log_aktivitas`, `riwayat_chat`, plus `alembic_version`
3. Klik tabel `pengguna` → ada 1 baris (akun yang baru kamu buat)
4. Klik tabel `kategori` → ada 10 kategori default

> ✅ **Selesai Fase E**. Skema + akun pemilik vault siap.

---

## 7. Fase F — Deploy ke Cloud Run

### F.1 Deploy otomatis dengan script
```powershell
.\deploy.ps1
```

Script akan:
1. Build Docker image lewat Cloud Build (~3-5 menit)
2. Push image ke Artifact Registry
3. Deploy ke Cloud Run dengan semua env var dari `.env.production`
4. Tampilkan URL service di akhir

**Expected output di akhir**:
```
============================================================
  DEPLOY BERHASIL
============================================================
  Service URL : https://gonanku-app-xxxxx-as.a.run.app
  Health      : https://gonanku-app-xxxxx-as.a.run.app/health
  Login       : https://gonanku-app-xxxxx-as.a.run.app/login
```

### F.2 Catat Service URL
**Simpan URL** ini — itu URL produksi Gonanku kamu.

---

## 8. Fase G — Verifikasi production

### G.1 Cek health endpoint
Buka di browser: `<SERVICE_URL>/health`

Expected response:
```json
{"status": "ok", "app": "Gonanku"}
```

### G.2 Login
1. Buka `<SERVICE_URL>/login`
2. Login dengan akun yang dibuat di Fase E.3
3. Harus masuk ke dashboard

### G.3 Test upload
1. Klik **+ Upload Arsip**
2. Pilih 1 file dokumen kecil (PDF/TXT)
3. Submit
4. **Cek Telegram**: file harus muncul di private channel kamu
5. **Cek detail file**: ringkasan AI harus terisi

### G.4 Test chatbot
1. Buka menu **Chatbot**
2. Tanya: `tampilkan dokumen` (atau apa pun terkait file yang barusan kamu upload)
3. Harus jawab + tampilkan kartu file

### G.5 Cek biaya
1. Buka https://console.cloud.google.com/billing/01A770-22235C-497805/reports
2. Filter **Service** → **Cloud Run**
3. Cost harusnya **Rp 0** (under Always Free quota)

### G.6 Cek log realtime (kalau ada error)
```powershell
gcloud run services logs tail gonanku-app --region=asia-southeast1
```

> ✅ **DEPLOY SELESAI**. Gonanku live di production.

---

## 9. Troubleshooting umum

### ❌ `could not translate host name` saat migrasi
Penyebab: DATABASE_URL typo / password salah.
**Fix**: cek ulang nilai di `.env.production`, pastikan password Supabase benar.

### ❌ `SSL connection required` saat connect
Penyebab: sslmode tidak dipasang.
**Fix**: sudah ditangani otomatis oleh `config.py` (patch `?sslmode=require`). Kalau masih muncul, cek apakah `app/config.py` versi terbaru.

### ❌ `Permission denied` saat `gcloud builds submit`
**Fix**:
```powershell
gcloud auth configure-docker asia-southeast1-docker.pkg.dev --quiet
gcloud auth application-default login
```

### ❌ Cloud Run 503 / Service Unavailable
Penyebab: container crash saat startup.
**Cek log**:
```powershell
gcloud run services logs read gonanku-app --region=asia-southeast1 --limit=100
```
Penyebab umum: ENV var kurang (DATABASE_URL salah, SECRET_KEY kosong, dll).

### ❌ Upload gagal di production tapi sukses di lokal
Penyebab: TELEGRAM_BOT_TOKEN atau TELEGRAM_CHAT_ID salah.
**Fix**: cek URL `https://api.telegram.org/bot<TOKEN>/getMe` — kalau 401 = token salah; kalau OK = cek chat ID.

### ❌ Chatbot bilang "Groq belum dikonfigurasi"
Penyebab: GROQ_API_KEY tidak ter-set di Cloud Run.
**Fix**: jalankan ulang `.\deploy.ps1` setelah pastikan key ada di `.env.production`.

### ❌ Foto/screenshot tidak dapat ringkasan AI
Penyebab: GROQ_API_KEY_3 (vision) tidak ter-set atau invalid.
**Fix**: ulangi deploy dengan key vision yang valid di `.env.production`.

---

## 10. Re-deploy setelah update code

Setiap ada perubahan code (push ke laptop), tinggal jalankan ulang:

```powershell
.\deploy.ps1
```

Script akan otomatis tag image dengan timestamp baru (`v202606051430` dst) supaya Cloud Run tahu ini versi berbeda.

**Env var tidak perlu di-set ulang** — script membaca ulang dari `.env.production`.

---

## 11. Cara hapus semua resource (kalau demo selesai)

Untuk pastikan **tidak ada biaya berlanjut** setelah demo:

```powershell
# 1. Hapus Cloud Run service
gcloud run services delete gonanku-app --region=asia-southeast1 --quiet

# 2. Hapus Artifact Registry repo (image)
gcloud artifacts repositories delete gonanku-repo --location=asia-southeast1 --quiet

# 3. (OPSIONAL) Hapus project sepenuhnya
$PROJECT_ID = "gonanku-prod-2026"  # ganti sesuai project kamu
gcloud projects delete $PROJECT_ID --quiet
```

**Supabase**: tidak ada biaya selama free tier. Bisa dibiarkan, atau hapus project lewat dashboard Supabase.

---

## 📊 Estimasi biaya produksi (untuk reference)

| Resource | Pemakaian demo akademik | Cost / bulan |
|---|---|---|
| Cloud Run (request, vCPU, memory) | < 1.000 req/hari | **Rp 0** (Always Free) |
| Artifact Registry (image storage) | 1 image ~150 MB | **Rp 0** (< 0.5 GB free) |
| Cloud Build (build minutes) | ~5 menit/deploy | **Rp 0** (< 120 min/hari free) |
| Egress network | < 1 GB/bulan | **Rp 0** (1 GB free) |
| Supabase Postgres | 0.5 GB DB | **Rp 0** (free tier) |
| Telegram API | unlimited | **Rp 0** |
| Groq API | < 10k req/bulan | **Rp 0** (free tier) |
| **TOTAL** |  | **Rp 0** |

Kredit GCP kamu Rp 16,6 juta tetap utuh untuk eksperimen lain.

---

## 🆘 Butuh bantuan?

Kalau ada error yang tidak ada di troubleshooting di atas, kirim:
1. Perintah yang kamu jalankan
2. Pesan error lengkap
3. Output `gcloud config list` + `gcloud auth list`

Saya bantu diagnose.
