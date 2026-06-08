"""Chatbot pencarian arsip. Hanya menjawab berdasarkan hasil database.

Alur: baca intent (Groq) -> cari di database -> susun jawaban (Groq).
Jika Groq tidak tersedia, dipakai fallback pencarian kata kunci sederhana
agar fitur tetap berjalan saat demo tanpa API key.
"""

from app.extensions import db
from app.models import RiwayatChat, Berkas
from app.models.konstanta import TIPE_BERKAS
from app.services import layanan_groq, layanan_pencarian, layanan_log
from app.utils.format_tanggal import format_tanggal

_BATAS_HASIL = 10
_STOPWORD = {
    "yang", "dan", "atau", "saya", "aku", "apa", "saja", "ada", "di", "ke",
    "dari", "untuk", "tentang", "cari", "carikan", "tampilkan", "semua",
    "ini", "itu", "pada", "dengan", "adakah", "tolong", "mohon",
    "mana", "gimana", "bagaimana", "apakah", "berapa", "kapan", "bisa",
    "file", "arsip", "berkas", "dong", "deh", "kan", "nih", "tuh",
    "lihat", "lihatkan", "kasih", "minta", "gak", "tidak", "belum",
    "sudah", "lagi", "juga", "masih", "punya", "pernah", "kamu",
}

# Kata-kata yang menandai sapaan/ucapan terima kasih (fallback lokal saat Groq mati).
_KATA_SAPAAN = {
    "halo", "hallo", "hai", "hi", "hello", "hey", "hei",
    "pagi", "siang", "sore", "malam", "assalamualaikum", "assalamu'alaikum",
    "thanks", "thank", "makasih", "trims",
}
_FRASE_TERIMA_KASIH = ("terima kasih", "terimakasih", "thank you")
_FRASE_BANTUAN = (
    "apa yang bisa", "bisa apa", "fitur apa", "cara pakai", "cara menggunakan",
    "bagaimana cara", "kamu siapa", "siapa kamu", "kamu bisa apa",
    "help", "bantuan",
)


def proses_pertanyaan_chatbot(pengguna_id, pertanyaan):
    """Proses satu pertanyaan dan kembalikan dict {jawaban, berkas}."""
    pertanyaan = (pertanyaan or "").strip()
    if not pertanyaan:
        return {"jawaban": "Silakan tulis pertanyaan terlebih dahulu.", "berkas": []}

    intent = _ekstrak_intent(pertanyaan)
    jenis = (intent.get("jenis_intent") or "").lower()

    # Tangani sapaan/bantuan/tidak_jelas SEBELUM hit database.
    # Tidak perlu cari di DB dan tidak boleh kembalikan "tidak ditemukan".
    if jenis == "sapaan":
        jawaban = _jawaban_sapaan()
        _simpan_riwayat(pengguna_id, pertanyaan, jawaban, [])
        return {"jawaban": jawaban, "berkas": []}

    if jenis == "bantuan":
        jawaban = _jawaban_bantuan()
        _simpan_riwayat(pengguna_id, pertanyaan, jawaban, [])
        return {"jawaban": jawaban, "berkas": []}

    if jenis == "tidak_jelas" and not intent.get("kata_kunci"):
        jawaban = _jawaban_tidak_jelas()
        _simpan_riwayat(pengguna_id, pertanyaan, jawaban, [])
        return {"jawaban": jawaban, "berkas": []}

    # Alur pencarian normal
    hasil = layanan_pencarian.cari_arsip_berdasarkan_intent(
        pengguna_id, intent, _BATAS_HASIL
    )

    if not hasil:
        # ────────────────────────────────────────────────────────────────
        # FALLBACK SEMANTIK: keyword search 0 → minta AI baca konten file
        # terbaru dan tentukan mana yang relevan secara konsep.
        #
        # Pattern: LLM-as-retriever fallback (Pedro Alonso 2026,
        # ZeroEntropy 2025). Saat keyword bangkrut, kirim sample berkas
        # terbaru ke Groq, biar dia decide based on ringkasan_ai +
        # judul + tag yang sudah ada. Ini menyelamatkan kasus:
        # "cewek berkacamata" tidak match "wanita berjilbab kacamata"
        # secara literal tapi AI bisa decide they're the same concept.
        # ────────────────────────────────────────────────────────────────
        hasil_fallback = _fallback_semantik(pengguna_id, pertanyaan, intent)
        if hasil_fallback:
            hasil_final, jawaban_ai = _rerank_dan_jawab(
                pertanyaan, hasil_fallback
            )
            if hasil_final:
                _simpan_riwayat(
                    pengguna_id, pertanyaan, jawaban_ai, hasil_final
                )
                return {"jawaban": jawaban_ai, "berkas": hasil_final}

        # Fallback semantik juga 0 → baru kirim pesan "tidak ditemukan".
        kata = intent.get("kata_kunci") or []
        saran = ""
        if kata:
            saran = (
                f" Kata kunci yang dicari: {', '.join(kata)}. "
                "Coba:\n• Gunakan kata kunci yang lebih umum atau singkat\n"
                "• Periksa ejaan kata kunci\n"
                "• Hapus filter tanggal jika menggunakan rentang waktu\n"
                "• Pastikan file sudah pernah diunggah ke Gonanku"
            )
        jawaban = (
            "Maaf, arsip yang kamu cari tidak ditemukan di Gonanku."
            + saran
        )
        _simpan_riwayat(pengguna_id, pertanyaan, jawaban, [])
        return {"jawaban": jawaban, "berkas": []}

    # SEMANTIC RE-RANK: AI nilai kandidat keyword search lalu pilih yang
    # benar-benar relevan dengan maksud pengguna (anti "semua foto buku
    # muncul saat user cari foto bermasker").
    hasil_final, jawaban = _rerank_dan_jawab(pertanyaan, hasil)
    _simpan_riwayat(pengguna_id, pertanyaan, jawaban, hasil_final)
    return {"jawaban": jawaban, "berkas": hasil_final}


