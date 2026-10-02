#!/usr/bin/env python3
"""
validate_arc22.py — step 2 of the rebuild order.

RECORDED CAD checks only. A PASS here means "the model agrees with itself and
with the numbers in arc22_params.py". It does NOT prove physical fit: every
VERIFY measurement is a guess until you measure your parts (docs/MEASUREMENTS.md)
and print the fit samples (docs/BUILD_GUIDE.md, stages 0-2).

Checks
  1. envelope, bed fit on a Bambu Lab P1S, one solid per shell
  2. hard parts (PCB, glass, lens, parts, headers, PLUGGED Dupont housings) vs shells
  3. reserved fields (wire exit + bend + strain relief, open backs, USB plug) vs shells
  4. INSERTION path: each module's hard parts swept along +Y (lay-in) vs its shell
  5. CLOSING swept volume: everything installed swept along -Y vs the RIGHT shell
  6. cable routes lie inside the cavity and miss every hard part
  7. hand loop never exposes the cavity; screws never clamp a module
  8. WHITE + BLUE regions exactly rebuild each shell (aligned, no overlap)
Writes docs/validation/cad_checks.json and docs/validation/cad_checks.md
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

import cadquery as cq
from OCP.BRepExtrema import BRepExtrema_DistShapeShape

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import arc22_geometry as G  # noqa: E402
import arc22_params as P  # noqa: E402

BUILD = HERE / "build"
OUT = HERE.parent / "docs" / "validation"
TOL = 0.5  # mm^3 of numerical noise tolerated in an intersection
SWEEP = 80.0


def load(name):
    return cq.Shape.importBrep(str(BUILD / f"{name}.brep"))


STEP = 1.0  # mm; thinner than any printed wall, rib or jaw (>= 1.2 mm)


def path_check(moving, target, path, step=STEP, skip_seated=True):
    """Move `moving` (modelled at its seated position) along the waypoint
    offsets in `path` (far -> seated) in `step` increments; return the worst
    intersection with `target` and the offset where it happened."""
    import numpy as np
    pts = []
    for a, b in zip(path[:-1], path[1:]):
        a, b = np.array(a, float), np.array(b, float)
        n = max(1, int(np.ceil(np.linalg.norm(b - a) / step)))
        pts += [a + (b - a) * i / n for i in range(n)]
    if not skip_seated:
        pts.append(np.array(path[-1], float))
    mb = moving.BoundingBox()
    P_ = np.array(pts)
    lo, hi = P_.min(0), P_.max(0)
    region = G.box(mb.xmin + lo[0] - 1, mb.xmax + hi[0] + 1, mb.ymin + lo[1] - 1, mb.ymax + hi[1] + 1,
                   mb.zmin + lo[2] - 1, mb.zmax + hi[2] + 1)
    tgt = target.intersect(region)
    if G.vol(tgt) <= 0:
        return 0.0, None
    worst, where = 0.0, None
    for o in pts:
        v = G.inter_vol(moving.translate(cq.Vector(*o)), tgt)
        if v > worst:
            worst, where = v, tuple(round(x, 1) for x in o)
    return worst, where


def sweep_check(moving, target, dy, step=STEP):
    return path_check(moving, target, [(0, dy, 0), (0, 0, 0)], step)


def mindist(a, b) -> float:
    d = BRepExtrema_DistShapeShape(a.wrapped, b.wrapped)
    d.Perform()
    return d.Value() if d.IsDone() else float("nan")


def main() -> int:
    t0 = time.time()
    p = P.load()
    man = json.loads((BUILD / "manifest.json").read_text())
    L, R = load("LEFT"), load("RIGHT")
    shells = {"LEFT": L, "RIGHT": R}
    both = L.fuse(R)
    rows: list[dict] = []

    def rec(group, item, ok, value="", note=""):
        rows.append(dict(group=group, item=item, result="PASS" if ok is True else
                         ("FAIL" if ok is False else str(ok)), value=value, note=note))

    # 1 ------------------------------------------------------------------
    bb = both.BoundingBox()
    size = (bb.xlen, bb.ylen, bb.zlen)
    rec("envelope", "bounds X×Y×Z (front-back × width × height)",
        all(s <= t + 0.6 for s, t in zip(size, (p.BODY_X, p.BODY_Y + p.LIP_H, p.BODY_Z))),
        f"{size[0]:.1f} × {size[1]:.1f} × {size[2]:.1f} mm", "ARC22 target ~218 × 118 × 218")
    for n, s in shells.items():
        b = s.BoundingBox()
        foot = max(b.xlen, b.zlen)
        h = b.ylen
        rec("envelope", f"{n} one solid, valid", len(s.Solids()) == 1 and s.isValid(),
            f"{len(s.Solids())} solid(s)")
        rec("printer", f"{n} on P1S bed (exterior down)",
            foot <= p.BED - 2 * p.BED_MARGIN and h <= p.BED,
            f"footprint {b.xlen:.1f} × {b.zlen:.1f}, height {h:.1f} mm",
            f"bed {p.BED:.0f}³ minus {p.BED_MARGIN:.0f} mm margin for brim/purge/exclusions")

    # 2 / 3 --------------------------------------------------------------
    hard, fields = {}, {}
    for f in sorted(BUILD.glob("mod_*.brep")):
        mod, kind, part = f.stem[4:].split("__")
        (hard if kind == "hard" else fields).setdefault(mod, {})[part] = cq.Shape.importBrep(str(f))
    for mod, parts in hard.items():
        for part, s in parts.items():
            v = G.inter_vol(s, both)
            rec("hard parts vs shells", f"{mod}.{part}", v <= TOL, f"{v:.2f} mm³")
    for mod, parts in fields.items():
        for part, s in parts.items():
            v = G.inter_vol(s, both)
            rec("reserved fields vs shells", f"{mod}.{part}", v <= TOL, f"{v:.2f} mm³",
                "wire/air space stays free of plastic")
    # module-to-module: hard of one vs hard+fields of another
    names = list(hard)
    for i, a in enumerate(names):
        ha = G.fuse(list(hard[a].values()))
        for b in names[i + 1:]:
            hb = G.fuse(list(hard[b].values()))
            fb = G.fuse(list(fields.get(b, {}).values()))
            fa = G.fuse(list(fields.get(a, {}).values()))
            v = G.inter_vol(ha, hb) + G.inter_vol(ha, fb) + G.inter_vol(hb, fa)
            rec("module-to-module room", f"{a} ↔ {b}", v <= TOL, f"{v:.2f} mm³",
                "hard parts never sit in another module's wire field")

    # 4 insertion --------------------------------------------------------
    clips = load("_esp_clip_hooks")
    L_noclip = L.cut(clips)
    for mod, parts in hard.items():
        H = G.fuse(list(parts.values()))
        path = man["modules"][mod]["insert_path"]
        v, where = path_check(H, L_noclip, path)
        desc = " → ".join(f"({a:+.0f},{b:+.0f},{c:+.0f})" for a, b, c in path)
        note = f"path {desc} mm into the LEFT shell (plugs fitted), checked every 1 mm"
        if mod == "esp32":
            snap, _ = path_check(H, clips, path)
            note += f"; snap clips engage up to {snap:.1f} mm³ (intended, hook {p.CLIP_HOOK} mm)"
        val = f"{v:.2f} mm³" + (f" at offset {where}" if where else "")
        rec("insertion path (swept)", mod, v <= TOL, val, note)

    # 5 closing ----------------------------------------------------------
    installed = []
    for mod in hard:
        installed += list(hard[mod].values()) + list(fields.get(mod, {}).values())
    for k in man["routes"]:
        installed.append(load(f"route_{k}"))
    I = G.fuse(installed)
    R_body = R.cut(G.halfspace_y(-1, p.LIP_H + p.LIP_CLEAR + 0.01))  # groove zone meets the lip
    v, where = path_check(R_body, I, [(0, SWEEP, 0), (0, 0, 0)])
    rec("closing swept volume", "RIGHT shell descending onto fully wired LEFT half", v <= TOL,
        f"{v:.2f} mm³" + (f" at {where[1]:.0f} mm above seat" if where else ""),
        "includes plugged housings, wire fields and cable routes; checked every 1 mm")
    v = G.inter_vol(I, R)
    rec("closing swept volume", "RIGHT shell at final position vs installed stack", v <= TOL,
        f"{v:.2f} mm³", "halves meet with no module pressure → close by hand before screws")

    # 6 routes -----------------------------------------------------------
    H_all = G.fuse([s for parts in hard.values() for s in parts.values()])
    for k in man["routes"]:
        r = load(f"route_{k}")
        v1 = G.inter_vol(r, both)
        v2 = G.inter_vol(r, H_all)
        rec("cable routes", f"{k} inside cavity", v1 <= TOL, f"{v1:.2f} mm³ plastic")
        rec("cable routes", f"{k} clear of hard parts", v2 <= 50.0, f"{v2:.1f} mm³",
            "ends touch the header/plug zone by design (≤ 50 mm³ allowed)")

    # 7 loop / screws ----------------------------------------------------
    cav = load("_cavity")
    loop_space = G.loop_cut_profile(p, 0).extrude(G.BIG / 2, both=True).val().intersect(
        G.box(-G.BIG, G.BIG, -G.BIG, G.BIG, p.LOOP_Z0, G.BIG))
    v = G.inter_vol(loop_space, cav)
    rec("hand loop", "loop opening never reaches the electronics cavity", v <= TOL, f"{v:.2f} mm³",
        f"loop wall {p.WALL} mm all round")
    for s in man["screws"]:
        col = G.cyl_y(s["x"], s["z"], p.BOSS_D / 2, -G.BIG / 2, G.BIG / 2)
        d = min(mindist(col, h) for h in [H_all])
        rec("screws", f"{s['name']} boss clear of every module", d > 1.0, f"{d:.1f} mm gap",
            "screws clamp shell to shell only — never a module")
        rec("screws", f"{s['name']} pilot stays blind (left skin ≥ 1.0 mm)", s["left_skin"] >= 1.0,
            f"skin {s['left_skin']} mm, M2×{s['length']:.0f}, engagement {s['engagement']:.0f} mm, "
            f"well {s['well_depth']} mm deep")

    # 8 material regions ------------------------------------------------
    for n in ("LEFT", "RIGHT"):
        w, b = load(f"{n}_WHITE"), load(f"{n}_BLUE")
        vs, vw, vb = G.vol(shells[n]), G.vol(w), G.vol(b)
        ov = G.inter_vol(w, b)
        err = abs(vw + vb - vs) / vs * 100
        rec("two-colour regions", f"{n}: WHITE + BLUE = shell, no overlap", err < 0.2 and ov <= TOL,
            f"white {vw/1000:.1f} cm³, blue {vb/1000:.1f} cm³, Δ {err:.3f} %, overlap {ov:.2f} mm³",
            "same assembly coordinates → identical per-shell print transform")

    OUT.mkdir(exist_ok=True)
    fails = [r for r in rows if r["result"] == "FAIL"]
    summary = dict(total=len(rows), passed=sum(r["result"] == "PASS" for r in rows), failed=len(fails),
                   unverified_measurements=len(p.unverified), seconds=round(time.time() - t0, 1))
    (OUT / "cad_checks.json").write_text(json.dumps(dict(summary=summary, checks=rows), indent=2))
    md = ["# Recorded CAD checks (auto-generated by `cad/validate_arc22.py`)", "",
          "These are **RECORDED CAD/mesh checks**, not physical tests. "
          f"{len(p.unverified)} measurements are still marked VERIFY, so a PASS means the model is "
          "self-consistent with nominal numbers — nothing more.", "",
          f"**{summary['passed']} / {summary['total']} passed, {summary['failed']} failed.**", "",
          "| Group | Item | Result | Value | Note |", "|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['group']} | {r['item']} | {r['result']} | {r['value']} | {r['note']} |")
    (OUT / "cad_checks.md").write_text("\n".join(md) + "\n")
    print(f"{summary['passed']}/{summary['total']} passed, {summary['failed']} failed "
          f"({summary['seconds']} s)")
    for r in fails:
        print("  FAIL", r["group"], "|", r["item"], "|", r["value"])
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
