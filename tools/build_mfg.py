#!/usr/bin/env python3
"""
build_mfg.py — the manufacturing data package, generated from three source files:

  hardware/bom.csv          every part, quantity, specification and where to get it
  hardware/connectors.yml   every header / splice and its pin order
  hardware/connections.csv  every wire, pin by pin (colour, gauge, length)

It checks them against each other AND against the firmware pin map
(firmware/main/pins.h), then writes:

  hardware/harness/arc22_harness.yml + .svg .png .html .tsv   WireViz harness drawing + wire list
  docs/img/harness.svg, docs/img/harness.png                    the same drawing for the website/README
  docs/CONNECTIONS.md                                           pin-by-pin tables, one per module
  docs/BOM.md                                                   the bill of materials as a readable page
  dist/arc22-manufacturing-<version>.zip   (with --package)     everything a maker or workshop needs

Run:  python tools/build_mfg.py            (needs: pip install wireviz==0.4.1, apt install graphviz)
      python tools/build_mfg.py --package  (also builds the ZIP)
"""
from __future__ import annotations

import argparse
import csv
import datetime
import json
import pathlib
import re
import shutil
import subprocess
import sys
import zipfile
from collections import defaultdict

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
HW = ROOT / "hardware"
HARNESS = HW / "harness"
DOCS = ROOT / "docs"

# What each firmware pin must reach (part, pin label). Splices/tees are followed through.
EXPECT = {
    "PIN_CAM_SDA": [("CAM", "SDA")], "PIN_CAM_SCL": [("CAM", "SCL")], "PIN_CAM_CS": [("CAM", "CS")],
    "PIN_CAM_MISO": [("CAM", "MISO")], "PIN_CAM_MOSI": [("CAM", "MOSI")], "PIN_CAM_SCLK": [("CAM", "SCK")],
    "PIN_TFT_BL": [("TFT", "LED")], "PIN_TFT_RST": [("TFT", "RESET")], "PIN_TFT_DC": [("TFT", "DC/RS")],
    "PIN_TOUCH_CS": [("TFT", "T_CS")], "PIN_TFT_CS": [("TFT", "CS")],
    "PIN_TFT_MOSI": [("TFT", "SDI(MOSI)"), ("TFT", "T_DIN")], "PIN_TFT_SCLK": [("TFT", "SCK"), ("TFT", "T_CLK")],
    "PIN_TOUCH_MISO": [("TFT", "T_DO")], "PIN_TOUCH_IRQ": [("TFT", "T_IRQ")],
}
PULLED_UP = {"PIN_CAM_CS", "PIN_TFT_CS", "PIN_TOUCH_CS"}
PASS_THROUGH = {"PU1", "PU2", "PU3", "YMOSI", "YSCK"}  # IN<->OUT / IN<->A,B are the same net
COLOUR_NAMES = {"BK": "black", "WH": "white", "GY": "grey", "PK": "pink", "RD": "red", "OG": "orange",
                "YE": "yellow", "GN": "green", "TQ": "turquoise", "LB": "light blue", "BU": "blue",
                "VT": "violet", "BN": "brown"}
NICE = {"ESP32": "ESP32-S3", "TFT": "Display", "CAM": "Camera", "CHG": "Charger", "BAT": "Battery",
        "BTN": "Button", "RUN": "RUN pigtail", "B3V3": "3V3 splice", "B5V": "5V splice", "BGND": "GND splice",
        "PU1": "pull-up tee 1", "PU2": "pull-up tee 2", "PU3": "pull-up tee 3", "YMOSI": "MOSI Y-splice",
        "YSCK": "SCK Y-splice"}