_BATAS_FALLBACK = 30  # Berapa berkas terbaru yang dikirim ke AI saat fallback


def _fallback_semantik(pengguna_id, pertanyaan, intent):
    """Ambil berkas terbaru untuk dikirim ke AI sebagai kandidat semantik.

    Dipakai HANYA saat keyword search return 0 hasil. Tujuannya: kasih AI
    kesempatan baca isi berkas dan decide secara konsep, bukan literal match.

    Filter:
    - Berkas user, belum dihapus
    - Jika intent.tipe_file valid → filter tipe (jaga konteks)
    - Order desc tanggal_upload → 30 terbaru saja (latency reasonable)
    """
    q = Berkas.query.filter(
        Berkas.pengguna_id == pengguna_id,
        Berkas.dihapus_pada.is_(None),
    )
    tipe = (intent or {}).get("tipe_file")
    if tipe and tipe in TIPE_BERKAS:
        q = q.filter(Berkas.tipe_file == tipe)

    return q.order_by(Berkas.tanggal_upload.desc()).limit(_BATAS_FALLBACK).all()


def _rerank_dan_jawab(pertanyaan, kandidat):
    """Pakai AI untuk re-rank kandidat keyword search + susun jawaban.

    Hanya dipakai bila ada kandidat. Bila AI gagal/timeout, fallback ke
    perilaku lama (tampilkan semua kandidat + jawaban legacy).
    Return (hasil_terfilter, jawaban).
    """
    if not kandidat:
        return [], ""

    # Bangun ringkasan kandidat untuk AI
    payload = []
    for b in kandidat:
        payload.append({
            "id": b.id,
            "judul": b.judul,
            "tipe_file": b.tipe_file,
            "kategori": b.kategori.nama if b.kategori else None,
            "ringkasan": (b.ringkasan_ai or "")[:300],
            "tanggal": format_tanggal(b.tanggal_momen) if b.tanggal_momen else None,
        })

    try:
        out = layanan_groq.pilih_dan_susun_jawaban(pertanyaan, payload)
        ids_pilih = out["ids_relevan"]
        jawaban = out["jawaban"]
    except layanan_groq.GagalGroq:
        # Fallback: tampilkan semua + jawaban legacy
        return kandidat, _susun_jawaban(pertanyaan, kandidat)

    if not ids_pilih:
        # AI menilai TIDAK ADA yang relevan walaupun keyword match.
        if not jawaban:
            jawaban = (
                "Maaf, ada beberapa file yang cocok kata kunci tapi tidak ada "
                "yang benar-benar sesuai dengan maksud pertanyaanmu. Coba "
                "gunakan kata kunci lain atau lebih spesifik."
            )
        return [], jawaban

    # Filter kandidat sesuai pilihan AI, pertahankan urutan asli (paling relevan dulu)
    by_id = {b.id: b for b in kandidat}
    hasil_terfilter = [by_id[i] for i in ids_pilih if i in by_id]
    if not jawaban:
        jawaban = _susun_jawaban(pertanyaan, hasil_terfilter)
    return hasil_terfilter, jawaban


def _jawaban_sapaan():
    return (
        "Halo! 👋 Aku Gonanku, asisten pencari arsip pribadimu. "
        "Coba tanyakan sesuatu seperti \"tampilkan bukti pembayaran\" "
        "atau \"cari foto wisuda\"."
    )


def _jawaban_bantuan():
    return (
        "Aku membantumu menemukan file di vault Gonanku. 🗂️ "
        "Beberapa hal yang bisa kamu coba:\n"
        "• 🔍 Cari berdasarkan kata kunci — \"cari dokumen kuliah\"\n"
        "• 📸 Filter berdasarkan tipe — \"tampilkan semua foto\"\n"
        "• 📂 Filter berdasarkan kategori — \"bukti pembayaran bulan ini\"\n"
        "• 📅 Cari berdasarkan rentang tanggal — \"arsip di bulan juni\"\n"
        "• 🏷️ Cari berdasarkan tag — \"file tentang skripsi\"\n\n"
        "Kamu juga bisa menggabungkan filter, misalnya: "
        "\"foto wisuda bulan lalu\" atau \"dokumen keuangan 2025\"."
    )


