# Deploy Gonanku ke Vercel

Panduan ini menambahkan deployment Vercel untuk demo portfolio. Panduan Cloud Run tetap tersedia di [DEPLOY.md](DEPLOY.md).

## Arsitektur Vercel

- Flask + Jinja2 berjalan sebagai satu Python Function melalui `api/index.py`.
- `public/static/` berisi mirror asset dari `app/static/` dan dilayani CDN Vercel.
- Supabase PostgreSQL menyimpan user dan metadata.
- Telegram private channel menyimpan file asli.
- Groq API menjalankan metadata, vision, dan chatbot.
- Vercel filesystem ephemeral. Aplikasi hanya memakai filesystem untuk file sementara sebelum upload ke Telegram.

## Batas penting Vercel

Vercel Function membatasi request body sampai **4.5 MB**. Karena itu konfigurasi Vercel memakai `MAX_UPLOAD_MB=4`. Upload lebih besar harus memakai Cloud Run atau storage upload langsung.

Function memakai `maxDuration=300` detik. Upload batch tetap dikirim satu file per request oleh `app/static/js/upload.js`, tetapi proses AI + Telegram bisa lama. Demo sebaiknya memakai file kecil dan satu-dua file per batch.

Rate limiter default `memory://` berlaku per instance Function, bukan counter global. Ini cukup untuk demo portfolio, bukan deployment multi-user berskala besar.

## Prasyarat

- Repository sudah ada di GitHub.
- Akun Vercel.
- Project Supabase PostgreSQL aktif.
- Telegram bot menjadi admin private channel.
- Groq API key.
- Python 3.12 lokal.
- Vercel CLI opsional: `npm install -g vercel`.

## 1. Siapkan database dan akun

Gunakan connection string Supabase pooler mode Transaction, biasanya port `6543`.

Di PowerShell, set env sementara untuk migrasi lokal:

```powershell
$env:APP_ENV = "production"
$env:SECRET_KEY = "isi_secret_random_minimal_32_karakter"
$env:DATABASE_URL = "postgresql://postgres.<project-ref>:<password>@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"

flask --app run.py db upgrade
flask --app run.py buat-pengguna email@kamu.id "Nama Kamu" "kata_sandi_minimal_8"
```

Jalankan migrasi hanya sekali. Jangan menjalankan `flask db upgrade` saat cold start Vercel.

## 2. Import repository ke Vercel

1. Buka [vercel.com/new](https://vercel.com/new).
2. Import repository GitHub `cloudtubes-gonanku`.
3. Biarkan **Root Directory** di root repository.
4. Framework akan terdeteksi sebagai Python/Flask dari `requirements.txt`.
5. Jangan menambahkan Build Command khusus.
6. Deploy preview pertama setelah environment variables diisi.

File deployment sudah tersedia:

- `api/index.py`: entrypoint Flask WSGI.
- `vercel.json`: rewrite route dan durasi Function.
- `.python-version`: Python 3.12.
- `public/static/`: asset CSS, JavaScript, dan gambar.

## 3. Isi Environment Variables

Buka **Project Settings → Environment Variables**. Tambahkan variable berikut untuk **Production** dan **Preview** bila preview juga perlu login/upload:

```env
APP_NAME=Gonanku
APP_ENV=production
SECRET_KEY=<random-secret-minimal-32-karakter>
DATABASE_URL=<supabase-postgresql-pooler-url>
TELEGRAM_BOT_TOKEN=<token-botfather>
TELEGRAM_CHAT_ID=-100xxxxxxxxxx
GROQ_API_KEY=<groq-key-1>
GROQ_API_KEY_2=<groq-key-2>
GROQ_API_KEY_3=<groq-key-3>
GROQ_API_KEY_4=<opsional>
GROQ_API_KEY_5=<opsional>
GROQ_API_KEY_6=<opsional>
GROQ_API_KEY_7=<opsional>
GROQ_MODEL_TEXT=llama-3.3-70b-versatile
GROQ_MODEL_VISION=meta-llama/llama-4-scout-17b-16e-instruct
GROQ_MODEL_AUDIO=
MAX_UPLOAD_MB=4
AI_TEXT_LIMIT=4000
BATAS_UPLOAD_FOTO=15
BATAS_UPLOAD_DOKUMEN=10
```

`DATABASE_URL` wajib diisi. Jika kosong, aplikasi memakai SQLite lokal yang tidak persisten di serverless.

Template variable tersedia di [.env.vercel.example](.env.vercel.example). File itu hanya contoh; jangan isi secret lalu commit.

## 4. Deploy

### Dashboard

Klik **Deploy** atau redeploy dari tab Deployments setelah environment variables tersimpan.

### Vercel CLI

```powershell
vercel login
vercel link
vercel --prod
```

## 5. Verifikasi

Ganti `https://nama-project.vercel.app` dengan URL deployment:

```powershell
curl.exe -i https://nama-project.vercel.app/health
curl.exe -I https://nama-project.vercel.app/static/images/favicon-48.png
curl.exe -i https://nama-project.vercel.app/robots.txt
curl.exe -i https://nama-project.vercel.app/manifest.json
```

Expected:

- `/health` mengembalikan JSON status `ok`.
- `/` menampilkan landing page.
- `/login` menampilkan form login.
- CSS, JavaScript, favicon, dan gambar termuat dari `/static/...`.

Uji di browser:

1. Login memakai akun yang dibuat di Supabase.
2. Buka dashboard.
3. Upload satu PDF atau foto **<=4 MB**.
4. Pastikan file masuk Telegram private channel.
5. Pastikan metadata muncul di Supabase dan dashboard.
6. Uji chatbot, edit metadata, soft delete, restore, dan foto profil.
7. Upload file >4 MB untuk memastikan guardrail menolak file sebelum request.

## Troubleshooting

### `FUNCTION_PAYLOAD_TOO_LARGE` atau HTTP 413

Request melewati batas body Vercel 4.5 MB. Pakai file <=4 MB. Batas UI dan backend sudah diset lewat `MAX_UPLOAD_MB`.

### `SECRET_KEY wajib diset...`

Set `SECRET_KEY` pada Environment Variables Vercel untuk environment yang sedang dideploy, lalu redeploy.

### Database gagal konek

Pastikan `DATABASE_URL` memakai URL PostgreSQL Supabase valid, password sudah di-URL-encode bila memiliki karakter khusus, dan gunakan pooler port `6543`.

### Static asset 404

Pastikan folder `public/static/` ikut Git dan path request dimulai `/static/`. Jangan menghapus rewrite dari `vercel.json`.

### Upload timeout

Pakai file kecil, kurangi jumlah file dalam satu batch, dan cek Function Logs. Vercel Hobby membatasi durasi maksimum Function 300 detik.

### Preview memakai data production

Vercel membedakan environment variables Preview dan Production. Isi keduanya hanya bila memang ingin preview mengakses database/integrasi yang sama.
