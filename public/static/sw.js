/**
 * Service Worker — Gonanku PWA Caching
 * ======================================
 * Menyimpan file statis (CSS, JS, font, gambar) di cache browser.
 * Pada kunjungan berikutnya, website akan dimuat secara instan
 * tanpa perlu menunggu server — meningkatkan Core Web Vitals secara drastis.
 */

const CACHE_NAME = 'gonanku-v1';

// Daftar file statis yang akan di-cache saat Service Worker pertama kali aktif.
// Hanya file publik (landing page) yang di-cache — halaman internal
// yang membutuhkan login tidak perlu di-cache.
const PRECACHE_URLS = [
  '/',
  '/login',
  '/static/css/base.css',
  '/static/css/landing.css',
  '/static/css/layout.css',
  '/static/css/sidebar.css',
  '/static/css/komponen.css',
  '/static/css/tema.css',
  '/static/js/main.js',
  '/static/images/logo-sm.png',
  '/static/images/logo.png',
  '/static/images/favicon-48.png',
  '/static/images/favicon-32.png',
  '/static/images/favicon-16.png',
  '/static/images/favicon.ico',
  '/static/images/apple-touch-icon.png',
  '/manifest.json'
];

// ─── INSTALL: Cache semua file statis saat pertama kali ───
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting())  // Langsung aktifkan SW baru
  );
});

// ─── ACTIVATE: Hapus cache lama jika ada versi baru ───
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    }).then(() => self.clients.claim())  // Ambil alih semua tab
  );
});

// ─── FETCH: Strategi "Stale While Revalidate" ───
// Untuk file statis: sajikan dari cache dulu (instan), lalu update
// cache di background dengan versi terbaru dari server.
// Untuk request API/dinamis: langsung ke network (tidak di-cache).
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Hanya cache request GET dan dari origin yang sama
  if (event.request.method !== 'GET' || url.origin !== location.origin) {
    return;
  }

  // Jangan cache halaman internal yang butuh login
  const skipPaths = ['/dashboard', '/berkas', '/chat', '/kategori', '/tag', '/aktivitas', '/profil'];
  if (skipPaths.some((path) => url.pathname.startsWith(path))) {
    return;
  }

  // Stale-While-Revalidate untuk file statis
  if (url.pathname.startsWith('/static/') || PRECACHE_URLS.includes(url.pathname)) {
    event.respondWith(
      caches.open(CACHE_NAME).then((cache) => {
        return cache.match(event.request).then((cachedResponse) => {
          const networkFetch = fetch(event.request).then((networkResponse) => {
            // Update cache di background
            cache.put(event.request, networkResponse.clone());
            return networkResponse;
          }).catch(() => cachedResponse);  // Jika offline, pakai cache

          // Kembalikan cache dulu (instant), update di belakang
          return cachedResponse || networkFetch;
        });
      })
    );
    return;
  }

  // Untuk halaman publik (/, /login): Network-first, fallback ke cache
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        const clone = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});
