"""Pencarian berkas di database berdasarkan intent chatbot.

Selalu memfilter pengguna_id dan berkas yang belum dihapus. Maksimal 10 hasil.

Strategi pencarian berlapis (fallback) agar selalu mengembalikan hasil
yang paling relevan:
  1. Full filter (semua parameter intent).
  2. Fallback lunak (hapus filter kategori & tipe_file).
  3. Fallback kata per kata (pecah frasa menjadi kata individual).
  4. Pencarian fuzzy sederhana (cocokkan potongan kata >= 3 karakter).
"""

from datetime import datetime

from sqlalchemy import case

from app.extensions import db
from app.models import Berkas, Kategori, Tag
from app.models.konstanta import TIPE_BERKAS

# Kata generic yang akan SELALU di-skip dari kata_kunci:
# - Tipe file: sudah jadi filter tipe_file, tidak perlu ke keyword
# - Kata umum Indonesia: tidak punya nilai discriminasi
# Mencegah pencarian "foto bermasker" → match semua file foto.
_STOPWORDS = frozenset({
    # Tipe file (sudah jadi tipe_file filter)
    "foto", "video", "dokumen", "audio", "screenshot", "berkas", "file",
    # Kata umum tanya
    "saya", "aku", "ada", "tidak", "ya", "yang", "apakah", "adakah",
    "kah", "lah", "pun", "sih", "deh",
    # Preposisi & konjungsi
    "yang", "dan", "atau", "di", "ke", "dari", "untuk", "tentang",
    "pada", "dengan", "oleh", "agar", "supaya", "karena", "kalau",
    # Verba pencarian (sudah implisit dari intent)
    "cari", "carikan", "tampilkan", "tunjukkan", "lihat", "buka",
    "tolong", "mohon", "minta", "ingin", "mau",
    # Demonstrative & quantifier
    "ini", "itu", "semua", "satu", "beberapa", "banyak", "sedikit",
    # Common verbs
    "menggunakan", "memakai", "pakai", "punya", "memiliki",
    # Verba aksi yang muncul di pertanyaan tapi tidak match metadata
    "berfoto", "berfotonya", "berfoto-foto", "selfie", "wefie",
})


# Peta sinonim Bahasa Indonesia (informal ↔ formal) + atribut khas Gonanku.
# Dipakai oleh _ekspansi_sinonim() untuk menjembatani vocabulary gap antara
# query user (informal: "cewek", "berkacamata") dan output vision AI yang
# kadang formal ("wanita", "memakai kacamata"). Sumber pattern: ChatReID
# (arXiv 2502.19958), Memory-QA caption-for-retrieval (arXiv 2509.18436).
_SINONIM = {
    # Gender
    "cewek": ["wanita", "perempuan", "gadis", "mbak"],
    "cowok": ["pria", "laki", "lelaki", "lakilaki", "mas"],
    "wanita": ["cewek", "perempuan", "gadis"],
    "perempuan": ["cewek", "wanita", "gadis"],
    "pria": ["cowok", "laki", "lelaki"],
    "laki": ["cowok", "pria", "lelaki"],
    # Atribut kepala / wajah
    "berkacamata": ["kacamata", "berkaca", "kaca-mata"],
    "kacamata": ["berkacamata", "kaca-mata"],
    "berjilbab": ["jilbab", "hijab", "kerudung", "berhijab", "berkerudung"],
    "berhijab": ["hijab", "jilbab", "kerudung", "berjilbab", "berkerudung"],
    "berkerudung": ["kerudung", "jilbab", "hijab"],
    "jilbab": ["hijab", "kerudung", "berjilbab", "berhijab"],
    "hijab": ["jilbab", "kerudung", "berhijab", "berjilbab"],
    "kerudung": ["jilbab", "hijab", "berkerudung"],
    "berjenggot": ["jenggot", "berjanggut", "janggut"],
    "berkumis": ["kumis", "kumisan"],
    "bermasker": ["masker", "pakai-masker"],
    "masker": ["bermasker"],
    "berpeci": ["peci", "kopiah", "songkok"],
    "peci": ["berpeci", "kopiah", "songkok"],
    # Panggilan / hubungan
    "ibu": ["mama", "ibunda", "wanita", "perempuan"],
    "bapak": ["ayah", "papa", "pria", "laki"],
    "anak": ["bocah", "balita"],
    "kakak": ["kak", "abang", "mas", "mbak"],
    "adik": ["dik", "ade"],
    "teman": ["kawan", "sahabat", "rekan"],
    # Pakaian
    "kemeja": ["kameja"],
    "kaos": ["kaus", "tshirt", "t-shirt"],
    "jaket": ["jacket"],
    # Tempat
    "kampus": ["universitas", "kuliah"],
    "kelas": ["ruangkelas", "ruang-kelas"],
    "kantor": ["office", "tempat-kerja"],
}


