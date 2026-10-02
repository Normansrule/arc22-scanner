#!/usr/bin/env python3
"""
build_arc22.py — step 1 of the rebuild order.

Builds the two printable shells (LEFT, RIGHT), their WHITE/BLUE material
regions, the reference modules (hard parts + reserved wire/air fields) and the
cable routes, all in ASSEMBLY coordinates, and caches them as BREP files in
cad/build/ for the next steps:

    build_arc22.py -> validate_arc22.py -> export_arc22.py
                   -> fit_samples_arc22.py -> render_arc22.py

Run:  python cad/build_arc22.py
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

import cadquery as cq

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import arc22_geometry as G  # noqa: E402
import arc22_params as P  # noqa: E402

BUILD = HERE / "build"


def save(shape, name: str) -> None:
    BUILD.mkdir(exist_ok=True)
    shape.exportBrep(str(BUILD / f"{name}.brep"))


def main() -> int:
    t0 = time.time()
    p = P.load()
    print(p.report())
    mods = G.modules(p)

    if BUILD.exists():
        for f in BUILD.glob("*.brep"):
            f.unlink()
    print("• outer skin / cavity")
    outer = G.body(p, 0.0, mouth_fillet=True)
    cav = G.body(p, -p.WALL)
    shell = outer.cut(cav)
    assert shell.isValid()

    print("• retention features")
    feats = []
    feats += G.display_slots(p)
    feats += G.camera_slots(p)
    esp_sup, esp_clips = G.esp32_supports(p)
    feats += esp_sup
    feats += G.battery_cradle(p, cav)
    feats += G.charger_slots(p)
    feat = G.fuse(feats).intersect(outer)

    print("• screws")
    bosses, screw_cuts, screw_table = G.screw_features(p, outer)
    boss = G.fuse(bosses)

    print("• openings, seam lip")
    ops = G.openings(p)
    op_all = G.fuse(list(ops.values()))
    lip, groove = G.seam_lip(p)

    cuts = G.fuse(screw_cuts)
    whole = shell.fuse(feat).fuse(boss).cut(cuts)
    left = whole.intersect(G.halfspace_y(-G.BIG, 0.0)).fuse(lip).cut(op_all).cut(cuts)
    right = whole.intersect(G.halfspace_y(0.0, G.BIG)).cut(groove).cut(op_all)
    for n, s in (("LEFT", left), ("RIGHT", right)):
        if not s.isValid():
            raise SystemExit(f"{n} shell is not a valid solid — stop and inspect the last change")

    print("• material regions (WHITE body / BLUE accents)")
    tool = G.accent_tool(p)
    regions = {
        "LEFT_WHITE": G.drop_slivers(left.cut(tool)),
        "LEFT_BLUE": G.drop_slivers(left.intersect(tool)),
        "RIGHT_WHITE": G.drop_slivers(right.cut(tool)),
        "RIGHT_BLUE": G.drop_slivers(right.intersect(tool)),
    }

    print("• caching BREP")
    save(left, "LEFT")
    save(right, "RIGHT")
    for k, v in regions.items():
        save(v, k)
    save(outer, "_outer")
    save(cav, "_cavity")
    save(feat, "_features")
    save(boss, "_bosses")
    save(G.fuse(esp_clips), "_esp_clip_hooks")
    save(lip, "_lip")
    save(tool, "_accent_tool")
    for k, v in ops.items():
        save(v, f"_open_{k}")
    for name, m in mods.items():
        for k, v in m.hard.items():
            save(v, f"mod_{name}__hard__{k}")
        for k, v in m.fields.items():
            save(v, f"mod_{name}__field__{k}")
    route_meta = {}
    for k, (pts, r) in G.routes(p).items():
        save(G.polyline_tube(pts, r), f"route_{k}")
        route_meta[k] = dict(points=pts, radius=r)

    manifest = dict(
        units="mm",
        coordinates="assembly: X front-back (0 = rear face), Y width (seam Y=0, LEFT<0), Z up",
        params={k: getattr(p, k) for k in list(P.MEASURED) + list(P.DESIGN)},
        unverified=p.unverified,
        screws=screw_table,
        routes=route_meta,
        topology=G.topology(),
        modules={n: dict(hard=list(m.hard), fields=list(m.fields), insert_shell=m.insert_shell,
                         insert_path=m.insert_path)
                 for n, m in mods.items()},
        solids={k: len(v.Solids()) for k, v in {"LEFT": left, "RIGHT": right, **regions}.items()},
        volumes_cm3={k: round(G.vol(v) / 1000, 2) for k, v in {"LEFT": left, "RIGHT": right,
                                                               **regions}.items()},
        bounds={k: [round(x, 2) for x in (b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax)]
                for k, b in {"LEFT": left.BoundingBox(), "RIGHT": right.BoundingBox()}.items()},
        build_seconds=round(time.time() - t0, 1),
        cadquery=cq.__version__,
    )
    (BUILD / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"done in {manifest['build_seconds']} s  → {BUILD}")
    print(json.dumps(manifest["solids"]), json.dumps(manifest["bounds"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
