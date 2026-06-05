# Nilai status dan tipe yang dipakai di seluruh aplikasi (sesuai PRD bagian 17).

TIPE_BERKAS = ["foto", "video", "dokumen", "audio", "screenshot", "lainnya"]

STATUS_BERKAS = ["aktif", "diarsipkan", "terhapus", "gagal_upload"]
STATUS_AI = ["menunggu", "diproses", "selesai", "gagal"]
STATUS_PRIVASI = ["normal", "penting", "sensitif", "rahasia"]

# Kategori bawaan yang dibuat saat akun pertama kali disiapkan.
KATEGORI_DEFAULT = [
    "Foto Pribadi",
    "Video Pribadi",
    "Dokumen Kuliah",
    "Screenshot Penting",
    "Bukti Pembayaran",
    "Catatan",
    "Tugas Besar",
    "Arsip Project",
    "Dokumen Sensitif",
    "Lainnya",
]

# Kategori penampung saat sebuah kategori dihapus.
KATEGORI_FALLBACK = "Lainnya"