# Prefix Bahasa Indonesia yang umum dipakai dan layak di-strip untuk
# mendapatkan akar kata. Sederhana, tidak full stemmer Sastrawi supaya
# tetap ringan dan tidak ada dependency baru.
_PREFIX_BI = ("ber", "men", "meng", "mem", "me", "ter", "pe", "pen")


def _ekspansi_sinonim(kata_kunci):
    """Ekspansi kata kunci dengan sinonim + ber-stripping akar kata.

    Contoh:
      ["cewek", "berkacamata"] → ["cewek", "wanita", "perempuan", "gadis",
                                  "mbak", "berkacamata", "kacamata", ...]

    Strategy: kalau kata ada di _SINONIM, tambah semua sinonimnya. Kalau
    kata pakai prefix BI (ber-, men-, dll), tambahkan juga akar katanya
    plus sinonim akar tersebut. Dedupe sambil pertahankan urutan.
    """
    diperluas = list(kata_kunci)
    for k in kata_kunci:
        kl = str(k).lower().strip()
        if kl in _SINONIM:
            diperluas.extend(_SINONIM[kl])
        for prefix in _PREFIX_BI:
            if kl.startswith(prefix) and len(kl) > len(prefix) + 2:
                akar = kl[len(prefix):]
                if akar not in diperluas:
                    diperluas.append(akar)
                if akar in _SINONIM:
                    diperluas.extend(_SINONIM[akar])
                break
    seen, hasil = set(), []
    for k in diperluas:
        k_norm = str(k).lower().strip()
        if k_norm and k_norm not in seen:
            seen.add(k_norm)
            hasil.append(k_norm)
    return hasil


def _bersihkan_kata_kunci(kata_kunci):
    """Hapus stopwords dan kata pendek dari list kata_kunci."""
    bersih = []
    for k in kata_kunci or []:
        k = str(k).strip().lower()
        # Filter kata kosong, terlalu pendek (< 3 char), atau stopword
        if not k or len(k) < 3 or k in _STOPWORDS:
            continue
        if k not in bersih:
            bersih.append(k)
    return bersih


def cari_arsip_berdasarkan_intent(pengguna_id, intent, batas=10):
    """Bangun query dari intent lalu kembalikan daftar berkas relevan.

    Strategi berlapis agar pencarian tidak pernah "kosong" tanpa alasan:
      1) Pencarian penuh (semua filter dari intent).
      2) Jatuhkan filter tipe_file & kategori (sering ditebak salah AI).
      3) Pecah setiap kata kunci menjadi kata individual.
      4) Pencarian fuzzy: potongan kata >= 3 huruf.

    Setiap lapis hanya dijalankan bila lapis sebelumnya menghasilkan 0 baris.
    """
    # Lapis 1: Full filter.
    hasil = _jalankan_query(pengguna_id, intent, batas)
    if hasil:
        return hasil

    kata_kunci = intent.get("kata_kunci") or []

    # Lapis 2: Hapus tipe_file & kategori, pertahankan kata kunci & tanggal.
    if kata_kunci:
        intent_lunak = dict(intent)
        intent_lunak["tipe_file"] = None
        intent_lunak["kategori"] = None
        hasil = _jalankan_query(pengguna_id, intent_lunak, batas)
        if hasil:
            return hasil

    # Lapis 3: Pecah frasa menjadi kata individual.
    # Contoh: ["laporan keuangan"] -> ["laporan", "keuangan"]
    if kata_kunci:
        kata_pecah = []
        for kk in kata_kunci:
            for bagian in str(kk).split():
                bagian = bagian.strip()
                if bagian and bagian not in kata_pecah:
                    kata_pecah.append(bagian)
        if kata_pecah != kata_kunci:
            intent_pecah = dict(intent)
            intent_pecah["kata_kunci"] = kata_pecah
            intent_pecah["tipe_file"] = None
            intent_pecah["kategori"] = None
            hasil = _jalankan_query(pengguna_id, intent_pecah, batas)
            if hasil:
                return hasil

    # Lapis 4: Pencarian fuzzy — cari potongan kata minimal 3 karakter.
    if kata_kunci:
        potongan = []
        for kk in kata_kunci:
            for bagian in str(kk).split():
                bagian = bagian.strip().lower()
                if len(bagian) >= 3 and bagian not in potongan:
                    potongan.append(bagian)
        if potongan:
            intent_fuzzy = {
                "kata_kunci": potongan,
                "tanggal_mulai": None,
                "tanggal_selesai": None,
                "tipe_file": None,
                "kategori": None,
            }
            hasil = _jalankan_query(pengguna_id, intent_fuzzy, batas)
            if hasil:
                return hasil

    return []


