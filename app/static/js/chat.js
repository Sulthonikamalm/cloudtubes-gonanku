// Chatbot: kirim pertanyaan ke backend dan tampilkan jawaban + kartu file.
(function () {
  const form = document.getElementById("form-chat");
  const input = document.getElementById("input-pertanyaan");
  const area = document.getElementById("area-pesan");
  const tombol = document.getElementById("tombol-kirim");

  if (!form || !area) return;

  function buatElemen(kelas, isi) {
    const el = document.createElement("div");
    el.className = kelas;
    if (isi !== undefined) el.textContent = isi;
    return el;
  }

  function gulirBawah() {
    area.scrollTop = area.scrollHeight;
  }

  function tambahPesanPengguna(teks) {
    area.appendChild(buatElemen("pesan pengguna", teks));
    gulirBawah();
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
      const tautanDetail = document.createElement("a");
      tautanDetail.className = "tautan-aksi";
      tautanDetail.href = b.url_detail;
      tautanDetail.textContent = "Detail";
      aksi.appendChild(tautanDetail);
      if (b.url_telegram) {
        const tautanTg = document.createElement("a");
        tautanTg.className = "tautan-aksi";
        tautanTg.href = b.url_telegram;
        tautanTg.target = "_blank";
        tautanTg.rel = "noopener";
        tautanTg.textContent = "Telegram";
        aksi.appendChild(tautanTg);
      }

      kartu.appendChild(kiri);
      kartu.appendChild(aksi);
      wadah.appendChild(kartu);
    });
    induk.appendChild(wadah);
  }

  async function kirimPertanyaan(pertanyaan) {
    tambahPesanPengguna(pertanyaan);

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
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: data,
      });
      const hasil = await resp.json();
      bubble.textContent = hasil.jawaban;
      tambahKartuFile(bubble, hasil.berkas);
    } catch (e) {
      bubble.textContent = "Maaf, terjadi kendala saat memproses pertanyaan.";
    } finally {
      tombol.disabled = false;
      gulirBawah();
    }
  }

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const pertanyaan = input.value.trim();
    if (!pertanyaan) return;
    input.value = "";
    kirimPertanyaan(pertanyaan);
  });

  document.querySelectorAll(".saran").forEach((btn) => {
    btn.addEventListener("click", () => {
      input.value = btn.textContent.trim();
      form.requestSubmit();
    });
  });
})();
