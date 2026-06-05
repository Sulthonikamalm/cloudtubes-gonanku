// Interaksi halaman upload: drag & drop multi-file, preview daftar,
// validasi jumlah client-side, dan loading state batch.
(function () {
  const dropzone = document.getElementById("dropzone");
  const input = document.getElementById("input-file");
  const daftarPreview = document.getElementById("daftar-preview");
  const listPreview = document.getElementById("list-preview");
  const ringkasanPreview = document.getElementById("ringkasan-preview");
  const jumlahPreview = document.getElementById("jumlah-preview");
  const tombolBersihkan = document.getElementById("bersihkan-preview");
  const form = document.getElementById("form-upload");
  const tombol = document.getElementById("tombol-upload");

  if (!dropzone || !input) return;

  // Batas batch dibaca dari atribut hint di template (atau default aman).
  const BATAS_FOTO = 15;
  const BATAS_DOK = 10;

  const EKSTENSI_FOTO = new Set(["jpg", "jpeg", "png", "gif", "webp", "bmp", "heic"]);
  const EKSTENSI_VIDEO = new Set(["mp4", "mov", "mkv", "avi", "webm", "3gp"]);
  const EKSTENSI_AUDIO = new Set(["mp3", "wav", "ogg", "m4a", "aac", "flac"]);
  const EKSTENSI_DOK = new Set(["pdf", "doc", "docx", "txt", "rtf", "xls", "xlsx", "ppt", "pptx", "csv", "md"]);

  function formatUkuran(byte) {
    const satuan = ["B", "KB", "MB", "GB"];
    let i = 0;
    let nilai = byte;
    while (nilai >= 1024 && i < satuan.length - 1) {
      nilai /= 1024;
      i++;
    }
    return (i === 0 ? nilai : nilai.toFixed(1)) + " " + satuan[i];
  }

  function ekstensi(nama) {
    const i = nama.lastIndexOf(".");
    return i >= 0 ? nama.slice(i + 1).toLowerCase() : "";
  }

  function ikonTipe(ext, nama) {
    if (EKSTENSI_FOTO.has(ext)) {
      const nl = nama.toLowerCase();
      if (nl.includes("screenshot") || nl.includes("screen shot")) return "ri-screenshot-line";
      return "ri-image-line";
    }
    if (EKSTENSI_VIDEO.has(ext)) return "ri-video-line";
    if (EKSTENSI_AUDIO.has(ext)) return "ri-music-2-line";
    if (EKSTENSI_DOK.has(ext)) return "ri-file-text-line";
    return "ri-file-line";
  }

  function isFoto(ext, nama) {
    return EKSTENSI_FOTO.has(ext);
  }

  function render(files) {
    listPreview.innerHTML = "";
    if (!files.length) {
      daftarPreview.hidden = true;
      return;
    }
    daftarPreview.hidden = false;
    jumlahPreview.textContent = files.length;

    let totalUkuran = 0;
    let nFoto = 0, nDok = 0;

    Array.from(files).forEach((f, idx) => {
      const ext = ekstensi(f.name);
      totalUkuran += f.size;
      if (isFoto(ext, f.name)) nFoto++;
      else nDok++;

      const li = document.createElement("li");
      li.className = "item-preview";
      li.innerHTML = `
        <i class="${ikonTipe(ext, f.name)}"></i>
        <div class="info">
          <div class="nama">${f.name}</div>
          <div class="meta">${formatUkuran(f.size)}</div>
        </div>
        <button type="button" class="hapus-item" data-idx="${idx}" aria-label="Hapus dari batch">
          <i class="ri-close-line"></i>
        </button>
      `;
      listPreview.appendChild(li);
    });

    // Ringkasan + status batas
    const pesan = [];
    pesan.push(`Total ${formatUkuran(totalUkuran)}`);
    if (nFoto) pesan.push(`${nFoto} foto/screenshot`);
    if (nDok) pesan.push(`${nDok} dokumen/lainnya`);

    let warn = "";
    if (nFoto > BATAS_FOTO) warn = `⚠ Melebihi batas ${BATAS_FOTO} foto. Kurangi sebelum upload.`;
    else if (nDok > BATAS_DOK) warn = `⚠ Melebihi batas ${BATAS_DOK} dokumen. Kurangi sebelum upload.`;

    ringkasanPreview.innerHTML =
      `<span>${pesan.join(" · ")}</span>` +
      (warn ? `<span class="batas-warn">${warn}</span>` : "");

    tombol.disabled = !!warn;
  }

  // DataTransfer untuk akumulasi file (saat user pilih beberapa kali / drag berkali-kali)
  let kumpulan = new DataTransfer();

  function gabungkan(filesBaru) {
    Array.from(filesBaru).forEach((f) => kumpulan.items.add(f));
    input.files = kumpulan.files;
    render(input.files);
  }

  function hapusIndex(idx) {
    const baru = new DataTransfer();
    Array.from(kumpulan.files).forEach((f, i) => {
      if (i !== idx) baru.items.add(f);
    });
    kumpulan = baru;
    input.files = kumpulan.files;
    render(input.files);
  }

  function bersihkan() {
    kumpulan = new DataTransfer();
    input.files = kumpulan.files;
    render(input.files);
  }

  dropzone.addEventListener("click", () => input.click());

  input.addEventListener("change", () => {
    if (input.files.length) gabungkan(input.files);
  });

  ["dragover", "dragenter"].forEach((ev) =>
    dropzone.addEventListener(ev, (e) => {
      e.preventDefault();
      dropzone.classList.add("aktif");
    })
  );
  ["dragleave", "drop"].forEach((ev) =>
    dropzone.addEventListener(ev, (e) => {
      e.preventDefault();
      dropzone.classList.remove("aktif");
    })
  );
  dropzone.addEventListener("drop", (e) => {
    if (e.dataTransfer.files.length) gabungkan(e.dataTransfer.files);
  });

  listPreview.addEventListener("click", (e) => {
    const btn = e.target.closest(".hapus-item");
    if (!btn) return;
    hapusIndex(parseInt(btn.dataset.idx, 10));
  });

  tombolBersihkan.addEventListener("click", bersihkan);

  // Loading state saat upload batch (sequential di backend, bisa beberapa detik per file).
  form.addEventListener("submit", (e) => {
    if (!input.files.length) {
      e.preventDefault();
      return;
    }
    tombol.disabled = true;
    tombol.innerHTML = `<span class="pemuat"></span> Mengunggah ${input.files.length} file...`;
  });
})();
