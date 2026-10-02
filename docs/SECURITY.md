# Security and supply chain

This repository ships source, CAD and documentation — and helper scripts that download code onto your computer and a model onto your scanner. It follows the OWASP Top 10:2025 category **A03 Software Supply Chain Failures** as a checklist.

## What is pinned
| Item | Pin | Where |
|---|---|---|
| ESP-IDF | v5.4.2 (commit f5c3654) | `firmware/PINNED_VERSIONS.json`, `firmware/main/idf_component.yml` |
| arduino-esp32 / esp-dl / coco_detect | 3.2.1 / 3.3.6 / 0.4.0 | `idf_component.yml`; resolved versions land in `firmware/dependencies.lock` after a build (keep it with your release notes) |
| Model | YOLO11N_320_S8_V1 from coco_detect 0.4.0 | packed during the build, flashed to `coco_det` |
| LovyanGFX | tag 1.2.28 = commit 45dc36b | `tools/fetch_libraries.py` refuses any other commit |
| ArduCAM driver | commit 066a7ea | same |
| CAD Python packages | exact `==` versions | `cad/requirements.txt` |
| Desktop app (Electron 44.5.1, electron-builder 26.15.3) | exact versions + full `package-lock.json` (every transitive package with its integrity hash) | `app/`; installed only with `npm ci` |
| Web app libraries (three.js 0.186.1, fonts) | vendored copies with their licences | `docs/app/lib/` — no CDN at run time |
| GitHub Actions | full 40-character commit SHAs | `.github/workflows/*.yml` (Dependabot proposes updates) |
| Firmware build container | `espressif/idf:v5.4.2` (tag) | `firmware.yml` — for stricter pinning, replace the tag with its `@sha256:` digest after your first run |

## Controls
- **SBOM** — `python tools/make_sbom.py > sbom.cdx.json` writes a CycloneDX 1.5 Software Bill of Materials; every release attaches one.
- **Signed releases** — the `release` workflow builds the desktop installers on GitHub-hosted Windows, macOS and Linux runners, the source ZIP, writes `SHA256SUMS.txt`, and creates a Sigstore-backed GitHub build-provenance attestation. Verify a download with `sha256sum -c SHA256SUMS.txt` and `gh attestation verify <file> -R <owner>/arc22-scanner`.
- **Dependabot** — weekly for Actions, monthly for the CAD Python packages and the desktop app's npm packages.
- **App hardening** — a strict Content Security Policy (only the app's own files), no third-party requests; the desktop app uses context isolation, the Chromium sandbox, no Node.js in the page, a path-checked private `arc22://` scheme, and denies every permission request.
- **CodeQL** — scans the Python helper scripts, the app's JavaScript and the workflow files.
- **Least privilege** — every workflow starts with `permissions: contents: read`; only `release` gets `contents: write`, `id-token: write`, `attestations: write`. Checkouts use `persist-credentials: false`.
- **No binaries** — no firmware image or model weights are committed; they are fetched from their upstreams during setup and their SHA-256 hashes are printed by `tools/verify_project.py --after-build`.
- **Credentials** — Wi-Fi credentials live only in `.env` (from `.env.example`) and the generated `firmware/main/secrets.h`; both are git-ignored and CI fails if either is committed. Use a guest/IoT network if you can; the device only talks to `*.wikipedia.org` over HTTPS with the ESP-IDF certificate bundle.

## Reporting a problem
Open a private security advisory on the repository (Security → Advisories → Report a vulnerability) rather than a public issue.
