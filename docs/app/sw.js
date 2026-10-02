// ARC-22 Studio offline cache: stale-while-revalidate for every same-origin file.
// The app works offline after the first visit and picks up rebuilt data on the next load.
const CACHE = "arc22-studio-v1";
const CORE = [
  "./", "./index.html", "./studio.css", "./manifest.webmanifest",
  "./js/app.js", "./js/viewer.js", "./js/measure.js", "./js/wiring.js", "./js/build.js", "./js/checks.js",
  "./lib/three/three.module.js", "./lib/three/three.core.js",
  "./lib/three/addons/controls/OrbitControls.js", "./lib/three/addons/loaders/STLLoader.js",
  "./icons/icon-192.png", "./models/index.json",
  "./data/params.json", "./data/pins.json", "./data/checks.json", "./data/build.json",
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(CORE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;
  e.respondWith(caches.open(CACHE).then(async (cache) => {
    const hit = await cache.match(e.request, { ignoreSearch: true });
    const net = fetch(e.request).then((res) => {
      if (res.ok) cache.put(e.request, res.clone());
      return res;
    }).catch(() => hit);
    return hit || net;
  }));
});
