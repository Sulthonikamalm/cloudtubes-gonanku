<p align="center">
  <img src="docs/gonanku_banner.png" alt="Gonanku Banner" width="720"/>
</p>

<h1 align="center">☁️ Gonanku — Personal AI Memory Vault</h1>

<p align="center">
  <em>Simpan kenangan. Temukan kembali. Ditenagai kecerdasan buatan.</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/Flask-3.x-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask"/>
  <img src="https://img.shields.io/badge/Groq_AI-LLaMA_3.3_70B-F55036?style=for-the-badge&logo=meta&logoColor=white" alt="Groq AI"/>
  <img src="https://img.shields.io/badge/Telegram_Bot_API-26A5E4?style=for-the-badge&logo=telegram&logoColor=white" alt="Telegram"/>
  <img src="https://img.shields.io/badge/Google_Cloud-4285F4?style=for-the-badge&logo=google-cloud&logoColor=white" alt="GCP"/>
  <img src="https://img.shields.io/badge/SQLite_%7C_Cloud_SQL-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="Database"/>
</p>

<p align="center">
  <a href="#-tentang-proyek">Tentang</a> •
  <a href="#-arsitektur">Arsitektur</a> •
  <a href="#-fitur-utama">Fitur</a> •
  <a href="#-tech-stack">Stack</a> •
  <a href="#-cara-menjalankan">Instalasi</a> •
  <a href="#-screenshot">Screenshot</a> •
  <a href="#-identitas-mahasiswa">Identitas</a>
</p>

---

## 📋 Tentang Proyek

> **Gonanku** adalah aplikasi web arsip pribadi cerdas yang dibangun sebagai **Tugas Besar Mata Kuliah Komputasi Awan** di Telkom University Surabaya.

Pernahkah Anda kehilangan file penting di antara ribuan foto di galeri, chat WhatsApp, folder download, atau flashdisk yang tercecer? **Gonanku** hadir sebagai solusi — sebuah *personal memory vault* yang menyimpan file Anda di Telegram private channel, mengkatalogkannya dengan kecerdasan buatan, dan memungkinkan Anda menemukan kembali apapun cukup dengan bertanya ke chatbot.

### 💡 Konsep Inti

```
📱 User upload file melalui website
    ↓
📤 File dikirim otomatis ke Telegram Private Channel (penyimpanan gratis & unlimited)
    ↓
🧠 Groq AI menganalisis file → menghasilkan judul, kategori, tag, dan ringkasan otomatis
    ↓
💾 Metadata disimpan ke database (Cloud SQL / SQLite)
    ↓
🔍 User mencari file kapan saja lewat dashboard atau chatbot AI
```

### ❓ Mengapa Gonanku Berbeda?

| Masalah Umum | Solusi Gonanku |
|---|---|
| 📁 File tercecer di galeri, chat, email, flashdisk | Satu tempat terpusat untuk semua arsip |
| 🏷️ Nama file tidak jelas (IMG_20250601_*.jpg) | AI otomatis memberi judul deskriptif |
| 🔎 Sulit mencari file lama | Chatbot AI yang bisa menjawab "cari resi shopee bulan lalu" |
| 💸 Cloud storage mahal | Telegram sebagai storage gratis & unlimited |
| 📊 Tidak tahu punya berapa file | Dashboard metrik lengkap |

---

## 🏗️ Arsitektur

```
┌─────────────────────────────────────────────────────┐
│                    👤 USER                          │
│              Browser / Mobile Web                    │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│            🌐 GONANKU WEB APPLICATION               │
│      HTML + CSS + JavaScript + Jinja2 Template       │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │Dashboard │  │  Upload  │  │   Chatbot AI     │   │
│  │ Metrik   │  │  Arsip   │  │   Pencarian      │   │
│  └──────────┘  └──────────┘  └──────────────────┘   │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│              🐍 FLASK BACKEND (Python)              │
│  Routes → Services → Models → Extensions            │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │ Layanan  │  │ Layanan  │  │    Layanan       │   │
│  │ Upload   │  │ Chatbot  │  │    Groq AI       │   │
│  └────┬─────┘  └────┬─────┘  └───────┬──────────┘   │
│       │              │                │              │
└───────┼──────────────┼────────────────┼──────────────┘
        │              │                │
        ▼              ▼                ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────────┐
│  📱 Telegram │ │  💾 Database │ │   🧠 Groq AI     │
│  Bot API     │ │  Cloud SQL / │ │   LLaMA 3.3 70B  │
│  Private     │ │  SQLite      │ │   5-key failover  │
│  Channel     │ │              │ │   + Vision Model  │
└──────────────┘ └──────────────┘ └──────────────────┘
  File Storage     Metadata Only     Auto-Metadata
                                     Intent Parser
                                     Answer Generator
                                     OCR / Vision
```

