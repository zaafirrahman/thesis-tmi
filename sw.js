const CACHE_NAME = 'katalog-tmi-v1';
const CORE_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/pwa.png',
  '/catalog.png'
];

self.addEventListener('install', function (event) {
  event.waitUntil(
    caches.open(CACHE_NAME).then(function (cache) {
      return cache.addAll(CORE_ASSETS.map(function (url) {
        return new Request(url, { cache: 'reload' });
      })).catch(function () {
        // Kalau salah satu aset gak ada (mis. catalog.png beda nama), jangan gagalkan seluruh instalasi
      });
    }).then(function () {
      return self.skipWaiting();
    })
  );
});

self.addEventListener('activate', function (event) {
  event.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(
        keys.filter(function (key) { return key !== CACHE_NAME; })
            .map(function (key) { return caches.delete(key); })
      );
    }).then(function () {
      return self.clients.claim();
    })
  );
});

self.addEventListener('fetch', function (event) {
  if (event.request.method !== 'GET') return;

  event.respondWith(
    caches.match(event.request).then(function (cached) {
      const networkFetch = fetch(event.request).then(function (response) {
        if (response && response.status === 200 && response.type === 'basic') {
          const copy = response.clone();
          caches.open(CACHE_NAME).then(function (cache) {
            cache.put(event.request, copy);
          });
        }
        return response;
      }).catch(function () {
        return cached || caches.match('/index.html');
      });

      return cached || networkFetch;
    })
  );
});
