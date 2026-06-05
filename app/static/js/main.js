// Gonanku - main.js
// Sidebar expand/collapse (desktop) + drawer slide-in (mobile) + theme toggling.

(function () {
  // ── Theme Switcher (Runs everywhere: layout and login) ──
  const toggleTemaBtn = document.getElementById('toggle-tema');
  const ikonTema = document.getElementById('ikon-tema');
  const TEMA_KUNCI = 'gonanku-tema';

  function updateIkonTema(isLight) {
    if (!ikonTema) return;
    if (isLight) {
      ikonTema.className = 'ri-moon-line';
    } else {
      ikonTema.className = 'ri-sun-line';
    }
  }

  // Set initial icon on load
  const isCurrentlyLight = document.documentElement.classList.contains('tema-terang');
  updateIkonTema(isCurrentlyLight);

  if (toggleTemaBtn) {
    toggleTemaBtn.addEventListener('click', function () {
      const isLight = document.documentElement.classList.toggle('tema-terang');
      localStorage.setItem(TEMA_KUNCI, isLight ? 'light' : 'dark');
      updateIkonTema(isLight);
    });
  }

  // ── Sidebar logic (only runs if sidebar exists) ──
  const sidebar = document.getElementById('sidebar-utama');
  const toggleBtn = document.getElementById('toggle-sidebar');
  const burgerBtn = document.getElementById('toggle-mobile-sidebar');
  const backdrop = document.getElementById('backdrop-sidebar');
  const KUNCI = 'gonanku-sidebar-expanded';

  if (!sidebar) return;

  // Desktop sidebar expand/collapse
  if (toggleBtn) {
    const wasExpanded = localStorage.getItem(KUNCI) === 'true';
    if (wasExpanded) {
      sidebar.style.transition = 'none';
      sidebar.classList.add('expanded');
      sidebar.offsetHeight;
      sidebar.style.transition = '';
    }
    toggleBtn.addEventListener('click', function () {
      sidebar.classList.toggle('expanded');
      localStorage.setItem(KUNCI, sidebar.classList.contains('expanded'));
    });
  }

  // Mobile sidebar drawer
  function bukaDrawer() {
    sidebar.classList.add('terbuka');
    if (backdrop) backdrop.classList.add('tampil');
    document.body.style.overflow = 'hidden';
  }

  function tutupDrawer() {
    sidebar.classList.remove('terbuka');
    if (backdrop) backdrop.classList.remove('tampil');
    document.body.style.overflow = '';
  }

  if (burgerBtn) {
    burgerBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      if (sidebar.classList.contains('terbuka')) tutupDrawer();
      else bukaDrawer();
    });
  }

  if (backdrop) backdrop.addEventListener('click', tutupDrawer);

  sidebar.querySelectorAll('.nav-item').forEach(function (a) {
    a.addEventListener('click', function () {
      if (window.matchMedia('(max-width: 860px)').matches) tutupDrawer();
    });
  });

  window.addEventListener('resize', function () {
    if (window.innerWidth > 860 && sidebar.classList.contains('terbuka')) {
      tutupDrawer();
    }
  });

  // ── Crop Foto Profil Logic ──
  const inputFotoProfil = document.getElementById('input-foto-profil');
  const cropOverlay = document.getElementById('crop-modal-overlay');
  const cropTarget = document.getElementById('img-crop-target');
  const btnBatal = document.getElementById('btn-batal-crop');
  const btnTutup = document.getElementById('btn-tutup-crop');
  const btnSimpan = document.getElementById('btn-simpan-crop');
  const btnZoomIn = document.getElementById('btn-crop-zoom-in');
  const btnZoomOut = document.getElementById('btn-crop-zoom-out');
  const btnPutarKiri = document.getElementById('btn-crop-putar-kiri');
  const btnPutarKanan = document.getElementById('btn-crop-putar-kanan');
  
  let cropper = null;

  if (inputFotoProfil && cropOverlay && cropTarget) {
    inputFotoProfil.addEventListener('change', function (e) {
      const files = e.target.files;
      if (!files || files.length === 0) return;

      const file = files[0];
      const reader = new FileReader();

      reader.onload = function (event) {
        cropTarget.src = event.target.result;
        
        // Show overlay
        cropOverlay.classList.add('aktif');
        document.body.style.overflow = 'hidden';

        // Initialize Cropper
        if (cropper) {
          cropper.destroy();
        }

        cropper = new Cropper(cropTarget, {
          aspectRatio: 1,
          viewMode: 1,
          dragMode: 'move',
          autoCropArea: 0.8,
          restore: false,
          guides: false,
          center: true,
          highlight: false,
          cropBoxMovable: true,
          cropBoxResizable: true,
          toggleDragModeOnDblclick: false,
        });
      };

      reader.readAsDataURL(file);
    });

    function tutupCropModal() {
      cropOverlay.classList.remove('aktif');
      document.body.style.overflow = '';
      inputFotoProfil.value = ''; // Reset file input
      if (cropper) {
        cropper.destroy();
        cropper = null;
      }
    }

    if (btnBatal) btnBatal.addEventListener('click', tutupCropModal);
    if (btnTutup) btnTutup.addEventListener('click', tutupCropModal);

    if (btnZoomIn) {
      btnZoomIn.addEventListener('click', () => {
        if (cropper) cropper.zoom(0.1);
      });
    }

    if (btnZoomOut) {
      btnZoomOut.addEventListener('click', () => {
        if (cropper) cropper.zoom(-0.1);
      });
    }

    if (btnPutarKiri) {
      btnPutarKiri.addEventListener('click', () => {
        if (cropper) cropper.rotate(-90);
      });
    }

    if (btnPutarKanan) {
      btnPutarKanan.addEventListener('click', () => {
        if (cropper) cropper.rotate(90);
      });
    }

    if (btnSimpan) {
      btnSimpan.addEventListener('click', function () {
        if (!cropper) return;

        // Show loading state
        const teksTombol = btnSimpan.querySelector('.teks-tombol');
        const pemuat = btnSimpan.querySelector('.pemuat');
        if (teksTombol) teksTombol.style.display = 'none';
        if (pemuat) pemuat.style.display = 'inline-block';
        btnSimpan.disabled = true;

        cropper.getCroppedCanvas({
          width: 256,
          height: 256,
          imageSmoothingEnabled: true,
          imageSmoothingQuality: 'high',
        }).toBlob(function (blob) {
          if (!blob) {
            alert('Gagal memproses gambar.');
            tutupCropModal();
            return;
          }

          const formData = new FormData();
          formData.append('foto', blob, 'avatar.png');

          fetch('/profil/upload', {
            method: 'POST',
            body: formData
          })
          .then(response => {
            window.location.reload();
          })
          .catch(error => {
            console.error('Error uploading cropped image:', error);
            alert('Terjadi kesalahan saat mengunggah foto profil.');
            
            // Hide loading state
            if (teksTombol) teksTombol.style.display = 'inline';
            if (pemuat) pemuat.style.display = 'none';
            btnSimpan.disabled = false;
          });
        }, 'image/png');
      });
    }

    // Escape key handling for both modal and sidebar drawer
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        if (cropOverlay.classList.contains('aktif')) {
          tutupCropModal();
        } else if (sidebar.classList.contains('terbuka')) {
          tutupDrawer();
        }
      }
    });
  } else {
    // Normal Escape key fallback if not in page with profile upload
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && sidebar.classList.contains('terbuka')) tutupDrawer();
    });
  }
})();
