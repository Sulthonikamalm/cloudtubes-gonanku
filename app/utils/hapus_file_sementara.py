import os


def hapus_file_sementara(path):
    """Hapus file sementara dari server. Aman dipanggil walau file tidak ada.

    File asli hanya boleh berada di Telegram, tidak permanen di server.
    """
    if not path:
        return
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        # Kegagalan menghapus file temporary tidak boleh menggagalkan respons.
        pass
