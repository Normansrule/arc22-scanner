# Measurements — what to measure on YOUR parts

Enter values in `measurements/my_units.toml` (copy from `my_units.toml.example`) under `[measured]`, then run `bash scripts/rebuild_all.sh`. Every value you leave out keeps its nominal guess and stays flagged **VERIFY** in each build.

Use digital calipers, measure twice, record the photo file name next to each number. Axes are given for the module as installed (see [CAD.md](CAD.md)).

## Display (Hosyond 4.0" ST7796S + XPT2046)
| Key | Measure | Nominal |
|---|---|---|
| `DISP_PCB_W`, `DISP_PCB_H`, `DISP_PCB_T` | PCB width (short side), height (long side), thickness | 61.74, 108.04, 1.6 |
| `DISP_GLASS_W`, `DISP_GLASS_H` | outer edge of the glass / touch film | 61.0, 97.0 |
| `DISP_GLASS_OFF_Z` | glass centre minus PCB centre along the long side (+ = away from the header) | 2.5 |
| `DISP_ACTIVE_W`, `DISP_ACTIVE_H`, `DISP_ACTIVE_OFF_Z`, `DISP_ACTIVE_OFF_Y` | lit pixel area and its offset (power it, photograph it with a ruler) | 55.68, 83.52, 4.0, 0 |
| `DISP_GLASS_STACK` | PCB front face to glass front face | 4.6 |
| `DISP_BACK_POP` | tallest back-side part except the header (SD slot, regulator) | 4.0 |
| `DISP_HDR_PINS`, `DISP_HDR_INSET`, `DISP_HDR_SPACER` | header pin count, row centre to PCB edge, plastic spacer height | 14, 3.0, 2.5 |
| `DISP_BARE_SIDE`, `DISP_BARE_END_HDR`, `DISP_BARE_END_FAR` | **bare** PCB (no parts, no glass) at each corner: width from the long edge, length at the header end and at the far end | 5.0, 6.0, 2.5 |

## Camera (Arducam Mini / Mini Plus)
| Key | Measure | Nominal |
|---|---|---|
| — | **Mini or Mini Plus?** (printed on the PCB) → `fetch_libraries.py --camera` | — |
| `CAM_PCB_W`, `CAM_PCB_H`, `CAM_PCB_T` | PCB size | 24.4, 34.1, 1.6 |
| `CAM_HOLDER_SQ`, `CAM_LENS_D`, `CAM_LENS_PROJ` | lens-holder base, lens barrel diameter, PCB front to lens front | 14.5, 14.0, 20.0 |
| `CAM_OPT_OFF_Z`, `CAM_OPT_OFF_Y` | lens centre minus PCB centre | 3.0, 0 |
| `CAM_BACK_POP`, `CAM_HDR_INSET` | tallest back part; header row to bottom edge (note if pins point back or down) | 3.0, 2.0 |
| `CAM_BARE_CORNER` | bare square at each corner (both faces) | 4.0 |

## ESP32-S3-N16R8 board
| Key | Measure | Nominal |
|---|---|---|
| `ESP_L`, `ESP_W`, `ESP_T` | length, width, PCB thickness | 69.0, 25.5, 1.6 |
| `ESP_TOP_POP` | tallest top-side part (module shield, USB-C, buttons) | 3.4 |
| `ESP_HDR_LEN`, `ESP_HDR_OFF_X`, `ESP_HDR_SPACER` | header row length, its centre offset along the board, spacer height | 55.88, 0, 2.5 |
| `ESP_USB_PROJ`, `ESP_USB_HALF_SPAN` | USB-C overhang past the PCB end; half the span across the connector(s) | 1.5, 11.0 |
| `ESP_BARE_CORNER` | bare square at the antenna-end corners (top side) and beyond the header ends (back side) | 3.0 |

## Wiring and cables
| Key | Measure | Nominal |
|---|---|---|
| `DUPONT_HOUSING_L`, `DUPONT_HOUSING_W` | female housing length when seated on the pin; width | 14.0, 2.6 |
| `WIRE_STRAIGHT_EXIT` | how far the wire runs straight out of the housing before it can bend | 6.0 |
| `WIRE_BEND_R` | first **relaxed** bend radius of a real bundle (bend it gently, measure the inside radius) | 10.0 |
| `USB_PLUG_T`, `USB_PLUG_W` | overmold thickness/width of your programming cable | 7.0, 12.4 |

## Power parts and hardware
| Key | Measure | Nominal |
|---|---|---|
| `BAT_L`, `BAT_W`, `BAT_T` | battery pack | 69, 37, 18 |
| `CHG_L`, `CHG_W`, `CHG_H`, `CHG_USB_OFF_Y`, `CHG_BARE_CORNER` | charger PCB along/across the USB axis, tallest part, USB-C offset, bare front corners | 21, 26, 11, −6, 3 |
| `BTN_HOLE_D`, `BTN_BODY_D`, `BTN_DEPTH` | panel hole, widest body/nut, depth incl. terminals + solder | 12.5, 15, 22 |
| `M2_HEAD_D` | screw head diameter (≤ ~4) | 3.8 |
| `FOAM_T` | foam thickness you bought (0.5–1.0) | 0.8 |

## Record sheet (copy into your notes)
| Item | Value | Photo | Date |
|---|---|---|---|
| | | | |