def _jawaban_tidak_jelas():
    return (
        "Maaf, aku belum paham maksudmu. Coba tulis pertanyaan pencarian, misalnya "
        "\"cari foto wisuda\" atau \"tampilkan dokumen kuliah\"."
    )


def _deteksi_intent_lokal(pertanyaan):
    """Klasifikasi cepat tanpa Groq (untuk fallback)."""
    teks = pertanyaan.lower().strip(" !?.,")
    if teks in _KATA_SAPAAN or any(f in teks for f in _FRASE_TERIMA_KASIH):
        return "sapaan"
    # Sapaan multi-kata pendek mis. "selamat pagi", "hai gonanku"
    kata_awal = teks.split()
    if kata_awal and kata_awal[0] in _KATA_SAPAAN and len(kata_awal) <= 3:
        return "sapaan"
    if any(f in teks for f in _FRASE_BANTUAN):
        return "bantuan"
    return "pencarian"


def _ekstrak_intent(pertanyaan):
    """Coba Groq untuk intent; fallback ke deteksi lokal bila Groq gagal."""
    try:
        return layanan_groq.baca_intent_pertanyaan(pertanyaan)
    except layanan_groq.GagalGroq:
        jenis_lokal = _deteksi_intent_lokal(pertanyaan)
        return {
            "jenis_intent": jenis_lokal,
            "kata_kunci": _kata_kunci_sederhana(pertanyaan) if jenis_lokal == "pencarian" else [],
            "tanggal_mulai": None,
            "tanggal_selesai": None,
            "kategori": None,
            "tipe_file": None,
        }


def _kata_kunci_sederhana(pertanyaan):
    kata = [k.strip(".,?!").lower() for k in pertanyaan.split()]
    return [k for k in kata if len(k) > 3 and k not in _STOPWORD] or [pertanyaan]


def _susun_jawaban(pertanyaan, hasil):
    ringkasan = _ringkas_hasil(hasil)
    try:
        return layanan_groq.susun_jawaban_chatbot(pertanyaan, ringkasan)
    except layanan_groq.GagalGroq:
        return f"Ditemukan {len(hasil)} arsip yang relevan dengan pencarianmu."


def _ringkas_hasil(hasil):
    """Buat ringkasan teks daftar file untuk konteks jawaban AI.

    Semakin kaya informasi yang diberikan ke AI, semakin akurat dan
    lengkap jawaban yang dihasilkan. Sertakan semua metadata yang
    tersedia agar AI bisa memberikan jawaban informatif.
    """
    baris = []
    for i, b in enumerate(hasil, 1):
        kategori = b.kategori.nama if b.kategori else "Tanpa kategori"
        # Kumpulkan tag yang terkait.
        try:
            tag_list = [t.nama for t in b.tag.all()] if b.tag else []
        except Exception:
            tag_list = []
        tag_str = ", ".join(tag_list) if tag_list else "-"

        # Ambil cuplikan teks_ekstraksi jika ada (maks 200 karakter).
        cuplikan_teks = ""
        if b.teks_ekstraksi:
            cuplikan_teks = b.teks_ekstraksi[:200].replace("\n", " ").strip()

        bagian = (
            f"{i}. Judul: {b.judul}\n"
            f"   File asli: {b.nama_file_asli}\n"
            f"   Tipe: {b.tipe_file} | Kategori: {kategori}\n"
            f"   Tanggal momen: {format_tanggal(b.tanggal_momen)}\n"
            f"   Upload: {format_tanggal(b.tanggal_upload)}\n"
            f"   Tag: {tag_str}\n"
            f"   Ringkasan AI: {b.ringkasan_ai or '-'}"
        )
        if cuplikan_teks:
            bagian += f"\n   Cuplikan isi: {cuplikan_teks}"
        if b.judul_ai and b.judul_ai != b.judul:
            bagian += f"\n   Judul AI: {b.judul_ai}"

        baris.append(bagian)
    return "\n\n".join(baris)


def _simpan_riwayat(pengguna_id, pertanyaan, jawaban, hasil):
    riwayat = RiwayatChat(
        pengguna_id=pengguna_id,
        pertanyaan=pertanyaan,
        jawaban=jawaban,
        berkas_hasil=",".join(str(b.id) for b in hasil) or None,
    )
    db.session.add(riwayat)
    layanan_log.catat_aktivitas(pengguna_id, "chat", f"Bertanya: {pertanyaan[:80]}")
    db.session.commit()


def ambil_riwayat_chat(pengguna_id, batas=30):
    return (
        RiwayatChat.query.filter_by(pengguna_id=pengguna_id)
        .order_by(RiwayatChat.dibuat_pada.desc())
        .limit(batas)
        .all()
    )


def hapus_riwayat_chat(pengguna_id, riwayat_id):
    riwayat = RiwayatChat.query.filter_by(
        id=riwayat_id, pengguna_id=pengguna_id
    ).first()
    if riwayat is None:
        return False
    db.session.delete(riwayat)
    db.session.commit()
    return True
