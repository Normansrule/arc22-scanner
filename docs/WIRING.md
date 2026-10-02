# Wiring — pin by pin

**Rule zero: every General-Purpose Input/Output (GPIO) pin on the ESP32-S3 is 3.3 V logic. Never connect a 5 V signal to it.** The supply a module *runs from* (its VCC) and the voltage its *signals* use are different questions — don't confuse them.

Verify every label against the silkscreen of **your** boards before you plug anything in.

![Wiring at a glance](img/wiring_overview.png)

**Every wire, pin by pin, with colour, gauge and cut length: [CONNECTIONS.md](CONNECTIONS.md)** (generated from `hardware/connections.csv`, full harness drawing in [SVG](img/harness.svg)). The pin numbers are the single source in `firmware/main/pins.h`; `tools/verify_project.py` and `tools/build_mfg.py` check that the firmware, this page and the wire list agree.

## Signal wiring

| ESP32-S3 | Direction | Goes to | Notes |
|---|---|---|---|
| GPIO4 | ↔ | Camera **SDA** | Inter-Integrated Circuit (I2C) data — sensor registers |
| GPIO5 | → | Camera **SCL** | I2C clock |
| GPIO6 | → | TFT **LED/BL** | **Only** if your display has a backlight driver transistor; otherwise leave unconnected and keep `ARC_BACKLIGHT_GPIO_ENABLED=n` |
| GPIO7 | → | TFT **RESET** | |
| GPIO8 | → | TFT **DC/RS** | data/command select |
| GPIO9 | → | Touch **T_CS** | + 10 kΩ pull-up to 3V3 |
| GPIO10 | → | TFT **CS** | + 10 kΩ pull-up to 3V3 |
| GPIO11 | → | TFT **MOSI** *and* touch **T_DIN** | shared Serial Peripheral Interface (SPI) data out |
| GPIO12 | → | TFT **SCK** *and* touch **T_CLK** | shared SPI clock |
| GPIO13 | ← | Touch **T_DO** | the only device driving this line |
| GPIO14 | ← | Touch **T_IRQ** | touch interrupt |
| GPIO15 | → | Camera **CS** | + 10 kΩ pull-up to 3V3 |
| GPIO16 | ← | Camera **MISO** | |
| GPIO17 | → | Camera **MOSI** | |
| GPIO18 | → | Camera **SCLK** | |
| GND | — | every module GND | one common ground |

- **Leave TFT MISO/SDO and the SD-card pins unconnected.** Only the touch controller drives GPIO13.
- **The camera needs both SPI and I2C.** An Arducam Mini with only SPI wired will fail the I2C sensor-ID check in commissioning.
- **Reserved:** GPIO19/20 (native USB — needed for programming), GPIO0/3/45/46 (boot strapping), GPIO26–37 (flash and octal PSRAM on N16R8 modules), GPIO43/44 (serial console).
- The display and touch share one SPI bus (SPI3 in firmware); the camera has its own bus (SPI2) so a slow camera read never fights the screen.

### Pull-ups (3 × 10 kΩ, optional 2 × 4.7 kΩ)
Put a 10 kΩ resistor from each chip-select line (TFT CS, touch CS, camera CS) to 3V3. They keep every device deselected while the ESP32 boots, which stops a half-booted bus from confusing the others. Splice them into the jumper at the ESP32 end with heat-shrink — no custom board needed.
Add 4.7 kΩ I2C pull-ups on SDA/SCL **only if** your camera board has none fitted (look for two resistors near the header, or measure SDA→VCC with the board unpowered).

### Backlight pulldown (optional 100 kΩ)
Only after you have **verified** an onboard backlight transistor: a 100 kΩ from the LED/BL line to GND keeps the backlight off while GPIO6 floats during boot.

## Module supply (VCC) — resolve the camera conflict for YOUR board

| Module | Supply | Check before connecting |
|---|---|---|
| ESP32-S3 board | system 5 V → **5V / VIN** pin | the board's own regulator makes 3V3 |
| Display | 5 V **or** 3.3 V | many MSP4021-style boards have a 3.3 V regulator and accept 5 V on VCC — **verify on yours** (find the regulator, read its marking) |
| Camera | **conflict in old notes** | later ARC notes run the Arducam from regulated 5 V; older firmware notes say 3.3 V. Arducam Mini *Plus* boards carry their own regulator; plain Mini boards may not. Identify the regulator on **your** board; if unsure, use 3.3 V from the ESP32 3V3 pin and measure the current draw first |

Whatever VCC a module uses, its **signal pins still go straight to 3.3 V ESP32 GPIO** — if a module would output 5 V logic, it does not belong on this bus.

## Power path

```
 Li-ion 1S 4400 mAh (protected, factory leads)
        │  JST
        ▼
 Charger board (Adafruit #6106, bq25185 + 5 V boost)   ◄── charge here: the CHARGER USB-C port
   BATT          5V+ ──► [RUN two-pin pigtail, removable] ──► system 5 V ──► ESP32 5V, display VCC*, camera VCC*
   GND ─────────────────────────────────────────────────────► common GND
   EN  ──► [12 mm latching button] ──► GND        (button CLOSED = 5 V OFF, OPEN = 5 V ON)
                                                        * only if verified 5 V-compatible
```

- **EN here is the charger's boost enable, not the ESP32 reset/EN pin.**
- Use ~22 AWG stranded wire, properly insulated, for battery and 5 V distribution. **Do not carry battery current through a chain of loose breadboard jumpers.**
- **Never connect the raw cell to the ESP32 3V3 or 5V pins.**
- The button may not isolate every supply path (for example, the ESP32 USB). Follow the programming sequence in [SAFETY.md](SAFETY.md).

## Where the wires run inside the case

Five reserved routes are modelled as tubes and checked against both shells ([CAD.md](CAD.md)):

| Route | From → to | Notes |
|---|---|---|
| camera_to_esp32 | camera header (back/down) → ESP32 header field | 8 jumpers |
| esp32_to_display | ESP32 header field → display header field | ~13 jumpers |
| power_trunk_to_charger | display/ESP32 area → charger | 5 V + GND trunk, RUN pigtail lives here |
| battery_to_charger | battery top → over the hand loop → rear leg → charger | factory battery leads, extended with 22 AWG if needed |
| button_to_charger | button terminals → charger EN/GND | |

![Inside the LEFT shell: modules (dark) and reserved cable routes (orange)](img/arc22_left_interior.png)

Dress bundles along these routes **before** closing; hold them with soft, removable restraints (fabric tape, hook-and-loop strap), never by trapping them under a rib or a screw boss.
