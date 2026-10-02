#!/usr/bin/env python3
"""
build_web_data.py — step 6 of the rebuild order (after render_arc22.py).

Feeds ARC-22 Studio (the web app in docs/app/, also packaged as the desktop app)
from the same sources as everything else, so the app can never drift from the CAD
or the firmware:

  docs/app/models/*.stl      web meshes in ASSEMBLY coordinates (shell colour regions,
                             modules, reserved wire/air fields, cable routes)
  docs/app/models/index.json what each mesh is, its layer and colour
  docs/app/data/params.json  every measured/design value with its source + VERIFY state
  docs/app/data/pins.json    the pin map parsed from firmware/main/pins.h
  docs/app/data/checks.json  recorded CAD + mesh checks
  docs/app/data/build.json   manifest facts (bounds, screws, versions)

Run: python tools/build_web_data.py   (needs cad/build from build_arc22.py)
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "cad"))

import cadquery as cq  # noqa: E402
import numpy as np  # noqa: E402

import arc22_geometry as G  # noqa: E402
import arc22_params as P  # noqa: E402

BUILD = ROOT / "cad" / "build"
APP = ROOT / "docs" / "app"
MODELS = APP / "models"
DATA = APP / "data"
TOL, ANG = 0.12, 0.25

GROUPS = {  # key in manifest -> (label, layer)
    "display": ("Display + touch (ST7796S / XPT2046)", "modules"),
    "camera": ("Camera (Arducam Mini OV2640)", "modules"),
    "esp32": ("ESP32-S3-N16R8", "modules"),
    "battery": ("Battery 1S 4400 mAh", "modules"),
    "charger": ("Charger + 5 V boost (#6106)", "modules"),
    "button": ("Latching power button", "modules"),
}
MOD_COLOURS = {"display": "#20262e", "camera": "#2c7a4b", "esp32": "#244f8c", "battery": "#6b6f7a",
               "charger": "#86357a", "button": "#b8bec6"}


def load(name):
    return cq.Shape.importBrep(str(BUILD / f"{name}.brep"))


def write_stl(path, shape, tol=TOL, ang=ANG):
    v, f = shape.tessellate(tol, ang)
    V = np.array([(p.x, p.y, p.z) for p in v], np.float32)
    F = np.array(f, np.int64).reshape(-1, 3)
    tri = V[F]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    ln = np.linalg.norm(n, axis=1, keepdims=True)
    n = np.divide(n, ln, out=np.zeros_like(n), where=ln > 0)
    rec = np.zeros(len(F), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    rec["n"], rec["v"] = n, tri
    with open(path, "wb") as fh:
        fh.write(b"ARC22 web mesh, assembly coordinates, mm".ljust(80, b" "))
        fh.write(np.uint32(len(F)).tobytes())
        fh.write(rec.tobytes())
    return len(F)


def meshes(man) -> list[dict]:
    MODELS.mkdir(parents=True, exist_ok=True)
    for old in MODELS.glob("*.stl"):
        old.unlink()
    out = []
    for side in ("LEFT", "RIGHT"):
        for mat, col in (("WHITE", "#eef2f4"), ("BLUE", "#1a9fdb")):
            fn = f"{side}_{mat}.stl"
            tris = write_stl(MODELS / fn, load(f"{side}_{mat}"))
            out.append(dict(file=fn, layer="shells", side=side, label=f"{side.title()} shell, {mat.lower()}",
                            colour=col, triangles=tris))
    for mod, info in man["modules"].items():
        hard = G.fuse([load(f"mod_{mod}__hard__{k}") for k in info["hard"]])
        fn = f"mod_{mod}.stl"
        out.append(dict(file=fn, layer="modules", module=mod, label=GROUPS[mod][0], colour=MOD_COLOURS[mod],
                        triangles=write_stl(MODELS / fn, hard)))
        flds = G.fuse([load(f"mod_{mod}__field__{k}") for k in info["fields"]])
        if flds is not None:
            fn = f"field_{mod}.stl"
            out.append(dict(file=fn, layer="fields", module=mod, label=f"Reserved space: {mod}",
                            colour="#e39b2d", triangles=write_stl(MODELS / fn, flds)))
    routes = G.fuse([load(f"route_{k}") for k in man["routes"]])
    out.append(dict(file="routes.stl", layer="routes", label="Cable routes", colour="#d8662a",
                    triangles=write_stl(MODELS / "routes.stl", routes, 0.5, 0.5)))
    (MODELS / "index.json").write_text(json.dumps(dict(units="mm", coordinates=man["coordinates"],
                                                       meshes=out), indent=1))
    return out


LABELS = {
    "DISP_PCB_W": "Display PCB width (short side)", "DISP_PCB_H": "Display PCB height (long side)",
    "DISP_PCB_T": "Display PCB thickness", "DISP_ACTIVE_W": "Lit area width", "DISP_ACTIVE_H": "Lit area height",
    "DISP_ACTIVE_OFF_Z": "Lit area offset along the long side", "DISP_ACTIVE_OFF_Y": "Lit area offset across",
    "DISP_GLASS_W": "Glass width", "DISP_GLASS_H": "Glass height",
    "DISP_GLASS_OFF_Z": "Glass offset along the long side", "DISP_GLASS_STACK": "PCB front to glass front",
    "DISP_BACK_POP": "Tallest part on the back (not the header)", "DISP_HDR_SPACER": "Header spacer height",
    "DISP_HDR_PINS": "Header pin count", "DISP_HDR_INSET": "Header row to PCB edge",
    "DISP_BARE_SIDE": "Bare strip at the long edges", "DISP_BARE_END_HDR": "Bare length at the header end",
    "DISP_BARE_END_FAR": "Bare length at the far end",
    "CAM_PCB_W": "Camera PCB width", "CAM_PCB_H": "Camera PCB height", "CAM_PCB_T": "Camera PCB thickness",
    "CAM_HOLDER_SQ": "Lens holder base", "CAM_LENS_D": "Lens barrel diameter", "CAM_LENS_PROJ": "PCB front to lens front",
    "CAM_OPT_OFF_Z": "Lens centre offset (vertical)", "CAM_OPT_OFF_Y": "Lens centre offset (sideways)",
    "CAM_BACK_POP": "Tallest part on the back", "CAM_HDR_INSET": "Header row to bottom edge",
    "CAM_BARE_CORNER": "Bare square at each corner", "CAM_HDR_PINS": "Header pin count",
    "ESP_L": "Board length", "ESP_W": "Board width", "ESP_T": "PCB thickness",
    "ESP_TOP_POP": "Tallest part on the top side", "ESP_HDR_LEN": "Header row length",
    "ESP_HDR_SPACER": "Header spacer height", "ESP_USB_PROJ": "USB-C overhang past the PCB end",
    "ESP_BARE_CORNER": "Bare corner square", "ESP_HDR_OFF_X": "Header row offset along the board",
    "ESP_USB_HALF_SPAN": "Half the span across the USB-C port(s)",
    "USB_PLUG_T": "Programming cable plug thickness", "USB_PLUG_W": "Programming cable plug width",
    "DUPONT_HOUSING_L": "Dupont housing length on the pin", "DUPONT_HOUSING_W": "Dupont housing width",
    "WIRE_STRAIGHT_EXIT": "Straight wire before it can bend", "WIRE_BEND_R": "First relaxed bend radius",
    "WIRE_STRAIN": "Strain-relief allowance",
    "BAT_L": "Battery length", "BAT_W": "Battery width", "BAT_T": "Battery thickness",
    "CHG_L": "Charger length (USB-C axis)", "CHG_W": "Charger width", "CHG_H": "Charger height incl. parts",
    "CHG_USB_OFF_Y": "USB-C offset from charger centre", "CHG_BARE_CORNER": "Bare square at the front corners",
    "BTN_HOLE_D": "Panel hole diameter", "BTN_BODY_D": "Widest body or nut", "BTN_DEPTH": "Depth incl. terminals",
    "M2_HEAD_D": "M2 screw head diameter", "FOAM_T": "Foam pad thickness",
}


def params() -> dict:
    p = P.load()
    groups = [("DISP_", "Display"), ("CAM_", "Camera"), ("ESP_", "ESP32-S3 board"), ("DUPONT_", "Wiring"),
              ("WIRE_", "Wiring"), ("USB_PLUG", "Wiring"), ("BAT_", "Battery"), ("CHG_", "Charger"),
              ("BTN_", "Button"), ("M2_", "Hardware"), ("FOAM_", "Hardware")]
    rows = []
    for k, (nominal, src) in P.MEASURED.items():
        g = next((name for pre, name in groups if k.startswith(pre)), "Other")
        rows.append(dict(key=k, group=g, label=LABELS.get(k, k), nominal=nominal, current=getattr(p, k),
                         source=(src.split(":", 1)[-1].strip() if ":" in src else
                                 ("measure on your part" if src.upper().startswith("VERIFY") else src)),
                         verify=k in p.unverified))
    return dict(measured=rows, design={k: getattr(p, k) for k in P.DESIGN},
                unverified=len(p.unverified), total=len(P.MEASURED))


def pins() -> list[dict]:
    rows = []
    for m in re.finditer(r"#define\s+(PIN_\w+)\s+(\d+)\s*(?://\s*(.*))?",
                         (ROOT / "firmware" / "main" / "pins.h").read_text()):
        rows.append(dict(name=m.group(1), gpio=int(m.group(2)), note=(m.group(3) or "").strip()))
    return rows


def main() -> int:
    man = json.loads((BUILD / "manifest.json").read_text())
    DATA.mkdir(parents=True, exist_ok=True)
    ms = meshes(man)
    (DATA / "params.json").write_text(json.dumps(params(), indent=1))
    (DATA / "pins.json").write_text(json.dumps(pins(), indent=1))
    val = ROOT / "docs" / "validation"
    checks = {}
    for name in ("cad_checks", "mesh_checks"):
        f = val / f"{name}.json"
        checks[name] = json.loads(f.read_text()) if f.exists() else None
    (DATA / "checks.json").write_text(json.dumps(checks, indent=1))
    pinned = json.loads((ROOT / "firmware" / "PINNED_VERSIONS.json").read_text())
    (DATA / "build.json").write_text(json.dumps(dict(
        bounds=man["bounds"], screws=man["screws"], volumes_cm3=man["volumes_cm3"],
        topology=man["topology"], cadquery=man["cadquery"], firmware=pinned), indent=1))
    size = sum(f.stat().st_size for f in MODELS.glob("*.stl")) / 1e6
    print(f"web data: {len(ms)} meshes ({size:.1f} MB), {len(pins())} pins → {APP.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