def _jalankan_query(pengguna_id, intent, batas):
    query = Berkas.query.filter(
        Berkas.pengguna_id == pengguna_id, Berkas.dihapus_pada.is_(None)
    )

    # Filter stopwords agar kata generik tidak meluas hasil ke semua file.
    # Mis. "foto bermasker" -> ["masker"] (kata "foto" sudah jadi tipe_file).
    kata_kunci = _bersihkan_kata_kunci(intent.get("kata_kunci") or [])
    # Ekspansi sinonim BI: "cewek" → +["wanita","perempuan"], "berkacamata"
    # → +["kacamata"]. Menjembatani vocabulary gap antara query informal user
    # dan output vision yang kadang formal. Bersihkan stopword sekali lagi
    # karena ekspansi bisa menghasilkan kata yang masuk stopword.
    if kata_kunci:
        kata_kunci = _ekspansi_sinonim(kata_kunci)
        kata_kunci = _bersihkan_kata_kunci(kata_kunci)
    if kata_kunci:
        kondisi = []
        for kata in kata_kunci:
            pola = f"%{kata}%"
            # Cari di SEMUA kolom teks yang mungkin berisi informasi relevan.
            kondisi.append(Berkas.judul.ilike(pola))
            kondisi.append(Berkas.deskripsi.ilike(pola))
            kondisi.append(Berkas.ringkasan_ai.ilike(pola))
            kondisi.append(Berkas.nama_file_asli.ilike(pola))
            kondisi.append(Berkas.judul_ai.ilike(pola))
            kondisi.append(Berkas.teks_ekstraksi.ilike(pola))
            kondisi.append(Berkas.kategori_ai.ilike(pola))
            kondisi.append(Berkas.kode_arsip.ilike(pola))

        # Cocokkan juga lewat tag.
        query = query.outerjoin(Berkas.tag)
        for kata in kata_kunci:
            kondisi.append(Tag.nama.ilike(f"%{kata}%"))
        query = query.filter(db.or_(*kondisi))

    # Tipe file: hanya pakai filter bila nilai berasal dari daftar valid.
    # AI kadang mengarang nilai (mis. "teknologi") yang akan memblokir semua hasil.
    tipe = intent.get("tipe_file")
    if tipe and tipe in TIPE_BERKAS:
        query = query.filter(Berkas.tipe_file == tipe)

    # Kategori: hanya pakai filter bila kategori benar-benar ada di vault pengguna.
    kategori = intent.get("kategori")
    if kategori:
        ada = (
            Kategori.query.filter(
                Kategori.pengguna_id == pengguna_id,
                Kategori.nama.ilike(f"%{kategori}%"),
            )
            .first()
        )
        if ada is not None:
            query = query.join(Kategori, Berkas.kategori_id == Kategori.id).filter(
                Kategori.nama.ilike(f"%{kategori}%")
            )

    tgl_mulai = _baca_tanggal(intent.get("tanggal_mulai"))
    if tgl_mulai:
        query = query.filter(Berkas.tanggal_momen >= tgl_mulai)
    tgl_selesai = _baca_tanggal(intent.get("tanggal_selesai"))
    if tgl_selesai:
        query = query.filter(Berkas.tanggal_momen <= tgl_selesai)

    # ---- Skor relevansi sederhana untuk pengurutan yang lebih cerdas ----
    # File yang cocok di judul/judul_ai lebih relevan daripada cocok di teks_ekstraksi.
    #
    # CATATAN PostgreSQL: SELECT DISTINCT + ORDER BY computed expression bikin
    # error "ORDER BY expressions must appear in select list". SQLite tidak
    # strict, tapi Supabase Postgres tolak. Solusi: HAPUS .distinct(),
    # over-fetch hasil, lalu dedupe by id di Python (preserve order).
    if kata_kunci:
        skor_parts = []
        for kata in kata_kunci:
            pola = f"%{kata}%"
            skor_parts.append(case((Berkas.judul.ilike(pola), 4), else_=0))
            skor_parts.append(case((Berkas.judul_ai.ilike(pola), 4), else_=0))
            skor_parts.append(case((Berkas.ringkasan_ai.ilike(pola), 2), else_=0))
            skor_parts.append(case((Berkas.deskripsi.ilike(pola), 2), else_=0))
            skor_parts.append(case((Berkas.teks_ekstraksi.ilike(pola), 1), else_=0))
            skor_parts.append(case((Berkas.nama_file_asli.ilike(pola), 1), else_=0))

        skor_total = sum(skor_parts)
        rows = (
            query.order_by(skor_total.desc(), Berkas.tanggal_upload.desc())
            .limit(batas * 5)  # over-fetch untuk dedupe by id
            .all()
        )
        return _dedupe_preserve_order(rows, batas)

    rows = (
        query.order_by(Berkas.tanggal_upload.desc())
        .limit(batas * 5)
        .all()
    )
    return _dedupe_preserve_order(rows, batas)


def _dedupe_preserve_order(rows, batas):
    """Hapus duplikat berdasarkan id (dari outerjoin tag) sambil pertahankan urutan."""
    seen = set()
    unique = []
    for b in rows:
        if b.id not in seen:
            seen.add(b.id)
            unique.append(b)
            if len(unique) >= batas:
                break
    return unique


def _baca_tanggal(teks):
    if not teks:
        return None
    try:
        return datetime.strptime(str(teks).strip(), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None