def repo_url() -> str:
    """https://github.com/<owner>/arc22-scanner from the git remote, or the OWNER placeholder."""
    try:
        url = subprocess.run(["git", "remote", "get-url", "origin"], cwd=ROOT, capture_output=True, text=True,
                             check=True).stdout.strip()
        m = re.search(r"github\.com[:/]([^/]+)/([^/.]+)", url)
        if m:
            return f"https://github.com/{m.group(1)}/{m.group(2)}"
    except Exception:
        pass
    return "https://github.com/Normansrule/arc22-scanner"


def load():
    conns = yaml.safe_load((HW / "connectors.yml").read_text())
    wires = list(csv.DictReader((HW / "connections.csv").open()))
    bom = list(csv.DictReader((HW / "bom.csv").open()))
    pins = {m.group(1): int(m.group(2)) for m in
            re.finditer(r"#define\s+(PIN_\w+)\s+(\d+)", (ROOT / "firmware/main/pins.h").read_text())}
    return conns, wires, bom, pins


def check(conns, wires, pins) -> list[str]:
    errs = []
    used = defaultdict(int)
    for w in wires:
        for side in ("from", "to"):
            c, p = w[side], w[f"{side}_pin"]
            if c not in conns:
                errs.append(f"wire {w['wire']}: unknown connector {c}")
            elif p not in conns[c]["pinlabels"]:
                errs.append(f"wire {w['wire']}: {c} has no pin {p}")
            used[(c, p)] += 1
    # graph of nets
    adj = defaultdict(set)

    def link(a, b):
        adj[a].add(b)
        adj[b].add(a)

    for w in wires:
        link((w["from"], w["from_pin"]), (w["to"], w["to_pin"]))
    for c in PASS_THROUGH:
        labels = conns[c]["pinlabels"]
        for other in labels[1:]:
            if other != "3V3":
                link((c, labels[0]), (c, other))

    def reach(start):
        seen, todo = {start}, [start]
        while todo:
            n = todo.pop()
            for m in adj[n]:
                if m not in seen:
                    seen.add(m)
                    todo.append(m)
        return seen

    for name, gpio in pins.items():
        net = reach(("ESP32", f"GPIO{gpio}"))
        for target in EXPECT.get(name, []):
            if target not in net:
                errs.append(f"{name} = GPIO{gpio} (pins.h) does not reach {target[0]}.{target[1]} in connections.csv")
        if name in PULLED_UP:
            tee = next((c for c, p in net if c.startswith("PU")), None)
            if not tee or ("B3V3", tee) not in reach((tee, "3V3")):
                errs.append(f"{name}: no 10 kOhm pull-up tee to the 3V3 splice")
        # no GPIO net may touch a supply
        bad = [n for n in net if n[0] in ("B5V", "BGND", "B3V3", "RUN", "CHG", "BAT")]
        if bad:
            errs.append(f"{name}: GPIO net touches supply {bad}")
    for (c, p), n in used.items():
        if c in ("ESP32", "TFT", "CAM") and n > 1:
            errs.append(f"{c}.{p} has {n} wires on one header pin — use a splice")
    # 3V3 rail must only be fed by the ESP32
    rail = reach(("ESP32", "3V3"))
    if any(n[0] in ("B5V", "RUN", "CHG", "BAT") for n in rail):
        errs.append("3V3 rail is connected to a 5 V / battery net")
    return errs


