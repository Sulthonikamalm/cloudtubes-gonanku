// Upload Gonanku — per-file AJAX agar tiap request < 32 MiB (batas Cloud Run).
// Bonus: user lihat progress per file, retry per file, dan tidak ada lagi
// "Request Entity Too Large" untuk batch besar.
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

  const overlay = document.getElementById("overlay-progress");
  const judulProgress = document.getElementById("progress-judul");
  const counterProgress = document.getElementById("progress-counter");
  const barDalam = document.getElementById("bar-progress-dalam");
  const listProgress = document.getElementById("list-progress");
  const infoProgress = document.getElementById("progress-info");
  const aksiProgress = document.getElementById("progress-aksi");
  const tombolUploadLagi = document.getElementById("tombol-upload-lagi");

  if (!dropzone || !input) return;

  // CSRF token dari meta tag (di-set oleh layout.html). Wajib dikirim
  // pada semua request POST AJAX agar Flask-WTF CSRFProtect lolos.
  const CSRF_TOKEN =
    document.querySelector('meta[name="csrf-token"]')?.content || "";

  const BATAS_FOTO = 15;
  const BATAS_DOK = 10;
  const MAX_MB = window.MAX_FILE_MB || 30;

  const EKSTENSI_FOTO = new Set(["jpg", "jpeg", "png", "gif", "webp", "bmp", "heic"]);
  const EKSTENSI_VIDEO = new Set(["mp4", "mov", "mkv", "avi", "webm", "3gp"]);
  const EKSTENSI_AUDIO = new Set(["mp3", "wav", "ogg", "m4a", "aac", "flac"]);
  const EKSTENSI_DOK = new Set(["pdf", "doc", "docx", "txt", "rtf", "xls", "xlsx", "ppt", "pptx", "csv", "md"]);

  function formatUkuran(byte) {
    const satuan = ["B", "KB", "MB", "GB"];
    let i = 0, nilai = byte;
    while (nilai >= 1024 && i < satuan.length - 1) { nilai /= 1024; i++; }
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
  function isFoto(ext) { return EKSTENSI_FOTO.has(ext); }

  // ── Render preview list ──
  function render(files) {
    listPreview.innerHTML = "";
    if (!files.length) { daftarPreview.hidden = true; return; }
    daftarPreview.hidden = false;
    jumlahPreview.textContent = files.length;

    let totalUkuran = 0, nFoto = 0, nDok = 0, adaTerlaluBesar = false;
    Array.from(files).forEach((f, idx) => {
      const ext = ekstensi(f.name);
      totalUkuran += f.size;
      if (isFoto(ext)) nFoto++; else nDok++;
      const terlaluBesar = f.size > MAX_MB * 1024 * 1024;
      if (terlaluBesar) adaTerlaluBesar = true;

      const li = document.createElement("li");
      li.className = "item-preview" + (terlaluBesar ? " terlalu-besar" : "");
      li.innerHTML = `
        <i class="${ikonTipe(ext, f.name)}"></i>
        <div class="info">
          <div class="nama">${f.name}</div>
          <div class="meta">${formatUkuran(f.size)}${terlaluBesar ? ` · melebihi ${MAX_MB} MB` : ""}</div>
        </div>
        <button type="button" class="hapus-item" data-idx="${idx}" aria-label="Hapus">
          <i class="ri-close-line"></i>
        </button>
      `;
      listPreview.appendChild(li);
    });

    const pesan = [`Total ${formatUkuran(totalUkuran)}`];
    if (nFoto) pesan.push(`${nFoto} foto/screenshot`);
    if (nDok) pesan.push(`${nDok} dokumen/lainnya`);

    let warn = "";
    if (nFoto > BATAS_FOTO) warn = `⚠ Melebihi batas ${BATAS_FOTO} foto.`;
    else if (nDok > BATAS_DOK) warn = `⚠ Melebihi batas ${BATAS_DOK} dokumen.`;
    else if (adaTerlaluBesar) warn = `⚠ Ada file > ${MAX_MB} MB — hapus dulu.`;

    ringkasanPreview.innerHTML =
      `<span>${pesan.join(" · ")}</span>` +
      (warn ? `<span class="batas-warn">${warn}</span>` : "");

    tombol.disabled = !!warn;
  }

  // ── DataTransfer akumulator ──
  let kumpulan = new DataTransfer();
  function gabungkan(filesBaru) {
    Array.from(filesBaru).forEach((f) => kumpulan.items.add(f));
    input.files = kumpulan.files;
    render(input.files);
  }
  function hapusIndex(idx) {
    const baru = new DataTransfer();
    Array.from(kumpulan.files).forEach((f, i) => { if (i !== idx) baru.items.add(f); });
    kumpulan = baru;
    input.files = kumpulan.files;
    render(input.files);
  }
  function bersihkan() {
    kumpulan = new DataTransfer();
    input.files = kumpulan.files;
    render(input.files);
  }

  // ── Event drag-drop ──
  dropzone.addEventListener("click", () => input.click());
  input.addEventListener("change", () => { if (input.files.length) gabungkan(input.files); });
  ["dragover", "dragenter"].forEach((ev) =>
    dropzone.addEventListener(ev, (e) => { e.preventDefault(); dropzone.classList.add("aktif"); })
  );
  ["dragleave", "drop"].forEach((ev) =>
    dropzone.addEventListener(ev, (e) => { e.preventDefault(); dropzone.classList.remove("aktif"); })
  );
  dropzone.addEventListener("drop", (e) => {
    if (e.dataTransfer.files.length) gabungkan(e.dataTransfer.files);
  });
  listPreview.addEventListener("click", (e) => {
    const btn = e.target.closest(".hapus-item");
    if (btn) hapusIndex(parseInt(btn.dataset.idx, 10));
  });
  tombolBersihkan.addEventListener("click", bersihkan);

  // ── Bangun item progress ──
  function buatItemProgress(file, idx) {
    const li = document.createElement("li");
    li.className = "item-progress menunggu";
    li.dataset.idx = idx;
    li.innerHTML = `
      <i class="ikon-status ri-time-line"></i>
      <div class="info">
        <div class="nama">${file.name}</div>
        <div class="meta status-teks">Menunggu giliran...</div>
      </div>
    `;
    return li;
  }

  function setStatus(li, status, pesan) {
    li.classList.remove("menunggu", "proses", "sukses", "gagal");
    li.classList.add(status);
    const ikon = li.querySelector(".ikon-status");
    const teks = li.querySelector(".status-teks");
    const peta = {
      menunggu: ["ri-time-line", "Menunggu giliran..."],
      proses:   ["ri-loader-4-line spin", "Mengunggah ke Telegram + AI..."],
      sukses:   ["ri-check-line", pesan || "Berhasil"],
      gagal:    ["ri-error-warning-line", pesan || "Gagal"],
    };
    const [kelasIkon, pesanDefault] = peta[status] || peta.menunggu;
    ikon.className = "ikon-status " + kelasIkon;
    teks.textContent = pesanDefault;
  }

  // ── Upload satu file via fetch ──
  async function uploadSatu(file, metadata) {
    const data = new FormData();
    data.append("file", file);
    Object.keys(metadata).forEach((k) => data.append(k, metadata[k]));

    const resp = await fetch(window.URL_UNGGAH_SATU, {
      method: "POST",
      headers: { "X-CSRFToken": CSRF_TOKEN },
      body: data,
    });
    const text = await resp.text();
    let json;
    try { json = JSON.parse(text); } catch (e) { json = { ok: false, error: text.slice(0, 80) }; }
    if (!resp.ok && !json.error) json.error = `HTTP ${resp.status}`;
    return json;
  }

  // ── Submit utama: loop semua file ──
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!input.files.length) return;

    // Pre-validate ukuran per file
    const filesArr = Array.from(input.files);
    const terlaluBesar = filesArr.filter((f) => f.size > MAX_MB * 1024 * 1024);
    if (terlaluBesar.length) {
      alert(`Ada ${terlaluBesar.length} file > ${MAX_MB} MB. Hapus dulu.`);
      return;
    }

    const metadata = {
      judul: document.getElementById("judul").value,
      kategori_id: document.getElementById("kategori_id").value,
      tanggal_momen: document.getElementById("tanggal_momen").value,
      status_privasi: document.getElementById("status_privasi").value,
      tag: document.getElementById("tag").value,
      deskripsi: document.getElementById("deskripsi").value,
    };

    // Tampilkan overlay progress
    overlay.hidden = false;
    document.body.style.overflow = "hidden";
    listProgress.innerHTML = "";
    const items = filesArr.map((f, i) => {
      const li = buatItemProgress(f, i);
      listProgress.appendChild(li);
      return li;
    });

    const total = filesArr.length;
    let nSukses = 0, nGagal = 0;
    counterProgress.textContent = `0/${total}`;
    barDalam.style.width = "0%";
    judulProgress.textContent = `Mengunggah ${total} berkas...`;

    // Process sequential agar Telegram dan AI tidak overload
    for (let i = 0; i < filesArr.length; i++) {
      const li = items[i];
      setStatus(li, "proses");
      try {
        const hasil = await uploadSatu(filesArr[i], metadata);
        if (hasil.ok) {
          setStatus(li, "sukses", `${hasil.kode_arsip} · ${hasil.judul}`);
          nSukses++;
        } else {
          setStatus(li, "gagal", hasil.error || "Gagal upload");
          nGagal++;
        }
      } catch (e) {
        setStatus(li, "gagal", "Koneksi gagal");
        nGagal++;
      }

      const selesai = i + 1;
      counterProgress.textContent = `${selesai}/${total}`;
      barDalam.style.width = `${(selesai / total) * 100}%`;
    }

    // Finalisasi
    if (nGagal === 0) {
      judulProgress.textContent = `✓ ${nSukses} berkas berhasil diunggah`;
      infoProgress.textContent = "Semua file siap di vault Gonanku.";
    } else if (nSukses === 0) {
      judulProgress.textContent = `✗ Semua ${nGagal} berkas gagal`;
      infoProgress.textContent = "Cek pesan error di tiap file. Bisa coba upload ulang setelah memperbaiki.";
    } else {
      judulProgress.textContent = `${nSukses} berhasil, ${nGagal} gagal`;
      infoProgress.textContent = "File yang berhasil sudah tersimpan. File yang gagal bisa di-retry.";
    }
    aksiProgress.hidden = false;
  });

  if (tombolUploadLagi) {
    tombolUploadLagi.addEventListener("click", () => {
      overlay.hidden = true;
      document.body.style.overflow = "";
      aksiProgress.hidden = true;
      bersihkan();
    });
  }
})();
