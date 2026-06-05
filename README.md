<p align="center">
  <img width="1024" height="437" alt="gonanku_banner" src="https://github.com/user-attachments/assets/b07b0e80-7a3b-42fe-9853-99e570ba3645" />
</p>

<h1 align="center">☁️ Gonanku — Personal AI Memory Vault</h1>

<p align="center">
  <a href="https://git.io/typing-svg">
    <img src="https://readme-typing-svg.demolab.com?font=Plus+Jakarta+Sans&weight=600&size=22&duration=3000&pause=1000&color=1C4D8D&center=true&vCenter=true&multiline=true&repeat=true&width=600&height=70&lines=Simpan+kenangan.+Temukan+kembali.;Ditenagai+kecerdasan+buatan+%F0%9F%A7%A0" alt="Typing SVG"/>
  </a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/Flask-3.x-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask"/>
  <img src="https://img.shields.io/badge/Groq_AI-LLaMA_3.3_70B-F55036?style=for-the-badge&logo=meta&logoColor=white" alt="Groq AI"/>
  <img src="https://img.shields.io/badge/Telegram_Bot_API-26A5E4?style=for-the-badge&logo=telegram&logoColor=white" alt="Telegram"/>
  <img src="https://img.shields.io/badge/Google_Cloud-4285F4?style=for-the-badge&logo=google-cloud&logoColor=white" alt="GCP"/>
  <img src="https://img.shields.io/badge/Cloud_SQL-003B57?style=for-the-badge&logo=postgresql&logoColor=white" alt="Database"/>
</p>

<p align="center">
  <img src="https://img.shields.io/github/last-commit/Sulthonikamalm/cloudtubes-gonanku?style=flat-square&color=1C4D8D" alt="Last Commit"/>
  <img src="https://img.shields.io/github/repo-size/Sulthonikamalm/cloudtubes-gonanku?style=flat-square&color=4988C4" alt="Repo Size"/>
  <img src="https://img.shields.io/github/languages/count/Sulthonikamalm/cloudtubes-gonanku?style=flat-square&color=0F2854" alt="Languages"/>
  <img src="https://img.shields.io/badge/status-active-2F855A?style=flat-square" alt="Status"/>
  <img src="https://img.shields.io/badge/tugas_besar-komputasi_awan-BDE8F5?style=flat-square" alt="Course"/>
</p>

<p align="center">
  <a href="#-tentang-proyek">Tentang</a> •
  <a href="#-arsitektur-sistem">Arsitektur</a> •
  <a href="#-alur-kerja">Alur Kerja</a> •
  <a href="#-fitur-utama">Fitur</a> •
  <a href="#%EF%B8%8F-tech-stack">Stack</a> •
  <a href="#-cara-menjalankan">Instalasi</a> •
  <a href="#-identitas-mahasiswa">Identitas</a>
</p>

---

## 📋 Tentang Proyek

> **Gonanku** adalah aplikasi web arsip pribadi cerdas yang dibangun sebagai **Tugas Besar Mata Kuliah Komputasi Awan** di Telkom University Surabaya.

Pernahkah Anda kehilangan file penting di antara ribuan foto di galeri, chat WhatsApp, folder download, atau flashdisk yang tercecer?

**Gonanku** hadir sebagai solusi — sebuah *personal memory vault* yang:
- 📤 Menyimpan file di **Telegram Private Channel** (gratis & unlimited)
- 🧠 Mengkatalogkan otomatis dengan **Groq AI** (judul, kategori, tag, ringkasan)
- 🔍 Memungkinkan pencarian dengan **chatbot AI** berbahasa Indonesia
- ☁️ Berjalan di **Google Cloud Platform** (Cloud Run + Cloud SQL)

### ❓ Mengapa Gonanku Berbeda?

| Masalah Umum | Solusi Gonanku |
|:---|:---|
| 📁 File tercecer di galeri, chat, email, flashdisk | ✅ Satu tempat terpusat untuk semua arsip |
| 🏷️ Nama file tidak jelas (`IMG_20250601_*.jpg`) | ✅ AI otomatis memberi judul deskriptif |
| 🔎 Sulit mencari file lama | ✅ Chatbot AI: *"cari resi shopee bulan lalu"* |
| 💸 Cloud storage mahal | ✅ Telegram = storage **gratis & unlimited** |
| 📊 Tidak tahu punya berapa file | ✅ Dashboard **16 metrik** real-time |

---

## 🏗️ Arsitektur Sistem

