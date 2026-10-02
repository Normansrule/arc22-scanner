# ARC-22 — open-source handheld object scanner

A Subnautica-style handheld scanner you can print, wire and flash yourself. Point it, tap **SCAN**, and an ESP32-S3 recognises objects **on the device** — no cloud — then shows a Wikipedia intro for the one you tap.

![Hardware: CERN-OHL-P-2.0](https://img.shields.io/badge/hardware-CERN--OHL--P--2.0-1a9fdb) ![Software: MIT](https://img.shields.io/badge/software-MIT-17303d) ![Docs: CC BY 4.0](https://img.shields.io/badge/docs-CC%20BY%204.0-2e8b62) ![Status: unverified prototype](https://img.shields.io/badge/status-unverified%20prototype-e39b2d)

| Front | Rear |
|---|---|
| ![ARC-22 front](docs/img/arc22_hero_front.png) | ![ARC-22 rear: touchscreen, button, USB-C](docs/img/arc22_hero_rear.png) |

## Everything you need

| Step | Files | Read |
|---|---|---|
| 🖨️ **Print** | [`cad/out/print/stl/`](cad/out/print/stl) two shells, two colours each · [fit samples](cad/out/fit_samples) · [STEP](cad/out/step) | [PRINTING](docs/PRINTING.md) |
| 🛒 **Buy** | [`hardware/bom.csv`](hardware/bom.csv) | [BOM](docs/BOM.md) |
| 🔌 **Wire** | [`hardware/connections.csv`](hardware/connections.csv) · [harness drawing](hardware/harness/arc22_harness.svg) | [CONNECTIONS](docs/CONNECTIONS.md) · [SAFETY](docs/SAFETY.md) |
| ⚡ **Flash** | [`firmware/`](firmware) ESP-IDF 5.4.2 | [FIRMWARE](docs/FIRMWARE.md) |
| 🔧 **Build** | 7 stages, each PASS / FIX / STOP | [BUILD GUIDE](docs/BUILD_GUIDE.md) |
| 📐 **Check** | requirements with IDs + how each is verified | [REQUIREMENTS](docs/REQUIREMENTS.md) · [VALIDATION](docs/VALIDATION.md) |

All of it in one download: **`arc22-manufacturing-<version>.zip`** on the [Releases](../../releases) page. Index: [`hardware/README.md`](hardware/README.md).

## What's inside

![Exploded assembly with numbered parts](docs/img/arc22_assembly.png)

| # | Part | Qty |
|---|---|---|
| 1, 2 | Printed LEFT + RIGHT shells (white PETG, cyan accents) | 1 each |
| 3 | 4.0" 480×320 SPI touchscreen, ST7796S + XPT2046 | 1 |
| 4 | Arducam Mini 2MP (Plus) OV2640, SPI + I2C | 1 |
| 5 | ESP32-S3-N16R8 dev board (16 MB flash, 8 MB PSRAM) | 1 |
| 6 | Protected Li-ion 3.7 V 4400 mAh (Adafruit #354) | 1 |
| 7 | bq25185 charger + 5 V boost (Adafruit #6106) | 1 |
| 8 | 12 mm latching power button | 1 |
| 9 | M2 × 12 self-tapping screws | 6 |
| — | Dupont leads, 22 AWG wire, 3 × 10 kΩ, foam pads, heat-shrink | [full BOM](docs/BOM.md) |

## Wiring

![Wiring at a glance](docs/img/wiring_overview.png)

| GPIO | Goes to | GPIO | Goes to |
|---|---|---|---|
| GPIO4 | camera SDA | GPIO11 | display SDI + touch T_DIN (Y-splice) |
| GPIO5 | camera SCL | GPIO12 | display SCK + touch T_CLK (Y-splice) |
| GPIO6 | display LED *(optional)* | GPIO13 | touch T_DO |
| GPIO7 | display RESET | GPIO14 | touch T_IRQ |
| GPIO8 | display DC/RS | GPIO15 | camera CS + 10 kΩ ↑ 3V3 |
| GPIO9 | touch T_CS + 10 kΩ ↑ 3V3 | GPIO16 | camera MISO |
| GPIO10 | display CS + 10 kΩ ↑ 3V3 | GPIO17 / 18 | camera MOSI / SCK |

**3.3 V logic only.** Power: battery → charger → removable RUN pigtail → 5 V. The button switches the charger's EN. Every wire with colour, gauge and length: [CONNECTIONS.md](docs/CONNECTIONS.md).

## Why it fits: wires are part of the model

Earlier designs fit bare boards, not boards with jumpers plugged in. ARC-22 reserves space (amber) for every plugged connector, wire bend and strain relief. It also checks each part's insertion path and the right shell **closing** onto the fully wired left half.

| Reserved wire space | Inside the left shell |
|---|---|
| ![Reserved space in amber](docs/img/arc22_fields.png) | ![Modules and cable routes](docs/img/arc22_left_interior.png) |

## Build in 7 stages
0. **Measure** your exact parts (calipers) → `measurements/my_units.toml`
1. **Print fit samples** — screen bezel, camera nose, wired ESP32 gauge
2. **Check** the CAD: insertion paths + closing sweep, 0 failures
3. **Print the shells**, dry-fit empty, then fully wired — close by hand before screws
4. **Commission** on the bench: power → display/touch → camera image
5. **Enable on-device detection** — scan, select, learn
6. **Closed-case run** — 30 min, thermals, no resets
7. **Record** what passed and failed in [VALIDATION.md](docs/VALIDATION.md)

## ARC-22 Studio — web and desktop app

![ARC-22 Studio](docs/img/studio_model.png)

The 3D model, a measurement editor that writes `my_units.toml`, wiring, build progress and CAD checks. Use it on the [project website](docs/index.md) (`/app/`), install it from the browser, or download the desktop app from [Releases](../../releases). [More](docs/APP.md).

## Status — be honest

| Checked by scripts ✅ | Not yet done ⏳ |
|---|---|
| 99 / 99 CAD fit checks, watertight print meshes | 57 of 60 fit dimensions are reference values, not measured |
| wire list ↔ firmware pin map ↔ pull-ups, in CI | nothing printed, wired or powered yet |
| all dependency versions pinned | firmware not yet compiled (run the `firmware` workflow) |

Not waterproof. Recognises the 80 everyday COCO object types — not species, minerals or brands — and takes several seconds per scan.

## Make changes

```bash
bash scripts/rebuild_all.sh   # CAD → checks → print files → renders → app data → BOM + wiring
```
Setup, everyday loop, firmware: [DEVELOP.md](docs/DEVELOP.md) · Publishing to GitHub from a fresh Ubuntu terminal: [PUBLISH.md](docs/PUBLISH.md)

| Folder | Contents |
|---|---|
| `cad/` | CadQuery source (every dimension in `arc22_params.py`) and all generated 3D files in `cad/out/` |
| `hardware/` | BOM, connections, connectors, harness drawing |
| `firmware/` | ESP-IDF project: commissioning mode, local COCO detector, Wikipedia / QR |
| `docs/` | build guide and website; `docs/app/` is ARC-22 Studio |
| `app/` | desktop wrapper (Electron) · `tools/` generators and checks · `.github/` CI and releases |

## Licences
Hardware **CERN-OHL-P-2.0** ([LICENSE-HARDWARE](LICENSE-HARDWARE)) · software **MIT** ([LICENSE](LICENSE)) · docs and images **CC BY 4.0** ([LICENSE-DOCS](LICENSE-DOCS)). Third-party parts keep their own licences ([CREDITS](docs/CREDITS.md)). Inspired by the scanner in *Subnautica*; an original fan design, not affiliated with Unknown Worlds.
