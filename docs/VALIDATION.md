# Validation — what is checked, and what is not

Two kinds of evidence, never mixed:

- **RECORDED** — produced by scripts from the CAD model and exported files. Reproducible, but only as good as the numbers in `cad/arc22_params.py`, and **57 of the 60 measured values are still nominal (VERIFY)**.
- **PHYSICAL** — done with real parts on a real printer. **Every physical item below is currently UNVERIFIED.**

## RECORDED checks

| Area | Result | Details |
|---|---|---|
| CAD self-consistency (`cad/validate_arc22.py`) | 99 / 99 pass at nominal values | [cad_checks.md](validation/cad_checks.md) — envelope, bed fit, hard parts and wire fields vs shells, module-to-module room, insertion paths, closing swept volume, routes, hand loop, screws, colour regions |
| Exported meshes (`cad/export_arc22.py`) | pass | [mesh_checks.md](validation/mesh_checks.md) — all four STL regions watertight, consistent winding, volume within 0.5 % of the B-rep |
| Fit-sample generation | pass | gauge frame stays out of the reserved ESP32 wire volume (0 mm³) |
| Firmware static checks (`tools/verify_project.py`) | pass | pin map unique and on safe GPIO, matches [WIRING.md](WIRING.md); sdkconfig; version pins; git components at pinned commits; no credentials in git |
| Manufacturing data (`tools/build_mfg.py`) | pass | 40 wires, 15 connectors: every firmware GPIO in `pins.h` reaches its module pin, all three CS lines have 10 kΩ pull-ups to 3V3, no GPIO or 3V3 net touches 5 V/battery, no header pin carries two wires. Header pin orders themselves are from reference pinouts and are UNVERIFIED on your boards |
| Pinned dependency existence | confirmed 2026-09-30 | ESP-IDF v5.4.2, arduino-esp32 3.2.1, esp-dl v3.3.6 (contains coco_detect 0.4.0 and YOLO11N_320_S8_V1), LovyanGFX 1.2.28, ArduCAM commit 066a7ea — all resolved on GitHub |
| ARC-22 Studio web app | pass (headless Chromium, 2026-10-02) | all five views load at 1440 × 900 and 390 × 844 with no console errors; model loads; closing slider reports the recorded check; `my_units.toml` downloads in the format `arc22_params.py` reads |
| ARC-22 Studio desktop app | Linux only (2026-10-02) | Electron 44.5.1 window loads the app over `arc22://` with no console errors; `.AppImage` and `.deb` package. Windows/macOS installers are built by the `release` workflow and have not been launched |
| Firmware compilation | **NOT DONE** | the source has not been cross-compiled. Run the `firmware` GitHub Actions workflow (or build locally) and keep the log. Source present ≠ compiled |

What a recorded PASS means: *with the nominal numbers, nothing printed occupies space reserved for a part, a plugged connector, a wire bend or a cable route, at rest, during insertion, or while the right shell closes.* It does not mean your parts have those numbers.

## PHYSICAL checks — all UNVERIFIED

| # | Check | Stage | Status |
|---|---|---|---|
| P0 | Header pin order of YOUR ESP32, display and camera matches `hardware/connectors.yml` | 0 | UNVERIFIED |
| P1 | Measured values entered for display, camera, ESP32, plugs, button, charger, battery | 0 | UNVERIFIED |
| P2 | Fit samples 01–03 print at 100 % and fit snug, wired, without contact on glass/lens/components | 1 | UNVERIFIED |
| P3 | Bambu Studio import: correct colour assignment of WHITE/BLUE regions, no "load geometry only" error, toolpaths inspected | 3 | UNVERIFIED |
| P4 | Shells print with removable supports; clips and slots intact | 3 | UNVERIFIED |
| P5 | Empty halves close by hand; lip/groove seats all round | 3 | UNVERIFIED |
| P6 | Fully wired halves close with gentle hand pressure before any screw | 3 | UNVERIFIED |
| P7 | M2 × 12 screws hold in PETG without stripping; no module pressure | 3 | UNVERIFIED |
| P8 | Ergonomics: grip comfortable, nothing blocks the lens or screen | 3 | UNVERIFIED |
| P9 | Charger: start-up with the real load, peak current, restart, temperature, full charge within the 6 h timer | 4 | UNVERIFIED |
| P10 | Display colours/orientation, touch calibration to all corners | 4 | UNVERIFIED |
| P11 | Camera SPI + I2C, image upright and focused (optics) | 4 | UNVERIFIED |
| P12 | Firmware builds with the pinned versions (real build log) | 4 | UNVERIFIED |
| P13 | Local detection runs on-device; boxes align; measured end-to-end latency | 5 | UNVERIFIED |
| P14 | Selection, Wikipedia fetch with Wi-Fi off during detection; cache and QR fallbacks | 5 | UNVERIFIED |
| P15 | 30-minute closed-case run: no resets, thermals acceptable | 6 | UNVERIFIED |
| P16 | Endurance: charge/discharge cycles closed, repeated open/close of the shells | 6 | UNVERIFIED |

## How to update this file
When you complete a physical check, change its status to `VERIFIED <date> — <your part numbers / notes>` or `FAILED <date> — <what happened>`. Keep failures; they are the most useful lines in this file.

Never describe the build as perfect-fit, fully tested or waterproof. It has no Ingress Protection (IP) rating.