def harness_yaml(conns, wires) -> dict:
    out = {"metadata": {"title": "ARC-22 harness", "pn": "ARC22-HAR-01",
                        "notes": "Generated from hardware/connections.csv by tools/build_mfg.py — edit the CSV, not this file."},
           "options": {"bgcolor": "WH", "color_mode": "SHORT", "fontname": "arial"},
           "connectors": {}, "cables": {}, "connections": []}
    for name, c in conns.items():
        d = {"type": c["type"], "subtype": c.get("subtype", ""), "pinlabels": c["pinlabels"]}
        if c.get("notes"):
            d["notes"] = c["notes"]
        out["connectors"][name] = d
    groups = defaultdict(list)
    for w in wires:
        groups[w["group"]].append(w)
    titles = {"camera": "Camera bundle (Dupont 26 AWG)", "display": "Display + touch bundle (Dupont 26 AWG)",
              "esp32": "ESP32 supply taps", "power": "Power (22 AWG / factory leads)"}
    for g, ws in groups.items():
        cname = f"W_{g}"
        out["cables"][cname] = {"category": "bundle", "colors": [w["colour"] for w in ws],
                                "notes": titles.get(g, g)}
        for k, w in enumerate(ws, 1):
            fi = conns[w["from"]]["pinlabels"].index(w["from_pin"]) + 1
            ti = conns[w["to"]]["pinlabels"].index(w["to_pin"]) + 1
            out["connections"].append([{w["from"]: [fi]}, {cname: [k]}, {w["to"]: [ti]}])
    return out


def render(doc: dict) -> None:
    HARNESS.mkdir(parents=True, exist_ok=True)
    y = HARNESS / "arc22_harness.yml"
    y.write_text("# GENERATED by tools/build_mfg.py from hardware/connections.csv + connectors.yml\n"
                 + yaml.safe_dump(doc, sort_keys=False, width=120))
    if not shutil.which("dot"):
        print("WARNING: Graphviz 'dot' not found (sudo apt install graphviz) — harness drawing not re-rendered")
        return
    exe = shutil.which("wireviz")
    cmd = [exe] if exe else [sys.executable, "-m", "wireviz.wv_cli"]
    subprocess.run(cmd + ["-f", "hpst", str(y)], check=True, cwd=HARNESS)
    (DOCS / "img").mkdir(exist_ok=True)
    for ext in ("svg", "png"):
        shutil.copy2(HARNESS / f"arc22_harness.{ext}", DOCS / "img" / f"harness.{ext}")


HEX = {"BK": "#222222", "WH": "#9aa5ab", "GY": "#7d8790", "PK": "#e46fb0", "RD": "#d8322b", "OG": "#f08a24",
       "YE": "#d9b400", "GN": "#2e9b4f", "TQ": "#19b5b0", "LB": "#6cb8ea", "BU": "#2265c8", "VT": "#7b3fc4",
       "BN": "#8a5a35"}


