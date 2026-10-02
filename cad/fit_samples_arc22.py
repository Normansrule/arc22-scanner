#!/usr/bin/env python3
"""
fit_samples_arc22.py — step 4 of the rebuild order.

Print these FIRST, at 100 % scale, before committing ~20 h of two-colour printing.
They are test pieces, never installed in the scanner.

  01_SCREEN_76x124_BEZEL_AND_PADS   rear wall + touch window + the four display corner slots
  02_CAMERA_46x50_LENS_AND_PADS     fairing nose + lens aperture + camera corner slots/tethers
  03_ESP32_WIRED_100x66x44_GAUGE    side-wall plate + ESP32 pads/clips/stops + an open frame
                                    outlining the reserved plugged-wire volume (44 mm tall)

Samples 01 and 02 are cut straight out of the real shells, so they carry exactly
the geometry that will be printed. Sample 03 checks the WIRED board: plug in
every jumper you will use and confirm the bundle bends inside the frame.
Output: cad/out/fit_samples/*.stl and *.step (flat on the bed, +Z up).
"""
from __future__ import annotations

import pathlib
import sys

import cadquery as cq
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import arc22_geometry as G  # noqa: E402
import arc22_params as P  # noqa: E402
from export_arc22 import mesh, write_stl  # noqa: E402

BUILD = HERE / "build"
OUT = HERE / "out" / "fit_samples"


def load(name):
    return cq.Shape.importBrep(str(BUILD / f"{name}.brep"))


def to_bed(shape, rot_axis=None, angle=0.0):
    s = shape
    if rot_axis is not None:
        s = s.rotate(cq.Vector(0, 0, 0), cq.Vector(*rot_axis), angle)
    b = s.BoundingBox()
    return s.translate(cq.Vector(-b.xmin, -b.ymin, -b.zmin))


def save(shape, name):
    OUT.mkdir(parents=True, exist_ok=True)
    cq.exporters.export(cq.Workplane().add(shape), str(OUT / f"{name}.step"))
    v, f = mesh(shape, 0.03, 0.15)
    write_stl(OUT / f"{name}.stl", v, f)
    b = shape.BoundingBox()
    print(f"  {name}: {b.xlen:.1f} × {b.ylen:.1f} × {b.zlen:.1f} mm, {len(shape.Solids())} solid(s)")


def main() -> int:
    p = P.load()
    both = load("LEFT").fuse(load("RIGHT"))
    g = p.FOAM_T + p.SLOT_EXTRA / 2

    # 01 — screen: 76 (Y) × 124 (Z), from the rear face to just behind the back jaws
    cz = p.DISP_CZ
    s1 = both.intersect(G.box(-1, p.DISP_PCB_BACK_X + g + p.JAW_T + 0.6, -38, 38, cz - 62, cz + 62))
    s1 = to_bed(s1, (0, 1, 0), -90)  # rear face (-X) down
    save(s1, "01_SCREEN_76x124_BEZEL_AND_PADS")

    # 02 — camera: 46 (Y) × 50 (Z) around the lens axis, cut behind the back jaws
    x_cut = p.CAM_PCB_BACK_X - g - p.JAW_T - 2.0
    s2 = both.intersect(G.box(x_cut, G.BIG, -23, 23, p.CAM_AXIS_Z - 25, p.CAM_AXIS_Z + 25))
    s2 = to_bed(s2, (0, 1, 0), -90)  # flat cut face down, nose up
    save(s2, "02_CAMERA_46x50_LENS_AND_PADS")

    # 03 — ESP32 wired gauge: 100 (X) × 66 (Z) plate + supports + 44 mm open frame
    wall_in = -p.INNER_SIDE_Y
    x0, x1 = p.ESP_CX - 50, p.ESP_CX + 50
    z0, z1 = p.ESP_CZ - 33, p.ESP_CZ + 33
    plate = G.box(x0, x1, wall_in - p.WALL, wall_in, z0, z1)
    sup = load("_features").intersect(G.box(x0, x1, wall_in - 0.5, 0, z0, z1))
    top = wall_in + 44.0
    posts = [G.box(x, x + sx * 4, wall_in - 0.1, top, z, z + sz * 4)
             for x, sx in ((x0, 1), (x1, -1)) for z, sz in ((z0, 1), (z1, -1))]
    rails = [G.box(x0, x1, top - 2.4, top, z0, z0 + 2.4), G.box(x0, x1, top - 2.4, top, z1 - 2.4, z1),
             G.box(x0, x0 + 2.4, top - 2.4, top, z0, z1), G.box(x1 - 2.4, x1, top - 2.4, top, z0, z1)]
    gauge = G.fuse([plate, sup] + posts + rails)
    # the frame must stay out of the reserved wire field and USB corridor
    esp_fields = G.fuse([load(f"mod_esp32__field__{k}") for k in
                         ("wires_near_lo", "wires_near_hi", "wires_bend", "prog_usb")])
    clash = G.inter_vol(gauge, esp_fields)
    print(f"  gauge frame ∩ reserved ESP32 fields: {clash:.2f} mm³ (must be 0)")
    try:
        label = (cq.Workplane("XZ", origin=(0, wall_in - p.WALL, 0)).center(x0 + 20, z0 + 6)
                 .text("ARC22 03", 5, -0.6, kind="bold").val())
        gauge = gauge.cut(label)
    except Exception:
        pass
    gauge = to_bed(gauge, (1, 0, 0), 90)  # plate (-Y) down
    save(gauge, "03_ESP32_WIRED_100x66x44_GAUGE")
    _ = np
    return 0 if clash <= 0.5 else 1


if __name__ == "__main__":
    raise SystemExit(main())
