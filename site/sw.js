/* Planika · service worker: app instalable y funcionamiento sin conexión.
 *
 * - Páginas (navegación): primero la red, con 4 s de margen; si no hay conexión, la última copia guardada
 *   y, si no la hay, offline.html. La agenda cambia a diario: nunca se sirve una copia vieja si hay red.
 * - Archivos con versión en la URL (?v=..., estilos, app y datos de la portada): de la caché si ya están,
 *   porque una versión no cambia nunca; al guardar una versión nueva se borran las anteriores.
 * - Resto de archivos propios (iconos, imágenes de la web): la copia guardada al momento y se actualiza
 *   por detrás.
 * - Lo de otros dominios (mapas, analítica, imágenes de las agendas) no se toca.
 * Cambiar VERSION al cambiar este archivo de forma que haya que vaciar las cachés.
 */
var VERSION = 'v1';
var PAGES = 'planika-paginas-' + VERSION;
var ASSETS = 'planika-archivos-' + VERSION;
var MAX_PAGES = 60;
var MAX_ASSETS = 120;
var PRECACHE = ['/', '/offline.html', '/icon.svg', '/icon-192.png', '/manifest.webmanifest'];

self.addEventListener('install', function (ev) {
  ev.waitUntil(caches.open(PAGES).then(function (c) {
    return Promise.all(PRECACHE.map(function (u) {
      return fetch(u, { cache: 'reload' }).then(function (r) { if (r.ok) return c.put(u, r); }).catch(function () {});
    }));
  }).then(function () { return self.skipWaiting(); }));
});

self.addEventListener('activate', function (ev) {
  ev.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.filter(function (k) { return k.indexOf('planika-') === 0 && k !== PAGES && k !== ASSETS; })
      .map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});

function pageKey(url) {
  // Una copia por página: /?q=jazz y / comparten la portada; /index.html es la portada
  var p = url.pathname === '/index.html' ? '/' : url.pathname;
  return new Request(url.origin + p);
}

function trim(name, max) {
  return caches.open(name).then(function (c) {
    return c.keys().then(function (keys) {
      if (keys.length <= max) return;
      return Promise.all(keys.slice(0, keys.length - max).map(function (k) { return c.delete(k); }));
    });
  });
}

function fromNetworkPage(req, key) {
  return fetch(req).then(function (res) {
    if (res.ok && res.type === 'basic') {
      var copy = res.clone();
      caches.open(PAGES).then(function (c) { return c.put(key, copy); }).then(function () { return trim(PAGES, MAX_PAGES); });
    }
    return res;
  });
}

function page(ev, url) {
  var key = pageKey(url);
  var net = fromNetworkPage(ev.request, key);
  ev.waitUntil(net.catch(function () {}));
  var offline = function () {
    return caches.match(key).then(function (hit) { return hit || caches.match('/offline.html'); })
      .then(function (r) { return r || Response.error(); });
  };
  // Si la red tarda más de 4 s y hay copia guardada, la copia; si no, se sigue esperando a la red
  var slow = new Promise(function (resolve) { setTimeout(resolve, 4000); }).then(function () { return caches.match(key); });
  return Promise.race([net.catch(function () { return null; }), slow]).then(function (res) {
    return res || net.then(null, offline);
  });
}

function versioned(ev, url) {
  return caches.open(ASSETS).then(function (c) {
    return c.match(ev.request).then(function (hit) {
      if (hit) return hit;
      return fetch(ev.request).then(function (res) {
        if (res.ok && res.type === 'basic') {
          var copy = res.clone();
          ev.waitUntil(c.keys().then(function (keys) {
            // Fuera las versiones anteriores del mismo archivo
            return Promise.all(keys.filter(function (k) {
              var u = new URL(k.url); return u.pathname === url.pathname && u.search !== url.search;
            }).map(function (k) { return c.delete(k); }));
          }).then(function () { return c.put(ev.request, copy); }).then(function () { return trim(ASSETS, MAX_ASSETS); }));
        }
        return res;
      }).catch(function () {
        // Sin conexión y sin esa versión: la última que haya de ese archivo
        return c.match(ev.request, { ignoreSearch: true }).then(function (old) { return old || Response.error(); });
      });
    });
  });
}

function asset(ev) {
  return caches.open(ASSETS).then(function (c) {
    return c.match(ev.request).then(function (hit) {
      var net = fetch(ev.request).then(function (res) {
        if (res.ok && res.type === 'basic') { var copy = res.clone(); c.put(ev.request, copy).then(function () { return trim(ASSETS, MAX_ASSETS); }); }
        return res;
      });
      if (hit) { ev.waitUntil(net.catch(function () {})); return hit; }
      return net;
    });
  });
}

self.addEventListener('fetch', function (ev) {
  var req = ev.request;
  if (req.method !== 'GET') return;
  var url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  if (req.mode === 'navigate') { ev.respondWith(page(ev, url)); return; }
  if (/\/sw\.js$/.test(url.pathname) || /\.(xml|txt)$/.test(url.pathname)) return;
  if (/[?&]v=/.test(url.search)) { ev.respondWith(versioned(ev, url)); return; }
  if (/\.(css|js|svg|png|jpe?g|webp|ico|woff2?|webmanifest|json)$/.test(url.pathname)) { ev.respondWith(asset(ev)); return; }
});