```mermaid
graph TB
    subgraph CLIENT["🖥️ Client Layer"]
        USER["👤 User<br/>Browser / Mobile Web"]
    end

    subgraph APP["🌐 Gonanku Web Application"]
        direction LR
        FE["📄 Frontend<br/>HTML + CSS + JS + Jinja2"]
        DASH["📊 Dashboard"]
        UPLOAD["📤 Upload"]
        CHAT["🤖 Chatbot"]
    end

    subgraph BACKEND["🐍 Flask Backend"]
        direction LR
        ROUTES["🔀 Routes"]
        SERVICES["⚙️ Services"]
        MODELS["📦 Models"]
    end

    subgraph EXTERNAL["☁️ External Services"]
        direction LR
        TG["📱 Telegram Bot API<br/>Private Channel<br/><i>File Storage</i>"]
        DB["💾 Cloud SQL / SQLite<br/><i>Metadata Only</i>"]
        AI["🧠 Groq AI<br/>LLaMA 3.3 70B<br/><i>5-Key Failover</i>"]
    end

    USER --> FE
    FE --> DASH & UPLOAD & CHAT
    DASH & UPLOAD & CHAT --> ROUTES
    ROUTES --> SERVICES
    SERVICES --> MODELS
    SERVICES --> TG & DB & AI

    style CLIENT fill:#BDE8F5,stroke:#0F2854,color:#0F2854
    style APP fill:#E8F4FD,stroke:#1C4D8D,color:#0F2854
    style BACKEND fill:#D6E9F8,stroke:#1C4D8D,color:#0F2854
    style EXTERNAL fill:#F0F7FF,stroke:#4988C4,color:#0F2854
    style USER fill:#fff,stroke:#1C4D8D,color:#0F2854
    style TG fill:#26A5E4,stroke:#0F2854,color:#fff
    style DB fill:#336791,stroke:#0F2854,color:#fff
    style AI fill:#F55036,stroke:#0F2854,color:#fff
```

---

## 🔄 Alur Kerja

### 📤 Alur Upload File

```mermaid
sequenceDiagram
    actor U as 👤 User
    participant W as 🌐 Website
    participant F as 🐍 Flask
    participant T as 📱 Telegram
    participant D as 💾 Database
    participant A as 🧠 Groq AI

    U->>W: Pilih file & isi metadata
    W->>F: POST /upload (file + form)
    F->>F: Validasi ukuran & tipe
    F->>T: Kirim file ke Private Channel
    T-->>F: message_id + file_id
    F->>D: Simpan metadata file
    F->>A: Analisis isi file
    A-->>F: judul, kategori, tag, ringkasan
    F->>D: Update metadata AI
    F-->>W: ✅ Upload berhasil!
    W-->>U: Tampilkan di dashboard
```

### 🤖 Alur Chatbot

```mermaid
sequenceDiagram
    actor U as 👤 User
    participant W as 🌐 Chatbot UI
    participant F as 🐍 Flask
    participant A as 🧠 Groq AI
    participant D as 💾 Database

    U->>W: "Cari resi shopee bulan lalu"
    W->>F: POST /chat/tanya
    F->>A: Parse intent pertanyaan
    A-->>F: kata_kunci, tanggal, tipe_file
    F->>D: Query dengan 4-layer fallback
    D-->>F: Daftar file relevan
    F->>A: Susun jawaban natural
    A-->>F: Jawaban Bahasa Indonesia
    F-->>W: Jawaban + kartu file
    W-->>U: Tampilkan hasil pencarian
```

### 🧠 AI Processing Pipeline

```mermaid
graph LR
    subgraph INPUT["📥 Input"]
        FILE["File Upload"]
        IMG["Foto / Screenshot"]
        DOC["Dokumen PDF/DOCX"]
    end

    subgraph EXTRACT["🔍 Extraction"]
        OCR["Vision AI<br/>OCR + Deskripsi"]
        TXT["Text Extraction<br/>PyPDF2 / python-docx"]
    end

    subgraph AI["🧠 Groq AI Engine"]
        META["Metadata Generator<br/>Judul + Kategori + Tag"]
        SUM["Ringkasan AI"]
        PRIV["Privacy Detector<br/>NIK, Rekening, dll"]
    end

    subgraph OUTPUT["📤 Output"]
        DB["💾 Database"]
    end

    FILE --> IMG & DOC
    IMG --> OCR
    DOC --> TXT
    OCR --> META
    TXT --> META
    META --> SUM --> PRIV --> DB

    style INPUT fill:#BDE8F5,stroke:#1C4D8D
    style EXTRACT fill:#E8F4FD,stroke:#1C4D8D
    style AI fill:#FFE8E3,stroke:#F55036
    style OUTPUT fill:#D4EDDA,stroke:#2F855A
```

