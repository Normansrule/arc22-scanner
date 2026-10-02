# Safety

This build combines a lithium-ion cell, a boost converter, hand soldering and a closed plastic case. Read this before Stage 4 of the [build guide](BUILD_GUIDE.md).

## Battery
- Use a **protected** 1S 3.7 V lithium-ion pack (reference: Adafruit #354, 4400 mAh, ~69 × 37 × 18 mm). Keep its factory protection circuit, wrapper and leads. Do not cut into the wrapper or solder to the cells.
- Never connect the raw cell to the ESP32 **3V3** or **5V** pins. The battery goes to the charger's battery connector only.
- Keep the charger, screw tips, solder points and anything sharp off the battery wrapper. The cradle ribs are foam-lined for this reason.
- Stop and isolate the pack (outdoors, on a non-flammable surface) if it swells, smells, hisses or gets hot.

## Charger (candidate part, not yet validated)
The Adafruit #6106 board (bq25185 charger + TPS61023 5 V boost) is a **candidate** until you have measured it in this build:
- rated 5 V output at 1 A maximum;
- its boost converter **cannot switch on into a high load — it stalls above about 200 mA at start-up**;
- a fixed **6 hour** charge safety timer (a 4400 mAh cell at the default 1 A charge rate is close to that limit);
- EN pulled low disables the 5 V output.

Measure start-up, peak current (Wi-Fi + detection + backlight), restart behaviour and board temperature. **A firmware delay is not proof that inrush is solved.** Don't reflexively add a big capacitor (the old 470 µF part is deliberately *not* in this design) and never defeat a protection feature. If the board fails these tests, use a re-engineered replacement and update [BOM.md](BOM.md).

## Power switch
The 12 mm latching button connects the charger's **EN** to GND: **closed = output OFF, open = output ON**. This is the charger enable, not the ESP32 reset/EN pin. It may not isolate every path — for example, power fed back through the ESP32's USB port.

## Programming sequence (every time)
1. Turn the scanner **off** with the button.
2. Disconnect the **charging** USB-C cable.
3. Unplug the **RUN** two-pin pigtail (isolates the charger's 5 V from the ESP32).
4. Only then connect the computer's data-capable USB-C cable to the **ESP32**.

Reverse the order afterwards. Charge only through the **charger's** USB-C socket, never the ESP32's.

## Mains and enclosure
- Use a normal 5 V USB charger for charging.
- The case is enclosed, **not waterproof**. It has no Ingress Protection (IP) rating; keep it dry.
- Do not close the case over a pinched wire. Fully wired halves must close by hand before any screw (Stage 3).
- First closed-case runs are **monitored** (Stage 6). Never leave it charging unattended until you have.

## Soldering and tools
Ventilate flux fumes, wear eye protection when clipping leads, unplug everything before soldering near the battery leads, and insulate every splice with heat-shrink.