---

## ✨ Fitur Utama

### 📊 Dashboard Cerdas
- **16 metrik real-time**: total arsip, foto, video, dokumen, audio, screenshot, ukuran total, upload hari/bulan ini, status AI, file sensitif, dan lainnya
- Grafik komposisi tipe file dan kategori terbanyak
- File terbaru dan log aktivitas terkini

### 📤 Upload Multi-File
- Drag & drop atau pilih file (maks 50 MB/file)
- Batch upload hingga 15 foto atau 10 dokumen sekaligus
- Preview file sebelum upload dengan crop tool untuk foto profil
- File otomatis terkirim ke Telegram private channel

### 🧠 AI-Powered Metadata
- **Auto-Title**: judul deskriptif dari isi file
- **Auto-Category**: kategorisasi otomatis dari 10+ kategori
- **Auto-Tag**: tag relevan untuk pencarian
- **Auto-Summary**: ringkasan isi dokumen/foto
- **Privacy Detection**: deteksi data sensitif (NIK, nomor rekening, dll)
- **Vision/OCR**: membaca teks dari foto/screenshot (resi, struk, dokumen)
- **5 API key dengan failover otomatis** — tidak pernah down

### 🤖 Chatbot Pencarian AI
- Pencarian natural language: *"cari resi shopee bulan lalu"*
- Intent parsing cerdas dengan NLP Indonesia
- 4-layer search fallback untuk hasil akurat
- Relevance scoring — hasil diurutkan berdasarkan relevansi
- Pencarian di 8+ kolom metadata termasuk OCR text

### 🗂️ Manajemen Arsip Lengkap
- CRUD file, kategori, dan tag
- Soft delete & restore
- Filter berdasarkan tipe, kategori, tanggal, status privasi
- Regenerate AI metadata kapan saja
- Activity log untuk audit trail

### 🎨 UI/UX Profesional
- Desain clean & personal — bukan template generik
- Dark/light mode support
- Responsive untuk mobile & desktop
- Animasi halus dan micro-interactions
- Font Plus Jakarta Sans

---

## 🛠️ Tech Stack

| Layer | Teknologi | Fungsi |
|-------|-----------|--------|
| **Frontend** | HTML, CSS, JavaScript, Jinja2 | UI/UX responsif dan interaktif |
| **Backend** | Python Flask | REST API & server-side rendering |
| **Database** | Cloud SQL (PostgreSQL) / SQLite | Metadata file & user data |
| **AI Engine** | Groq API (LLaMA 3.3 70B) | Metadata otomatis, chatbot, OCR |
| **Vision AI** | Groq Vision (LLaMA 4 Scout) | Membaca teks dari gambar |
| **File Storage** | Telegram Bot API (Private Channel) | Penyimpanan file gratis & unlimited |
| **Deployment** | Google Cloud Run | Serverless container hosting |
| **Container** | Docker | Reproducible environment |

---

## 🚀 Cara Menjalankan