---

## ✨ Fitur Utama

<table>
<tr>
<td width="50%">

### 📊 Dashboard Cerdas
- **16 metrik real-time** — total arsip, foto, video, dokumen, audio, screenshot, ukuran total, upload hari/bulan ini, status AI, file sensitif
- Grafik komposisi tipe file & kategori terbanyak
- File terbaru & log aktivitas terkini

</td>
<td width="50%">

### 📤 Upload Multi-File
- Drag & drop atau pilih file (maks 50 MB/file)
- Batch upload: 15 foto / 10 dokumen sekaligus
- Image cropper untuk foto profil
- File otomatis → Telegram private channel

</td>
</tr>
<tr>
<td width="50%">

### 🧠 AI-Powered Metadata
- **Auto-Title** — judul deskriptif dari isi file
- **Auto-Category** — 10+ kategori otomatis
- **Auto-Tag** — tag relevan untuk pencarian
- **Auto-Summary** — ringkasan isi dokumen
- **Privacy Detection** — deteksi NIK, rekening, dll
- **Vision/OCR** — baca teks dari foto
- **5 API key failover** — always-on

</td>
<td width="50%">

### 🤖 Chatbot Pencarian AI
- Natural language: *"cari resi shopee bulan lalu"*
- Intent parsing NLP Bahasa Indonesia
- **4-layer search fallback** → selalu dapat hasil
- **Relevance scoring** → hasil paling akurat di atas
- Pencarian di **8+ kolom** termasuk OCR text

</td>
</tr>
<tr>
<td width="50%">

### 🗂️ Manajemen Arsip
- CRUD file, kategori, dan tag
- Soft delete & restore
- Filter tipe, kategori, tanggal, privasi
- Regenerate AI metadata kapan saja
- Activity log & audit trail

</td>
<td width="50%">

### 🎨 UI/UX Profesional
- Desain clean & personal
- 🌙 Dark / ☀️ Light mode
- Responsive mobile & desktop
- Micro-animations & transitions
- Font Plus Jakarta Sans

</td>
</tr>
</table>

### 🔁 Smart Search — 4-Layer Fallback

```mermaid
graph TD
    Q["🔍 User Query"] --> L1

    L1{"Layer 1<br/>Full Filter<br/>keyword + tipe + kategori + tanggal"}
    L1 -->|"✅ Found"| R["📄 Results"]
    L1 -->|"❌ Empty"| L2

    L2{"Layer 2<br/>Soft Filter<br/>keyword + tanggal only"}
    L2 -->|"✅ Found"| R
    L2 -->|"❌ Empty"| L3

    L3{"Layer 3<br/>Word Split<br/>pecah frasa → kata individual"}
    L3 -->|"✅ Found"| R
    L3 -->|"❌ Empty"| L4

    L4{"Layer 4<br/>Fuzzy Match<br/>substring ≥ 3 karakter"}
    L4 -->|"✅ Found"| R
    L4 -->|"❌ Empty"| NOPE["😔 Tidak ditemukan"]

    style Q fill:#BDE8F5,stroke:#1C4D8D
    style R fill:#D4EDDA,stroke:#2F855A
    style NOPE fill:#FED7D7,stroke:#C53030
    style L1 fill:#E8F4FD,stroke:#1C4D8D
    style L2 fill:#E8F4FD,stroke:#4988C4
    style L3 fill:#F0F7FF,stroke:#4988C4
    style L4 fill:#FFF5E6,stroke:#B7791F
```

---

## 🛠️ Tech Stack

<table>
<tr>
<td align="center" width="96">
  <img src="https://skillicons.dev/icons?i=python" width="48" height="48" alt="Python"/>
  <br><strong>Python</strong>
</td>
<td align="center" width="96">
  <img src="https://skillicons.dev/icons?i=flask" width="48" height="48" alt="Flask"/>
  <br><strong>Flask</strong>
</td>
<td align="center" width="96">
  <img src="https://skillicons.dev/icons?i=postgres" width="48" height="48" alt="PostgreSQL"/>
  <br><strong>Cloud SQL</strong>
</td>
<td align="center" width="96">
  <img src="https://skillicons.dev/icons?i=sqlite" width="48" height="48" alt="SQLite"/>
  <br><strong>SQLite</strong>
</td>
<td align="center" width="96">
  <img src="https://skillicons.dev/icons?i=html" width="48" height="48" alt="HTML"/>
  <br><strong>HTML5</strong>
