# Firmware — local object detection on the ESP32-S3

**What it does.** Point the high front camera, tap **SCAN**. The scanner takes one still photo (JPEG, 320 × 240), decodes it, and runs a COCO object detector **on the ESP32-S3 itself** — no cloud, no computer. It draws boxes and names for up to 8 objects. Tap one, tap **LEARN**, and it fetches the Wikipedia introduction over Wi-Fi (cached afterwards), with a QR code to the article or a Google search as fallbacks. **DIM** toggles the backlight on displays with a backlight driver.

**What it cannot do.** The model knows the 80 everyday COCO categories (person, cup, bottle, chair, laptop, dog, …). It cannot identify species, minerals, brands or unknown objects. It is a still-photo scanner, not live video recognition: Espressif lists about **6.2 s** for this model alone on an ESP32-S3 (YOLO11n, 320 × 320 input, INT8). The full capture → decode → detect → draw time on this device is higher and **unmeasured** until you measure it in Stage 5.

**Status.** The firmware is written against the pinned library versions below but has **not yet been compiled or run on hardware** for ARC-22 (the ARC04/ARC20 lineage was never cross-compiled for this layout either). The `firmware` GitHub Actions workflow builds it in Espressif's official ESP-IDF 5.4.2 container and keeps the full build log — get a real log before trusting it.

## Pinned versions
| Component | Version | Source |
|---|---|---|
| ESP-IDF (Espressif IoT Development Framework) | 5.4.2 | `espressif/esp-idf` tag v5.4.2 |
| Arduino-ESP32 (as an IDF component) | 3.2.1 | component manager |
| ESP-DL (deep-learning library) | 3.3.6 | component manager |
| coco_detect (model wrapper) | 0.4.0 | component manager |
| Model | YOLO11N_320_S8_V1 | weights packed by coco_detect, flashed to the `coco_det` partition |
| LovyanGFX (display + touch) | 1.2.28 | git, commit 45dc36b, fetched by `tools/fetch_libraries.py` |
| ArduCAM driver | commit 066a7ea | git, fetched and wrapped by `tools/fetch_libraries.py` |

Everything is recorded in `firmware/PINNED_VERSIONS.json`. No binaries or weights are committed; they download during setup.

## Memory plan
- Weights stay **in flash** (the `coco_det` partition, read in place). With 8 MB PSRAM, coco_detect does not copy them to PSRAM.
- Detector and decoded image are **deleted right after each detection**, before Wi-Fi/TLS (Transport Layer Security) starts.
- **Wi-Fi is switched off before every detection** and only switched on for the article lookup.

## Setup (Ubuntu or the ESP-IDF terminal on Windows)
You need ESP-IDF **5.4.2** (Arduino-ESP32 3.2.1 targets the 5.4 line; a newer IDF such as 5.5.x will be rejected by the version pin). Install it side by side with any other IDF version.

```bash
# from the repository root
python tools/fetch_libraries.py --camera plus      # or: --camera mini  (read your camera PCB)
cp .env.example .env                               # optional: Wi-Fi for article lookup only
python tools/fetch_libraries.py --secrets          # writes firmware/main/secrets.h (git-ignored)
cd firmware
idf.py set-target esp32s3
idf.py build
cd .. && python tools/verify_project.py --after-build && cd firmware
idf.py -p PORT flash monitor                       # PORT e.g. /dev/ttyACM0, or COM9 on Windows
```

`idf.py flash` writes the bootloader, partition table, app **and the model partition**. Follow the programming sequence in [SAFETY.md](SAFETY.md) before connecting USB.

## Stage 4 — commission capture first (default build)
`CONFIG_ARC_COMMISSION_CAPTURE_ONLY=y` loads no model. Three pages:
1. **Display + orientation** — colour bars, an arrow that must point to the top of the scanner, touch calibration (stored in NVS, non-volatile storage).
2. **Touch** — draw anywhere; the dot must follow the stylus into every corner.
3. **Camera** — SPI test, I2C sensor ID (0x26/0x41 or 0x42), then a live still loop with JPEG size and frame rate.

## Stage 5 — enable inference
`idf.py menuconfig` → **ARC-22 scanner** → untick *Commissioning mode*, rebuild, flash. Other options there:

| Option | Default | Meaning |
|---|---|---|
| `ARC_BACKLIGHT_GPIO_ENABLED` | n | drive the backlight from GPIO6 — only on a driver-equipped display; enables DIM |
| `ARC_LCD_ROTATION` | 0 | LovyanGFX rotation 0–7 |
| `ARC_CAM_FLIP_180` | n | sensor flip registers (verify on your module) |
| `ARC_SCORE_THRESHOLD_PCT` | 35 | minimum detection score |
| `ARC_MAX_DETECTIONS` | 8 | boxes shown |
| `ARC_CAMERA_SPI_HZ` | 4 000 000 | camera SPI clock (Arducam Mini max 8 MHz) |
| `ARC_WIKI_LANG` | en | Wikipedia language |

## Credentials
Wi-Fi credentials live only in `.env` (git-ignored) → `firmware/main/secrets.h` (git-ignored). Without them the scanner stays offline and shows QR codes. Never commit either file; CI fails if you do.

## Source map
| File | Role |
|---|---|
| `main/pins.h` | the pin map (mirrors [WIRING.md](WIRING.md)) |
| `main/display.*` | LovyanGFX config: ST7796S + XPT2046 on SPI3, touch calibration |
| `main/camera.*` | ArduCAM wrapper on Arduino SPI (SPI2) + Wire, JPEG 320 × 240 capture |
| `main/detector.*` | JPEG decode + COCODetect (YOLO11N_320_S8_V1), frees everything after |
| `main/wiki.*` | NVS cache → Wi-Fi → HTTPS Wikipedia REST summary, Wi-Fi off afterwards |
| `main/ui.*`, `main/main.cpp` | screens, touch handling, commissioning and scanner flows |
| `main/coco_labels.h` | 80 COCO names + Wikipedia article titles |

Wikipedia text is licensed CC BY-SA; the article screen says so.
