// Chatbot Gonanku — ChatGPT-style UX:
// - Buka chat = fresh state (cuma sapaan)
// - Riwayat di sidebar, klik untuk lihat percakapan (load on-demand)
// - "Chat Baru" reset area pesan (DB tidak disentuh)
// - Hemat memory: tidak load semua percakapan saat page load
(function () {
  const form = document.getElementById("form-chat");
  const input = document.getElementById("input-pertanyaan");
  const area = document.getElementById("area-pesan");
  const tombol = document.getElementById("tombol-kirim");
  const tombolChatBaru = document.getElementById("tombol-chat-baru");
  const listRiwayat = document.getElementById("list-riwayat");
  const infoMode = document.getElementById("info-mode-chat");

  if (!form || !area) return;

  // CSRF token dari meta tag (di-set oleh layout.html). Wajib dikirim
  // pada semua request POST AJAX agar Flask-WTF CSRFProtect lolos.
  const CSRF_TOKEN =
    document.querySelector('meta[name="csrf-token"]')?.content || "";

  // ── Helper DOM ──
  function buatElemen(kelas, isi) {
    const el = document.createElement("div");
    el.className = kelas;
    if (isi !== undefined) el.textContent = isi;
    return el;
  }
  function gulirBawah() {
    area.scrollTop = area.scrollHeight;
  }
  function bersihkanArea() {
    area.innerHTML = "";
  }

  // ── Render pesan ──
  function tambahPesanPengguna(teks) {
    area.appendChild(buatElemen("pesan pengguna", teks));
  }

  function tambahKartuFile(induk, daftar) {
    if (!daftar || !daftar.length) return;
    const wadah = buatElemen("kartu-hasil");
    daftar.forEach((b) => {
      const kartu = buatElemen("kartu-file");
      const kiri = buatElemen("div");
      const judul = buatElemen("div", b.judul);
      judul.className = "judul";
      const meta = buatElemen(
        "div",
        [b.kode_arsip, b.tipe_file, b.kategori || "Tanpa kategori"].join(" · ")
      );
      meta.className = "meta";
      kiri.appendChild(judul);
      kiri.appendChild(meta);

      const aksi = buatElemen("div");
      aksi.className = "aksi-baris";
      const detail = document.createElement("a");
      detail.className = "tautan-aksi";
      detail.href = b.url_detail;
      detail.textContent = "Detail";
      aksi.appendChild(detail);
      if (b.url_telegram) {
        const tg = document.createElement("a");
        tg.className = "tautan-aksi";
        tg.href = b.url_telegram;
        tg.target = "_blank";
        tg.rel = "noopener";
        tg.textContent = "Telegram";
        aksi.appendChild(tg);
      }
      kartu.appendChild(kiri);
      kartu.appendChild(aksi);
      wadah.appendChild(kartu);
    });
    induk.appendChild(wadah);
  }

  function tambahJawabanBot(jawaban, berkas) {
    const bubble = buatElemen("pesan bot");
    bubble.textContent = jawaban || "";
    if (berkas && berkas.length) tambahKartuFile(bubble, berkas);
    area.appendChild(bubble);
  }

  function tambahPesanSapaan() {
    const bubble = buatElemen("pesan bot");
    bubble.innerHTML =
      'Halo! 👋 Aku Gonanku, asisten pencari arsip pribadimu. Coba tanyakan ' +
      'sesuatu, misalnya <em>"tampilkan bukti pembayaran"</em> atau ' +
      '<em>"cari dokumen kuliah"</em>.';
    area.appendChild(bubble);
  }

  // ── Mode state ──
  function setActiveRiwayat(id) {
    listRiwayat.querySelectorAll(".riwayat-item").forEach((li) => {
      li.classList.toggle("aktif", li.dataset.id === String(id));
    });
  }

  function modeChatBaru() {
    bersihkanArea();
    tambahPesanSapaan();
    setActiveRiwayat(null);
    if (infoMode) infoMode.textContent = "Sesi chat baru. Tanyakan sesuatu di bawah.";
    input.focus();
  }

  function modeLihatRiwayat(tanggal) {
    if (infoMode) {
      infoMode.textContent = "Melihat percakapan dari " + (tanggal || "riwayat") +
        ". Tulis pertanyaan baru untuk memulai sesi baru.";
    }
  }

  // ── Load percakapan dari riwayat (on-demand AJAX) ──
  async function bukaRiwayat(id) {
    try {
      const resp = await fetch(window.URL_CHAT_RIWAYAT + "/" + id);
      if (!resp.ok) throw new Error("Gagal memuat riwayat");
      const data = await resp.json();
      bersihkanArea();
      tambahPesanPengguna(data.pertanyaan);
      tambahJawabanBot(data.jawaban, data.berkas);
      setActiveRiwayat(id);
      modeLihatRiwayat(data.tanggal);
      gulirBawah();
    } catch (e) {
      alert("Gagal memuat riwayat. Coba lagi.");
    }
  }

  async function hapusRiwayat(id, liElement) {
    if (!confirm("Hapus entri riwayat ini?")) return;
    try {
      const resp = await fetch(window.URL_CHAT_HAPUS + "/" + id + "/hapus", {
        method: "POST",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": CSRF_TOKEN,
        },
      });
      if (resp.ok) {
        liElement.remove();
        // Kalau yang dihapus sedang aktif, reset ke chat baru
        if (liElement.classList.contains("aktif")) modeChatBaru();
        // Kalau list jadi kosong, tampilkan placeholder
        if (listRiwayat.children.length === 0) {
          const li = document.createElement("li");
          li.className = "riwayat-kosong";
          li.innerHTML = '<p class="subjudul">Belum ada riwayat. Ajukan pertanyaan untuk memulai.</p>';
          listRiwayat.appendChild(li);
        }
      }
    } catch (e) { /* silent fail */ }
  }

  // ── Tambah item riwayat baru di sidebar setelah submit pertanyaan ──
  function tambahItemRiwayat(id, pertanyaan, tanggal) {
    // Kalau placeholder "kosong" ada, hapus dulu
    const kosong = listRiwayat.querySelector(".riwayat-kosong");
    if (kosong) kosong.remove();

    const li = document.createElement("li");
    li.className = "riwayat-item";
    li.dataset.id = id;
    li.title = pertanyaan + " · " + (tanggal || "");
    li.innerHTML = `
      <button type="button" class="riwayat-btn" data-id="${id}">
        <i class="ri-chat-3-line"></i>
        <span class="riwayat-judul">${pertanyaan.length > 50 ? pertanyaan.slice(0, 50) + "…" : pertanyaan}</span>
      </button>
      <button type="button" class="riwayat-hapus" data-id="${id}" title="Hapus riwayat ini">
        <i class="ri-close-line"></i>
      </button>
    `;
    listRiwayat.insertBefore(li, listRiwayat.firstChild);
  }

  // ── Kirim pertanyaan baru ──
  async function kirimPertanyaan(pertanyaan) {
    // Kalau sedang lihat riwayat, otomatis mulai sesi baru saat user kirim
    if (area.querySelector(".pesan.pengguna") && !document.querySelector(".riwayat-item.aktif:last-child")) {
      // sudah di mode chat baru, lanjut append
    } else if (document.querySelector(".riwayat-item.aktif")) {
      bersihkanArea();
      setActiveRiwayat(null);
    }

    tambahPesanPengguna(pertanyaan);
    gulirBawah();

    const bubble = buatElemen("pesan bot");
    bubble.innerHTML = '<span class="pemuat"></span> Mencari arsip...';
    area.appendChild(bubble);
    gulirBawah();

    tombol.disabled = true;
    try {
      const data = new URLSearchParams();
      data.append("pertanyaan", pertanyaan);
      const resp = await fetch(window.URL_CHAT_TANYA, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
          "X-CSRFToken": CSRF_TOKEN,
        },
        body: data,
      });
      const hasil = await resp.json();
      bubble.textContent = hasil.jawaban;
      tambahKartuFile(bubble, hasil.berkas);

      // Tambah ke sidebar riwayat
      if (hasil.riwayat_id) {
        tambahItemRiwayat(hasil.riwayat_id, pertanyaan, hasil.riwayat_tanggal);
      }
      if (infoMode) infoMode.textContent = "Sesi chat live. Tanyakan apa pun, riwayat tersimpan otomatis.";
    } catch (e) {
      bubble.textContent = "Maaf, terjadi kendala saat memproses pertanyaan.";
    } finally {
      tombol.disabled = false;
      gulirBawah();
    }
  }

  // ── Event listeners ──
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const p = input.value.trim();
    if (!p) return;
    input.value = "";
    kirimPertanyaan(p);
  });

  document.querySelectorAll(".saran").forEach((btn) => {
    btn.addEventListener("click", () => {
      input.value = btn.textContent.trim();
      form.requestSubmit();
    });
  });

  if (tombolChatBaru) {
    tombolChatBaru.addEventListener("click", modeChatBaru);
  }

  // Klik item riwayat → load percakapan
  // Pakai event delegation supaya item baru pun otomatis ter-handle
  listRiwayat.addEventListener("click", (e) => {
    const btnHapus = e.target.closest(".riwayat-hapus");
    if (btnHapus) {
      e.stopPropagation();
      const li = btnHapus.closest(".riwayat-item");
      hapusRiwayat(btnHapus.dataset.id, li);
      return;
    }
    const btnBuka = e.target.closest(".riwayat-btn");
    if (btnBuka) {
      bukaRiwayat(btnBuka.dataset.id);
    }
  });
})();