</td>
<td align="center" width="96">
  <img src="https://skillicons.dev/icons?i=css" width="48" height="48" alt="CSS"/>
  <br><strong>CSS3</strong>
</td>
<td align="center" width="96">
  <img src="https://skillicons.dev/icons?i=js" width="48" height="48" alt="JavaScript"/>
  <br><strong>JavaScript</strong>
</td>
<td align="center" width="96">
  <img src="https://skillicons.dev/icons?i=docker" width="48" height="48" alt="Docker"/>
  <br><strong>Docker</strong>
</td>
</tr>
<tr>
<td align="center" width="96">
  <img src="https://skillicons.dev/icons?i=gcp" width="48" height="48" alt="GCP"/>
  <br><strong>GCP</strong>
</td>
<td align="center" width="96">
  <img src="https://skillicons.dev/icons?i=git" width="48" height="48" alt="Git"/>
  <br><strong>Git</strong>
</td>
<td align="center" width="96">
  <img src="https://upload.wikimedia.org/wikipedia/commons/8/82/Telegram_logo.svg" width="48" height="48" alt="Telegram"/>
  <br><strong>Telegram</strong>
</td>
<td align="center" width="96">
  <img src="https://groq.com/wp-content/uploads/2024/03/PBMark-Purple.svg" width="48" height="48" alt="Groq"/>
  <br><strong>Groq AI</strong>
</td>
<td align="center" width="96" colspan="4">
</td>
</tr>
</table>

<details>
<summary><strong>📦 Detail Stack Lengkap (klik untuk membuka)</strong></summary>

| Layer | Teknologi | Fungsi |
|:------|:----------|:-------|
| **Frontend** | HTML, CSS, JavaScript, Jinja2 | UI/UX responsif dan interaktif |
| **Backend** | Python Flask | REST API & server-side rendering |
| **Database** | Cloud SQL (PostgreSQL) / SQLite | Metadata file & user data |
| **AI Engine** | Groq API (LLaMA 3.3 70B) | Metadata otomatis, chatbot, OCR |
| **Vision AI** | Groq Vision (LLaMA 4 Scout) | Membaca teks dari gambar |
| **File Storage** | Telegram Bot API (Private Channel) | Penyimpanan file gratis & unlimited |
| **Deployment** | Google Cloud Run | Serverless container hosting |
| **Container** | Docker | Reproducible environment |
| **Migration** | Flask-Migrate (Alembic) | Database version control |
| **Auth** | Flask-Login + Werkzeug | Session auth + password hashing |

</details>

---

## 🚀 Cara Menjalankan

<details>
<summary><strong>📋 Prasyarat</strong></summary>

