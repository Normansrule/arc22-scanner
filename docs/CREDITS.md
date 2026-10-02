# Credits and sources

Every datasheet, vendor page and library this build relies on. Numbers taken from these sources are **nominal** until you measure your own part ([MEASUREMENTS.md](MEASUREMENTS.md)).

## Modules
- Espressif — [ESP32-S3-DevKitC-1 user guide](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide.html) (header layout, USB ports, strapping pins)
- Espressif — [ESP32-S3 datasheet](https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf) (GPIO, flash/PSRAM pins, 3.3 V logic)
- LCDwiki — [4.0inch SPI Module ST7796 (MSP4020/MSP4021)](https://www.lcdwiki.com/4.0inch_SPI_Module_ST7796) and its [user manual (PDF)](https://www.lcdwiki.com/res/MSP4021/4.0inch_SPI_Module_MSP4020&MSP4021_User_Manual_EN.pdf) — reference PCB 61.74 × 108.04 mm, active area 55.68 × 83.52 mm, pinout
- Sitronix ST7796S display driver and XPT2046 touch controller datasheets (linked from the LCDwiki page above)
- Arducam — [Arducam Mini 2MP Plus product page](https://www.arducam.com/arducam-2mp-spi-camera-b0067-arduino.html) and [Arducam Shield Mini 2MP Plus documentation](https://docs.arducam.com/Arduino-SPI-camera/Legacy-SPI-camera/Hardware/Arducam-Shield-Mini-2MP-Plus/) (SPI + I2C interface, S-mount lens)

## Power
- Adafruit — [Lithium Ion Battery Pack 3.7 V 4400 mAh (#354)](https://www.adafruit.com/product/354)
- Adafruit — [bq25185 USB/DC/Solar Charger with 5 V Boost (#6106)](https://www.adafruit.com/product/6106) and the [learn guide pinouts page](https://learn.adafruit.com/adafruit-bq25185-usb-dc-solar-charger-with-5v-boost-board/pinouts) — 5 V / 1 A boost output, EN low disables 5 V, ~200 mA start-up load limit, 6 h charge timer
- Texas Instruments — [BQ25185 charger](https://www.ti.com/product/BQ25185) and [TPS61023 boost converter](https://www.ti.com/product/TPS61023) product pages

## Software
- Espressif — [ESP-IDF](https://github.com/espressif/esp-idf) v5.4.2
- Espressif — [arduino-esp32](https://github.com/espressif/arduino-esp32) 3.2.1
- Espressif — [ESP-DL](https://github.com/espressif/esp-dl) 3.3.6 and the [coco_detect model component](https://github.com/espressif/esp-dl/tree/master/models/coco_detect) (YOLO11n 320 INT8; ~6.16 s model latency on ESP32-S3 per its README)
- lovyan03 — [LovyanGFX](https://github.com/lovyan03/LovyanGFX) 1.2.28
- ArduCAM — [ArduCAM Arduino library](https://github.com/ArduCAM/Arduino) @ 066a7ea
- Ultralytics — YOLO11 architecture (the model trained/quantised by Espressif)
- COCO — [Common Objects in Context dataset](https://cocodataset.org/) (the 80 categories)
- Wikimedia — [Wikipedia REST API](https://en.wikipedia.org/api/rest_v1/) and the [User-Agent policy](https://meta.wikimedia.org/wiki/User-Agent_policy); article text is CC BY-SA
- [CadQuery](https://github.com/CadQuery/cadquery), [OpenCascade](https://dev.opencascade.org/), [trimesh](https://github.com/mikedh/trimesh), [NumPy](https://numpy.org/), [Matplotlib](https://matplotlib.org/)

## App
- [three.js](https://threejs.org/) 0.186.1 (MIT) — 3D viewer, vendored in `docs/app/lib/three`
- [Electron](https://www.electronjs.org/) 44.5.1 and [electron-builder](https://www.electron.build/) 26.15.3 (MIT) — desktop app
- [Chakra Petch](https://fonts.google.com/specimen/Chakra+Petch) and [Atkinson Hyperlegible](https://www.brailleinstitute.org/freefont/) (SIL Open Font License 1.1) via [Fontsource](https://fontsource.org/) 5.3.0

## Printing
- Bambu Lab — [P1S specifications](https://bambulab.com/en/p1) (256 × 256 × 256 mm build volume)
- 3MF Consortium — [3MF core specification](https://github.com/3MFConsortium/spec_core)

## Security
- OWASP — [A03:2025 Software Supply Chain Failures](https://owasp.org/Top10/2025/A03_2025-Software_Supply_Chain_Failures/)
- [CycloneDX](https://cyclonedx.org/) SBOM standard · GitHub [artifact attestations](https://docs.github.com/en/actions/security-for-github-actions/using-artifact-attestations)

## Inspiration
The silhouette is inspired by the handheld scanner from the game *Subnautica* (Unknown Worlds Entertainment). ARC-22 is an original fan-made design; it reproduces no game assets and is not affiliated with or endorsed by Unknown Worlds.