def wiring_overview(conns, wires, out: pathlib.Path) -> None:
    """Clean schematic-style pinout: ESP32 header J1 in the middle, camera left, display right,
    supplies as net labels, power path along the bottom. Same data as the harness drawing."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch

    fig, ax = plt.subplots(figsize=(15, 10.6))
    ax.set_xlim(0, 150)
    ax.set_ylim(-34, 100)
    ax.axis("off")
    ink, sub = "#17303d", "#4c6470"
    RH = 3.6  # row height

    def box(x, y_top, w, title, sub_t, labels, side):
        h = RH * len(labels) + 8
        ax.add_patch(FancyBboxPatch((x, y_top - h), w, h, boxstyle="round,pad=0.4,rounding_size=1.6",
                                    fc="#f7fafb", ec=ink, lw=1.6))
        ax.text(x + w / 2, y_top - 2.6, title, ha="center", va="center", fontsize=12.5, weight="bold", color=ink)
        ax.text(x + w / 2, y_top - 5.6, sub_t, ha="center", va="center", fontsize=8.2, color=sub)
        pos = {}
        for i, lab in enumerate(labels):
            yy = y_top - 9.5 - i * RH
            px = x + w if side == "right" else x
            ax.plot([px], [yy], "o", ms=4.2, color=ink, zorder=5)
            ha = "right" if side == "right" else "left"
            ax.text(px + (-1.6 if side == "right" else 1.6), yy, f"{lab}", ha=ha, va="center", fontsize=9.4, color=ink)
            pos[lab] = (px, yy)
        return pos

    esp_labels = conns["ESP32"]["pinlabels"]
    esp_l = box(63, 96, 24, "ESP32-S3", "header J1 · 3.3 V logic", [f"{i + 1}  {p}" for i, p in enumerate(esp_labels)], "left")
    esp_r = {k: (v[0] + 24, v[1]) for k, v in esp_l.items()}
    for k, (xx, yy) in esp_r.items():
        ax.plot([xx], [yy], "o", ms=4.2, color=ink, zorder=5)
    cam = box(6, 86, 26, "Camera", "Arducam Mini OV2640", conns["CAM"]["pinlabels"], "right")
    tft = box(118, 90, 27, "Display + touch", "ST7796S / XPT2046", conns["TFT"]["pinlabels"], "left")

    def esp_pin(label):
        i = esp_labels.index(label)
        return f"{i + 1}  {label}"

    # trace each ESP32 pin through tees / Y-splices to module pins
    by_from = defaultdict(list)
    for w in wires:
        by_from[(w["from"], w["from_pin"])].append(w)

    def ends(node, colour=None, pulled=False):
        out = []
        for w in by_from.get(node, []):
            c, p = w["to"], w["to_pin"]
            col = colour or w["colour"]
            if c in PASS_THROUGH:
                labels = conns[c]["pinlabels"]
                is_pu = c.startswith("PU")
                for o in labels[1:]:
                    if o != "3V3":
                        out += ends((c, o), col, pulled or is_pu)
            else:
                out.append((c, p, col, pulled))
        return out

    for lab in esp_labels:
        if not lab.startswith("GPIO"):
            continue
        for c, p, col, pulled in ends(("ESP32", lab)):
            if c == "CAM":
                (x0, y0), (x1, y1) = esp_l[esp_pin(lab)], cam[p]
            elif c == "TFT":
                (x0, y0), (x1, y1) = esp_r[esp_pin(lab)], tft[p]
            else:
                continue
            xm = (x0 + x1) / 2
            xb, yb = (xm - 4 if x1 < x0 else xm + 4), y0 + (y1 - y0) * 0.15
            ax.plot([x0, xb, x1], [y0, yb, y1], color=HEX.get(col, "#555"), lw=2.4, solid_capstyle="round", zorder=3)
            if pulled:
                mx, my = xb + 0.8 * (x1 - xb), yb + 0.8 * (y1 - yb)
                ax.plot([mx], [my], "o", ms=8, mfc=HEX["OG"], mec="white", mew=1.5, zorder=6)

    # supply net labels
    def flag(pt, text, colour, side):
        x, y = pt
        dx = -9 if side == "left" else 9
        ax.plot([x, x + dx * 0.55], [y, y], color=colour, lw=2.4)
        ax.text(x + dx * 0.6, y, text, ha="right" if side == "left" else "left", va="center", fontsize=9,
                weight="bold", color="white", bbox=dict(boxstyle="round,pad=0.25", fc=colour, ec="none"))

    for pin, text, colour in (("VCC", "3V3*", HEX["OG"]), ("GND", "GND", HEX["BK"])):
        x, y = cam[pin]
        ax.text(x - 12, y, text, ha="right", va="center", fontsize=9, weight="bold", color="white",
                bbox=dict(boxstyle="round,pad=0.25", fc=colour, ec="none"))
    flag(tft["VCC"], "5V*", HEX["RD"], "left")
    flag(tft["GND"], "GND", HEX["BK"], "left")
    flag(esp_r[esp_pin("5V")], "5V", HEX["RD"], "right")
    flag(esp_r[esp_pin("GND")], "GND", HEX["BK"], "right")
    flag(esp_l["1  3V3"], "3V3 out", HEX["OG"], "left")
    ax.plot([7.2], [45], "o", ms=8, mfc=HEX["OG"], mec="white", mew=1.5)
    ax.text(9, 45, "10 kΩ pull-up to 3V3 (soldered tee near the module)", fontsize=8.6, color=sub, va="center")
    ax.text(6, 41.5, "* camera VCC: 3V3, or 5 V only if your board has a regulator\n* display VCC: 5 V only if verified, else 3V3\n"
            "Not connected: display SDO(MISO), SD pins; J1 RST, GPIO3, GPIO46",
            fontsize=8.6, color=sub, va="top")

    # power path along the bottom
    y = -16
    chain = [("Battery", "1S 4400 mAh\nprotected", HEX["BK"]), ("Charger #6106", "bq25185 + 5 V boost\ncharge via ITS USB-C", HEX["BK"]),
             ("RUN pigtail", "2-pin, removable\nunplug to program", HEX["RD"]), ("5 V splice", "→ ESP32 5V\n→ display VCC*", HEX["RD"])]
    xs = [8, 44, 80, 114]
    for (t, st, _), x in zip(chain, xs):
        ax.add_patch(FancyBboxPatch((x, y - 6), 28, 12, boxstyle="round,pad=0.4,rounding_size=1.6", fc="#eef6fb",
                                    ec=ink, lw=1.4))
        ax.text(x + 14, y + 2.4, t, ha="center", fontsize=11, weight="bold", color=ink)
        ax.text(x + 14, y - 2.6, st, ha="center", va="center", fontsize=8, color=sub)
    for a, b, lab in ((xs[0] + 28.8, xs[1] - 0.8, "JST-PH"), (xs[1] + 28.8, xs[2] - 0.8, "5V+ / 5V−  22 AWG"),
                      (xs[2] + 28.8, xs[3] - 0.8, "22 AWG")):
        ax.annotate("", (b, y), (a, y), arrowprops=dict(arrowstyle="-|>", lw=2.2, color=HEX["RD"]))
        ax.text((a + b) / 2, y + 7.6, lab, ha="center", fontsize=7.6, color=sub)
    ax.add_patch(FancyBboxPatch((44, -33), 28, 7.5, boxstyle="round,pad=0.4,rounding_size=1.6", fc="#fff6e8",
                                ec=ink, lw=1.4))
    ax.text(58, -29.2, "Latching button: EN → GND\nclosed = OFF · open = ON", ha="center", va="center", fontsize=8.4, color=ink)
    ax.plot([58, 58], [y - 6.6, -25.3], color=HEX["WH"], lw=2.2)
    ax.text(6, 2, "Power path", fontsize=12.5, weight="bold", color=ink)
    ax.text(150, -33, "ARC-22 · generated from hardware/connections.csv · verify every label on your own boards",
            ha="right", fontsize=7.5, color=sub)
    fig.savefig(out, dpi=130, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def connections_md(conns, wires) -> str:
    by = defaultdict(list)
    for w in wires:
        by[w["group"]].append(w)
    L = ["# Pin-by-pin connections", "",
         f"Generated from [`hardware/connections.csv`]({repo_url()}/blob/main/hardware/connections.csv) "
         "by `tools/build_mfg.py`, and checked against the firmware pin map (`firmware/main/pins.h`). "
         "Every ESP32-S3 GPIO is **3.3 V logic**. Verify each header label on your own boards first.", "",
         "![Wiring at a glance](img/wiring_overview.png)", "",
         "Full harness drawing (every wire, splice and colour): [SVG](img/harness.svg) · [PNG](img/harness.png)", "",
         "Splices and tees are soldered and heat-shrunk: a **pull-up tee** is a 10 kΩ resistor from the "
         "signal to the 3V3 splice; a **Y-splice** joins one ESP32 pin to two module pins (a Dupont "
         "socket takes one wire). See [WIRING.md](WIRING.md) for why, and [SAFETY.md](SAFETY.md) before power.", ""]
    titles = {"camera": "Camera (Arducam Mini OV2640, 8-pin)", "display": "Display + touch (ST7796S / XPT2046, 14-pin)",
              "esp32": "ESP32-S3 supply taps", "power": "Power path (battery → charger → RUN → 5 V)"}
    for g, ws in by.items():
        L += [f"## {titles.get(g, g)}", "",
              "| # | From | → To | Signal | Wire | Length | Note |", "|---|---|---|---|---|---|---|"]
        for w in ws:
            col = COLOUR_NAMES.get(w["colour"], w["colour"])
            awg = w["awg"] if w["awg"] == "factory" else f"{w['awg']} AWG"
            ln = "—" if w["length_mm"] in ("", "0") else f"{w['length_mm']} mm"
            L.append(f"| {w['wire']} | {NICE.get(w['from'], w['from'])} **{w['from_pin']}** | "
                     f"{NICE.get(w['to'], w['to'])} **{w['to_pin']}** | {w['signal']} | {col}, {awg} | {ln} | {w['note']} |")
        L.append("")
    L += ["## Header pin order", "", "| Part | Pin 1 → last |", "|---|---|"]
    for name in ("ESP32", "TFT", "CAM", "CHG"):
        c = conns[name]
        L.append(f"| {NICE[name]} — {c['type']} | {' · '.join(f'{i}:{p}' for i, p in enumerate(c['pinlabels'], 1))} |")
    unused = [p for p in conns["TFT"]["pinlabels"] if not any(
        (w["to"] == "TFT" and w["to_pin"] == p) for w in wires)]
    L += ["", f"Unconnected on purpose: display **{', '.join(unused)}**; every ESP32 header J3 pin; "
          "GPIO19/20 (USB), GPIO0/3/45/46 (boot straps), GPIO26–37 (flash + PSRAM).", ""]
    return "\n".join(L)


def bom_md(bom) -> str:
    L = ["# Bill of materials", "",
         f"Generated from [`hardware/bom.csv`]({repo_url()}/blob/main/hardware/bom.csv) "
         "(open it in any spreadsheet) by `tools/build_mfg.py`. **KEEP** = core part, measure your unit · "
         "**CANDIDATE** = chosen but not yet validated in this build · **OPTIONAL** = only if a check says so. "
         "Buy against the specification, then measure ([MEASUREMENTS.md](MEASUREMENTS.md)).", ""]
    cats = defaultdict(list)
    for r in bom:
        cats[r["category"]].append(r)
    for cat, rows in cats.items():
        L += [f"## {cat}", "", "| ID | Part | Qty | Specification | Where | Status |", "|---|---|---|---|---|---|"]
        for r in rows:
            where = r["where_to_get"]
            if where.startswith("http"):
                where = f"[link]({where})"
            qty = f"{r['qty']} {r['unit']}".strip()
            spec = r["specification"] + (f" — {r['notes']}" if r["notes"] else "")
            L.append(f"| {r['id']} | {r['part']} | {qty} | {spec} | {where} | {r['status']} |")
        L.append("")
    L += ["## Deliberately not in this build",
          "The old 470 µF capacitor, M3 hardware, 8-LED lighting, separate charger + boost boards, a scan trigger, "
          "SD card, light diffuser, custom PCB or AI accelerator.", "",
          "The wire-by-wire cut list (colour, gauge, length) is in [CONNECTIONS.md](CONNECTIONS.md); "
          "WireViz also writes it as `hardware/harness/arc22_harness.tsv`.", ""]
    return "\n".join(L)


def package(version: str) -> pathlib.Path:
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    out = dist / f"arc22-manufacturing-{version}.zip"
    files = {
        "print": list((ROOT / "cad/out/print").rglob("*")),
        "step": list((ROOT / "cad/out/step").glob("*.step")),
        "fit_samples": list((ROOT / "cad/out/fit_samples").glob("*")),
        "hardware": [HW / "bom.csv", HW / "connections.csv", HW / "connectors.yml"]
        + list(HARNESS.glob("arc22_harness.*")),
        "docs": [DOCS / f for f in ("BUILD_GUIDE.md", "BOM.md", "CONNECTIONS.md", "WIRING.md", "SAFETY.md",
                                    "PRINTING.md", "MEASUREMENTS.md", "REQUIREMENTS.md", "VALIDATION.md",
                                    "FIRMWARE.md")],
        "docs/img": [DOCS / "img" / f for f in ("harness.png", "wiring_overview.png", "arc22_exploded.png", "arc22_assembly.png",
                                                "arc22_left_interior.png", "fit_samples.png")],
        "": [ROOT / f for f in ("LICENSE", "LICENSE-HARDWARE", "LICENSE-DOCS")],
    }
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for folder, paths in files.items():
            for p in paths:
                if p.is_file():
                    rel = p.relative_to(ROOT / "cad/out/print") if folder == "print" else pathlib.Path(p.name)
                    z.write(p, str(pathlib.PurePosixPath("arc22-manufacturing", folder, rel)))
        z.writestr("arc22-manufacturing/README.md", f"""# ARC-22 manufacturing package {version}

