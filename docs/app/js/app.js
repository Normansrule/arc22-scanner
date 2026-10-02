// ARC-22 Studio — entry point: view switching, storage helpers, install + offline support.
import { initViewer } from "./viewer.js";
import { initMeasure } from "./measure.js";
import { initWiring } from "./wiring.js";
import { initBuild } from "./build.js";
import { initChecks } from "./checks.js";

export const store = {
  get(key, fallback) {
    try {
      const v = localStorage.getItem("arc22." + key);
      return v === null ? fallback : JSON.parse(v);
    } catch { return fallback; }
  },
  set(key, value) {
    try { localStorage.setItem("arc22." + key, JSON.stringify(value)); return true; } catch { return false; }
  },
  remove(key) { try { localStorage.removeItem("arc22." + key); } catch { /* ignore */ } },
};

export async function getJSON(path) {
  const r = await fetch(path, { cache: "no-cache" });
  if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
  return r.json();
}

export function download(name, text, type = "text/plain") {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = Object.assign(document.createElement("a"), { href: url, download: name });
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

export function el(tag, attrs = {}, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") n.className = v;
    else if (k === "text") n.textContent = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else if (v !== false && v != null) n.setAttribute(k, v === true ? "" : v);
  }
  for (const c of kids.flat()) if (c != null) n.append(c);
  return n;
}

// ---- views ----
const started = {};
const starters = { model: initViewer, measure: initMeasure, wiring: initWiring, build: initBuild, checks: initChecks };

function show(view) {
  if (!starters[view]) view = "model";
  for (const b of document.querySelectorAll(".nav")) {
    if (b.dataset.view === view) b.setAttribute("aria-current", "page");
    else b.removeAttribute("aria-current");
  }
  for (const s of document.querySelectorAll(".view")) s.hidden = s.id !== "view-" + view;
  if (!started[view]) {
    started[view] = true;
    Promise.resolve(starters[view]()).catch((e) => {
      const sec = document.getElementById("view-" + view);
      sec.prepend(el("p", { class: "status", role: "alert",
        text: `This view could not load its data (${e.message}). Rebuild with scripts/rebuild_all.sh, then reload.` }));
      console.error(e);
    });
  }
  store.set("view", view);
  if (location.hash.slice(1) !== view) history.replaceState(null, "", "#" + view);
}

for (const b of document.querySelectorAll(".nav")) b.addEventListener("click", () => show(b.dataset.view));
window.addEventListener("hashchange", () => show(location.hash.slice(1)));
show(location.hash.slice(1) || store.get("view", "model"));

// ---- docs link only where the docs site exists (GitHub Pages / local server) ----
if (location.protocol.startsWith("http")) document.getElementById("docs-link").hidden = false;

// ---- installable app (Progressive Web App) ----
let deferred = null;
const installBtn = document.getElementById("install");
window.addEventListener("beforeinstallprompt", (e) => {
  e.preventDefault();
  deferred = e;
  installBtn.hidden = false;
});
installBtn.addEventListener("click", async () => {
  if (!deferred) return;
  deferred.prompt();
  await deferred.userChoice;
  deferred = null;
  installBtn.hidden = true;
});
const secure = location.protocol === "https:" || location.hostname === "localhost" || location.hostname === "127.0.0.1";
if ("serviceWorker" in navigator && secure) {
  navigator.serviceWorker.register("sw.js").catch((e) => console.warn("offline cache unavailable:", e));
}