- Python 3.11+
- Git
- Akun Telegram (untuk bot & private channel)
- API Key Groq (gratis di [console.groq.com](https://console.groq.com))

</details>

### 1️⃣ Clone & Setup

```bash
git clone https://github.com/Sulthonikamalm/cloudtubes-gonanku.git
cd cloudtubes-gonanku
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac
pip install -r requirements.txt
```

### 2️⃣ Konfigurasi

```bash
cp .env.example .env
```

Edit `.env` — isi minimal:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_private_channel_id
GROQ_API_KEY=your_groq_api_key
```

### 3️⃣ Jalankan

```bash
flask db upgrade
flask buat-pengguna email@example.com username password
flask run
```

Buka 👉 **http://localhost:5000** 🎉

---

## 📁 Struktur Proyek

<details>
<summary><strong>🗂️ Lihat pohon direktori lengkap</strong></summary>

```
cloudtubes-gonanku/
├── 📄 run.py                       # Entry point
├── 📄 Dockerfile                   # Container config
├── 📄 requirements.txt             # Dependencies
├── 📄 .env.example                 # Env template
│
├── 📂 app/
│   ├── __init__.py                 # App factory
│   ├── config.py                   # Environment config
│   ├── extensions.py               # SQLAlchemy, LoginManager
│   │
│   ├── 📂 models/                  # Database ORM
│   │   ├── pengguna.py             #   👤 User
│   │   ├── berkas.py               #   📄 File metadata
│   │   ├── kategori.py             #   📂 Category
│   │   ├── tag.py                  #   🏷️ Tag
│   │   ├── riwayat_chat.py         #   💬 Chat history
│   │   └── log_aktivitas.py        #   📋 Activity log
│   │
│   ├── 📂 routes/                  # HTTP handlers
│   │   ├── auth_routes.py          #   🔐 Login, logout, profil
│   │   ├── dashboard_routes.py     #   📊 Dashboard & metrik
│   │   ├── berkas_routes.py        #   📄 CRUD file/arsip
│   │   └── chat_routes.py          #   🤖 Chatbot API
│   │
│   ├── 📂 services/                # Business logic
│   │   ├── layanan_groq.py         #   🧠 Groq AI (5-key failover)
│   │   ├── layanan_telegram.py     #   📱 Telegram Bot API
│   │   ├── layanan_chatbot.py      #   🤖 Chatbot engine
│   │   ├── layanan_pencarian.py    #   🔍 Smart search (4-layer)
│   │   ├── layanan_upload.py       #   📤 Upload pipeline
│   │   └── layanan_log.py          #   📋 Activity logging
│   │
│   ├── 📂 templates/               # Jinja2 HTML
│   ├── 📂 static/                  # CSS, JS, images
│   └── 📂 utils/                   # Helpers
│
├── 📂 migrations/                  # Alembic migrations
└── 📂 docs/                        # Documentation
```

</details>

---

## 🔐 Keamanan

```mermaid
graph LR
    A["🔑 API Keys"] -->|".env file"| B["🚫 Not in Git"]
    C["🔒 Passwords"] -->|"Werkzeug"| D["#️⃣ Bcrypt Hash"]
    E["📄 Files"] -->|"Private Channel"| F["🔐 Telegram Encrypted"]
    G["👤 Queries"] -->|"pengguna_id"| H["🛡️ User-scoped"]
    I["📊 Sensitive Data"] -->|"AI Detection"| J["⚠️ Auto-flagged"]

    style B fill:#D4EDDA,stroke:#2F855A
    style D fill:#D4EDDA,stroke:#2F855A
    style F fill:#D4EDDA,stroke:#2F855A
    style H fill:#D4EDDA,stroke:#2F855A
    style J fill:#FFF3CD,stroke:#B7791F
```

---

## ☁️ Deployment (Google Cloud)

```mermaid
graph LR
    A["💻 Local Dev"] -->|"git push"| B["📦 GitHub"]
    B -->|"gcloud run deploy"| C["🐳 Cloud Build"]
    C -->|"Docker image"| D["☁️ Cloud Run"]
    D <-->|"SQL connection"| E["💾 Cloud SQL<br/>PostgreSQL"]
    D <-->|"HTTPS API"| F["📱 Telegram"]
    D <-->|"HTTPS API"| G["🧠 Groq AI"]

    style A fill:#E8F4FD,stroke:#1C4D8D
    style B fill:#24292E,stroke:#fff,color:#fff
    style C fill:#4285F4,stroke:#fff,color:#fff
    style D fill:#4285F4,stroke:#fff,color:#fff
    style E fill:#336791,stroke:#fff,color:#fff
    style F fill:#26A5E4,stroke:#fff,color:#fff
    style G fill:#F55036,stroke:#fff,color:#fff
```

```bash
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
    <td align="center" rowspan="6" width="160">
      <img src="https://img.shields.io/badge/TelU-Surabaya-C53030?style=for-the-badge" alt="TelU"/><br/><br/>
      <img src="https://img.shields.io/badge/Semester-6-1C4D8D?style=for-the-badge" alt="Semester"/>
    </td>
    <td><strong>👤 Nama</strong></td>
    <td>Sulthonika Mahfudz Al Mujahidin</td>
  </tr>
  <tr>
    <td><strong>🆔 NIM</strong></td>
    <td><code>1202230023</code></td>
  </tr>
  <tr>
    <td><strong>🎓 Program Studi</strong></td>
    <td>S1 Teknologi Informasi</td>
  </tr>
  <tr>
    <td><strong>🏫 Universitas</strong></td>
    <td>Telkom University Surabaya</td>
  </tr>
  <tr>
    <td><strong>📚 Mata Kuliah</strong></td>
    <td>Komputasi Awan (Cloud Computing)</td>
  </tr>
  <tr>
    <td><strong>📅 Semester</strong></td>
    <td>6 — Genap 2025/2026</td>
  </tr>
</table>

---

## 📄 Lisensi

Proyek ini dibuat untuk keperluan akademik sebagai **Tugas Besar** mata kuliah **Komputasi Awan** di **Telkom University Surabaya**.

---

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0F2854&height=100&section=footer&text=Gonanku%20—%20Karena%20setiap%20file%20punya%20cerita&fontSize=16&fontColor=BDE8F5&animation=fadeIn" width="100%"/>
</p>

<p align="center">
  Dibuat dengan ❤️ dan ☕ di Surabaya
</p>
