# Requirements

Every requirement has an ID, a verification method — **I**nspection, **A**nalysis (CAD/script), **D**emonstration, **T**est — and the place its evidence lives. Status is honest: **RECORDED** means a script checks it in this repository; **OPEN** means it needs your parts, printer or hardware ([VALIDATION.md](VALIDATION.md)).

## Goal A — snug modules, movable wires

| ID | Requirement | Method | Evidence | Status |
|---|---|---|---|---|
| MEC-01 | The enclosure **shall** be exactly two printed pieces, LEFT and RIGHT, joined by M2 screws only (no M3, no heat-set inserts). | I | `cad/out/print/`, [BOM](BOM.md) M1–M3 | RECORDED |
| MEC-02 | Each module **shall** register at verified bare corners/edges on soft pads or lay-in clips, never under screw pressure or a rigid bar across a header. | A, T | CAD check *screws: boss clear of every module*; Stage 1 + 3 | RECORDED / OPEN |
| MEC-03 | The clearance model of every board **shall** include the populated PCB, pin projection, the plugged 2.54 mm Dupont housing, a straight exit, the first relaxed bend and strain relief. | A | `cad/arc22_geometry.py` *hard* + *field*; CAD checks *hard parts* / *reserved fields* | RECORDED |
| MEC-04 | Wire space **shall** be reserved behind the display header, the camera pin row (back or down) and **both** ESP32 header rows. | A | CAD checks *reserved fields vs shells* | RECORDED |
| MEC-05 | Every module **shall** go in along its real insertion path without touching plastic (snap clips excepted). | A, D | CAD *insertion path (swept)*, 1 mm steps; Stage 3 | RECORDED / OPEN |
| MEC-06 | The RIGHT shell **shall** close onto the fully wired LEFT half with gentle hand pressure before any screw. | A, D | CAD *closing swept volume*; Stage 3 | RECORDED / OPEN |
| MEC-07 | Display and camera **shall** have open backs; nothing **shall** touch the glass or the lens. | A, I | CAD *glass_air*, *lens_air*, *open_back*; Stage 1 | RECORDED / OPEN |
| MEC-08 | Cable routes camera ↔ ESP32 ↔ display ↔ battery ↔ charger **shall** be open lay-in channels inside the cavity. | A | CAD *cable routes* | RECORDED |
| MEC-09 | Fit **shall** be tuned by named measured values only — never by scaling the scanner. | I | `cad/arc22_params.py`, `measurements/` | RECORDED |

## Shape and printing

| ID | Requirement | Method | Evidence | Status |
|---|---|---|---|---|
| SHP-01 | D-shaped silhouette with curved bow, integrated upper-bow camera fairing and rear touchscreen; envelope ≈ 218 × 118 × 218 mm. | I, A | CAD *envelope*; renders | RECORDED |
| SHP-02 | Only functional openings: lens, touch window, button, charger USB-C, screw wells, hand loop. The hand loop **shall not** expose the cavity. | A, I | CAD *hand loop* | RECORDED |
| PRT-01 | Each shell **shall** fit a Bambu Lab P1S bed (256 mm) with a 10 mm margin. | A | CAD *printer* | RECORDED |
| PRT-02 | White and cyan **shall** be aligned material regions of the same shell (one transform), not separate parts. | A | CAD *two-colour regions*; `PRINT_TRANSFORMS.json` | RECORDED |
| PRT-03 | Print meshes **shall** be watertight with consistent winding. | A | [mesh checks](validation/mesh_checks.md) | RECORDED |
| PRT-04 | The colour assignment **shall** be confirmed in the installed slicer before printing. | D | Stage 3, [PRINTING.md](PRINTING.md) | OPEN |

## Electrical and safety

| ID | Requirement | Method | Evidence | Status |
|---|---|---|---|---|
| ELE-01 | Every ESP32-S3 signal **shall** be 3.3 V logic; no 5 V signal on any GPIO. | A, I | `tools/build_mfg.py` net check; [CONNECTIONS](CONNECTIONS.md) | RECORDED |
| ELE-02 | The wiring **shall** match the firmware pin map exactly. | A | `build_mfg.py` traces every `pins.h` GPIO to its module pin | RECORDED |
| ELE-03 | TFT CS, touch CS and camera CS **shall** each have a 10 kΩ pull-up to 3V3. | A | `build_mfg.py` pull-up check | RECORDED |
| ELE-04 | No GPIO, the 3V3 rail or a module header pin **shall** connect to 5 V, battery or a second wire on one pin. | A | `build_mfg.py` | RECORDED |
| ELE-05 | Unused pins (GPIO19/20 USB, boot straps, flash/PSRAM pins, TFT SDO) **shall** stay unconnected. | A | `tools/verify_project.py` | RECORDED |
| SAF-01 | The raw cell **shall** connect only to the charger, keeping its factory protection, wrapper and leads. | I | [SAFETY.md](SAFETY.md) | OPEN |
| SAF-02 | The power button **shall** switch the charger EN (closed = off); a removable RUN pigtail **shall** isolate 5 V for programming. | I, D | Stage 4 | OPEN |
| SAF-03 | Start-up, peak current, restart and temperature of the charger **shall** be measured with the real load before closed-case use. | T | Stage 4 + 6 | OPEN |
| SAF-04 | The product **shall not** claim waterproofing or an Ingress Protection (IP) rating. | I | docs | RECORDED |

## Goal B — local computer vision

| ID | Requirement | Method | Evidence | Status |
|---|---|---|---|---|
| SW-01 | Object detection **shall** run on the ESP32-S3; Wi-Fi only for article lookup and off during detection. | I, D | `firmware/main/main.cpp`; Stage 5 | OPEN |
| SW-02 | The default build **shall** be commissioning-only (display, touch, camera) before inference is enabled. | I | `sdkconfig.defaults`, `verify_project.py` | RECORDED |
| SW-03 | Every firmware dependency **shall** be pinned (ESP-IDF 5.4.2, arduino-esp32 3.2.1, ESP-DL 3.3.6, coco_detect 0.4.0, LovyanGFX 1.2.28, ArduCAM 066a7ea). | I | `PINNED_VERSIONS.json`, `verify_project.py` | RECORDED |
| SW-04 | The firmware **shall** compile with the pinned versions, with a kept build log. | T | `firmware` workflow | OPEN |
| SW-05 | Show up to 8 boxes, selectable by touch, with Wikipedia intro or QR fallback; latency **shall** be measured, never promised as live video. | T | Stage 5 | OPEN |
| SW-06 | Wi-Fi credentials **shall** never be committed. | A | `.gitignore`, CI | RECORDED |

## Open-source manufacturing

| ID | Requirement | Method | Evidence | Status |
|---|---|---|---|---|
| MFG-01 | Editable sources **shall** be published: CadQuery scripts, STEP, connection CSV, BOM CSV, firmware. | I | repository | RECORDED |
| MFG-02 | Every output **shall** regenerate from source with one command. | D | `scripts/rebuild_all.sh`, CI | RECORDED |
| MFG-03 | Hardware, software and documentation **shall** carry open licences (CERN-OHL-P-2.0, MIT, CC BY 4.0). | I | `LICENSE*` | RECORDED |
| MFG-04 | Each release **shall** include a manufacturing ZIP, SBOM and SHA-256 checksums with provenance. | I | `release` workflow | RECORDED |
| MFG-05 | Documentation **shall** separate recorded checks from physical tests and never call the build perfect-fit or fully tested. | I | [VALIDATION.md](VALIDATION.md) | RECORDED |
