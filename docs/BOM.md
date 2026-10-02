# Bill of materials

Generated from [`hardware/bom.csv`](https://github.com/Normansrule/arc22-scanner/blob/main/hardware/bom.csv) (open it in any spreadsheet) by `tools/build_mfg.py`. **KEEP** = core part, measure your unit · **CANDIDATE** = chosen but not yet validated in this build · **OPTIONAL** = only if a check says so. Buy against the specification, then measure ([MEASUREMENTS.md](MEASUREMENTS.md)).

## Electronics

| ID | Part | Qty | Specification | Where | Status |
|---|---|---|---|---|---|
| E1 | ESP32-S3-N16R8 development board | 1 pc | ESP32-S3-WROOM-1-N16R8 module (16 MB flash, 8 MB octal PSRAM), DevKitC-1 header layout, USB-C — measure your exact board; N16R8 is a memory option not an outline | search: ESP32-S3-DevKitC-1 N16R8 | KEEP |
| E2 | 4.0 in SPI TFT with resistive touch | 1 pc | 480x320, ST7796S driver, XPT2046 touch, 14-pin header (MSP4021-style) — no rigid glass over resistive touch | search: Hosyond 4.0 inch ST7796S XPT2046 | KEEP |
| E3 | Arducam Mini 2MP Plus (or Mini 2MP) OV2640 | 1 pc | SPI + I2C, 8-pin header, S-mount (M12) lens — not an ESP32-CAM / bare OV2640 / Arducam Mega | [link](https://www.arducam.com/arducam-2mp-spi-camera-b0067-arduino.html) | KEEP |

## Power

| ID | Part | Qty | Specification | Where | Status |
|---|---|---|---|---|---|
| P1 | Li-ion battery 3.7 V 4400 mAh (protected) | 1 pc | 1S, built-in protection, JST-PH lead, ~69 x 37 x 18 mm — keep factory wrapper and leads | [link](https://www.adafruit.com/product/354) | CANDIDATE |
| P2 | bq25185 USB/DC/solar charger with 5 V boost | 1 pc | 5 V / 1 A boost, EN pin, 6 h charge timer, USB-C — boost stalls if switched on into >~200 mA; test before trusting | [link](https://www.adafruit.com/product/6106) | CANDIDATE |
| P3 | 12 mm latching push button | 1 pc | SPST or SPDT, panel hole 12.5 mm, <= 22 mm deep incl. lugs | search: 12mm latching push button self-locking | CANDIDATE |
| P4 | JST-XH 2-pin connector pair (RUN pigtail) | 1 set | keyed male + female housings with crimps — unplug before programming | search: JST-XH 2.54 2 pin connector kit | KEEP |

## Wiring

| ID | Part | Qty | Specification | Where | Status |
|---|---|---|---|---|---|
| W1 | Dupont jumper wires female-female | 40 pc | 2.54 mm, 26 AWG, 10/20 cm, assorted colours — or crimp your own to the lengths in connections.csv | search: dupont jumper wire female to female | KEEP |
| W2 | Stranded silicone wire 22 AWG red + black | 1 m each | for 5 V and ground distribution — no battery current through breadboard jumper chains | search: 22 AWG silicone wire | KEEP |
| W3 | Resistor 10 kOhm 1/4 W | 3 pc | CS pull-ups to 3V3 (TFT CS, touch CS, camera CS) | any electronics supplier | KEEP |
| W4 | Resistor 4.7 kOhm 1/4 W | 2 pc | I2C pull-ups SDA/SCL to 3V3 — only if the camera has none fitted | any electronics supplier | OPTIONAL |
| W5 | Resistor 100 kOhm 1/4 W | 1 pc | backlight pull-down — only after verifying a backlight driver | any electronics supplier | OPTIONAL |
| W6 | Heat-shrink tubing assortment | 1 set | 1.5-6 mm, 2:1 — every splice and pull-up tee | any | KEEP |
| W7 | Soft removable cable restraints | 1 set | fabric tape or hook-and-loop strap — never trap a bundle under a rib | any | KEEP |

## Mechanical

| ID | Part | Qty | Specification | Where | Status |
|---|---|---|---|---|---|
| M1 | Printed LEFT shell | 1 pc | cad/out/print/stl/ARC22_LEFT_WHITE.stl + ARC22_LEFT_BLUE.stl (one object, two colours) | print it (docs/PRINTING.md) | KEEP |
| M2 | Printed RIGHT shell | 1 pc | cad/out/print/stl/ARC22_RIGHT_WHITE.stl + ARC22_RIGHT_BLUE.stl (one object, two colours) | print it (docs/PRINTING.md) | KEEP |
| M3 | Screw M2 x 12 mm | 6 pc | self-tapping into PETG, head <= 4 mm — no M3 and no heat-set inserts | search: M2x12 self tapping screw | KEEP |
| M4 | Non-conductive foam tape 0.5-1.0 mm | 0.1 m2 | EVA or PE, adhesive back; model assumes 0.8 mm — on every pad and slot jaw | search: EVA foam tape 1mm | KEEP |
| M5 | Fit samples 01-03 | 1 set | cad/out/fit_samples/*.stl, single colour — test pieces; not installed | print first | KEEP |

## Filament

| ID | Part | Qty | Specification | Where | Status |
|---|---|---|---|---|---|
| F1 | PETG white | 0.65 kg | body regions (~481 cm3) plus supports | any PETG | KEEP |
| F2 | PETG cyan / blue | 0.1 kg | accent regions (~62 cm3); decorative, not illuminated — plus purge allowance | any PETG | KEEP |

## Cables

| ID | Part | Qty | Specification | Where | Status |
|---|---|---|---|---|---|
| C1 | USB-C cable + 5 V USB charger | 1 pc | charges through the charger board's USB-C | any | KEEP |
| C2 | USB-C data cable | 1 pc | programs the ESP32; measure its overmold (USB_PLUG_T/W) | any | KEEP |

## Tools

| ID | Part | Qty | Specification | Where | Status |
|---|---|---|---|---|---|
| T1 | Digital calipers | 1 pc |  — stage 0 measurements | any | KEEP |
| T2 | Multimeter | 1 pc |  — power commissioning | any | KEEP |
| T3 | Soldering iron + solder + flux | 1 set |  — splices and pull-up tees | any | KEEP |
| T4 | Crimping tool for Dupont / JST-XH | 1 pc |  — if you crimp custom-length leads | any | OPTIONAL |
| T5 | Slim screwdriver >= 60 mm shaft | 1 pc | <= 4 mm diameter (deep screw wells) | any | KEEP |
| T6 | 3D printer with two-filament support | 1 pc | Bambu Lab P1S + AMS (256 mm bed); single-colour printers can print one colour | any | KEEP |

## Deliberately not in this build
The old 470 µF capacitor, M3 hardware, 8-LED lighting, separate charger + boost boards, a scan trigger, SD card, light diffuser, custom PCB or AI accelerator.

The wire-by-wire cut list (colour, gauge, length) is in [CONNECTIONS.md](CONNECTIONS.md); WireViz also writes it as `hardware/harness/arc22_harness.tsv`.
