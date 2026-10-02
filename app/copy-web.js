// Copies the web app (docs/app) into app/web before running or packaging.
// docs/app stays the single source: never edit app/web by hand.
const fs = require("node:fs");
const path = require("node:path");
const src = path.join(__dirname, "..", "docs", "app");
const dst = path.join(__dirname, "web");
if (!fs.existsSync(path.join(src, "models", "index.json"))) {
  console.error("docs/app/models is missing: run `bash scripts/rebuild_all.sh` (or `python tools/build_web_data.py`) first.");
  process.exit(1);
}
fs.rmSync(dst, { recursive: true, force: true });
fs.cpSync(src, dst, { recursive: true, filter: (p) => !p.endsWith("sw.js") });
console.log("copied docs/app -> app/web");