![Assembly](docs/img/arc22_assembly.png)

| Step | Open |
|---|---|
| 1. Measure your parts, then print the fit samples | `docs/BUILD_GUIDE.md` (stages 0-1), `docs/MEASUREMENTS.md`, `fit_samples/` |
| 2. Print the two shells, two colours each | `print/stl/ARC22_LEFT_WHITE.stl` + `ARC22_LEFT_BLUE.stl` as ONE object; same for RIGHT; `docs/PRINTING.md` |
| 3. Buy the parts | `hardware/bom.csv`, `docs/BOM.md` |
| 4. Make the harness | `hardware/connections.csv` (every wire, colour, gauge, length), `hardware/arc22_harness.svg`, `docs/CONNECTIONS.md` |
| 5. Assemble, commission, flash | `docs/BUILD_GUIDE.md` (stages 3-6), `docs/SAFETY.md`, `docs/FIRMWARE.md` |
| Edit the design | `step/` (any CAD tool) or the CadQuery source in the repository |

![Wiring](docs/img/wiring_overview.png)

Every ESP32-S3 pin is 3.3 V logic. Nothing in this package is physically validated yet:
see `docs/VALIDATION.md` and `docs/REQUIREMENTS.md`.

Hardware CERN-OHL-P-2.0 (LICENSE-HARDWARE), software MIT (LICENSE), documentation CC BY 4.0 (LICENSE-DOCS).
""")
        z.writestr("arc22-manufacturing/MANIFEST.json", json.dumps(dict(
            version=version, created=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            note="Print LEFT and RIGHT (two colours each), cut the harness from hardware/connections.csv, "
                 "follow docs/BUILD_GUIDE.md. Nothing here is physically validated yet: see docs/VALIDATION.md."),
            indent=2))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", action="store_true", help="also build dist/arc22-manufacturing-<version>.zip")
    ap.add_argument("--version", default="dev")
    ap.add_argument("--no-render", action="store_true", help="skip WireViz (checks + markdown only)")
    a = ap.parse_args()
    conns, wires, bom, pins = load()
    errs = check(conns, wires, pins)
    if errs:
        print("Manufacturing data check FAILED:")
        for e in errs:
            print("  -", e)
        return 1
    print(f"checks: {len(wires)} wires, {len(conns)} connectors, {len(pins)} firmware pins — consistent")
    if not a.no_render:
        render(harness_yaml(conns, wires))
        print("harness drawing → hardware/harness/, docs/img/harness.{svg,png}")
    wiring_overview(conns, wires, DOCS / "img" / "wiring_overview.png")
    print("docs/img/wiring_overview.png written")
    (DOCS / "CONNECTIONS.md").write_text(connections_md(conns, wires))
    (DOCS / "BOM.md").write_text(bom_md(bom))
    print("docs/CONNECTIONS.md, docs/BOM.md written")
    if a.package:
        print("package →", package(a.version).relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