### Prasyarat
- Python 3.11+
- Git
- Akun Telegram (untuk bot & private channel)
- API Key Groq (gratis di [console.groq.com](https://console.groq.com))

### 1. Clone Repository

```bash
git clone https://github.com/Sulthonikamalm/cloudtubes-gonanku.git
cd cloudtubes-gonanku
```

### 2. Setup Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Konfigurasi Environment

```bash
cp .env.example .env
```

Edit `.env` dan isi minimal:

```env
# Wajib untuk upload file
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_private_channel_id

# Wajib untuk AI (bisa 1 key saja, tapi 5 key lebih kuat)
GROQ_API_KEY=your_groq_api_key
```

### 5. Inisialisasi Database

```bash
flask db upgrade
```

### 6. Buat Akun Pertama

```bash
flask buat-pengguna email@example.com username password
```

### 7. Jalankan Server

```bash
flask run
```

Buka **http://localhost:5000** di browser. 🎉

---

## 📸 Screenshot

> *Screenshot akan ditambahkan setelah deployment.*

---

## 📁 Struktur Proyek

```
cloudtubes-gonanku/
├── app/
│   ├── __init__.py              # App factory
│   ├── config.py                # Konfigurasi (env vars)
│   ├── extensions.py            # SQLAlchemy, Login Manager
│   ├── models/                  # Database models
│   │   ├── pengguna.py          #   User model
│   │   ├── berkas.py            #   File metadata model
│   │   ├── kategori.py          #   Category model
│   │   ├── tag.py               #   Tag model
│   │   ├── riwayat_chat.py      #   Chat history model
│   │   └── log_aktivitas.py     #   Activity log model
│   ├── routes/                  # HTTP route handlers
│   │   ├── auth_routes.py       #   Login, logout, profil
│   │   ├── dashboard_routes.py  #   Dashboard & metrik
│   │   ├── arsip_routes.py      #   CRUD file/arsip
│   │   └── chatbot_routes.py    #   Chatbot API
│   ├── services/                # Business logic layer
│   │   ├── layanan_groq.py      #   Groq AI integration (5-key failover)
│   │   ├── layanan_telegram.py  #   Telegram Bot API
│   │   ├── layanan_chatbot.py   #   Chatbot engine
│   │   ├── layanan_pencarian.py #   Smart search (4-layer fallback)
│   │   ├── layanan_upload.py    #   File upload pipeline
│   │   └── layanan_log.py       #   Activity logging
│   ├── templates/               # Jinja2 HTML templates
│   ├── static/                  # CSS, JS, assets
│   └── utils/                   # Helper functions
├── migrations/                  # Flask-Migrate (Alembic)
├── docs/                        # Documentation & assets
├── Dockerfile                   # Container configuration
├── requirements.txt             # Python dependencies
├── run.py                       # Application entry point
├── .env.example                 # Environment template
└── .gitignore
```

---

## 🔐 Keamanan

- API key dan token disimpan di `.env` (tidak masuk Git)
- Password di-hash menggunakan Werkzeug
- File disimpan di Telegram private channel (tidak bisa diakses publik)
- Session-based authentication dengan Flask-Login
- Deteksi data sensitif otomatis oleh AI
- Setiap query difilter berdasarkan `pengguna_id`

---

## ☁️ Deployment (Google Cloud)

```bash
# Build & deploy ke Cloud Run
gcloud run deploy gonanku \
  --source . \
  --region asia-southeast2 \
  --allow-unauthenticated \
  --set-env-vars "DATABASE_URL=postgresql://..." \
  --min-instances 0 \
  --max-instances 2 \
  --memory 512Mi
```

---

## 👨‍🎓 Identitas Mahasiswa

<table>
  <tr>
    <td><strong>Nama</strong></td>
    <td>Sulthonika Mahfudz Al Mujahidin</td>
  </tr>
  <tr>
    <td><strong>NIM</strong></td>
    <td>1202230023</td>
  </tr>
  <tr>
    <td><strong>Program Studi</strong></td>
    <td>S1 Teknologi Informasi</td>
  </tr>
  <tr>
    <td><strong>Universitas</strong></td>
    <td>Telkom University Surabaya</td>
  </tr>
  <tr>
    <td><strong>Mata Kuliah</strong></td>
    <td>Komputasi Awan (Cloud Computing)</td>
  </tr>
  <tr>
    <td><strong>Semester</strong></td>
    <td>6 (Genap 2025/2026)</td>
  </tr>
</table>

---

## 📄 Lisensi

Proyek ini dibuat untuk keperluan akademik sebagai Tugas Besar mata kuliah **Komputasi Awan** di **Telkom University Surabaya**.

---

<p align="center">
  Dibuat dengan ❤️ dan ☕ di Surabaya
  <br/>
  <strong>Gonanku</strong> — <em>Karena setiap file punya cerita.</em>
</p>
