#!/usr/bin/env python3
"""
export_arc22.py — step 3 of the rebuild order.

Reads cad/build/*.brep (from build_arc22.py) and writes:

  cad/out/step/   ARC22_ASSEMBLY.step   both shells, WHITE + BLUE regions, assembly coordinates
                  ARC22_LEFT.step, ARC22_RIGHT.step        one shell each (editable)
  cad/out/print/  ARC22_LEFT.obj + ARC22_LEFT.mtl          keep each OBJ with its MTL
                  ARC22_RIGHT.obj + ARC22_RIGHT.mtl
                  stl/ARC22_{LEFT,RIGHT}_{WHITE,BLUE}.stl  four ALIGNED material regions
                  3mf/ARC22_{LEFT,RIGHT}_2COLOR.3mf        optional; NOT a validated Bambu project
                  PRINT_TRANSFORMS.json                    the one transform used per shell
  cad/reference_cad/  simplified modules, clearance fields, wire routes, topology (NOT printable)

Coordinate rule: STEP stays in ASSEMBLY coordinates. Printable meshes use ONE
shared transform per shell (exterior down, open seam up, centred on the P1S
bed). The WHITE and BLUE regions of a shell always get the identical matrix —
never move, drop or scale an accent region on its own.
"""
from __future__ import annotations

import json
import math
import pathlib
import sys
import zipfile

import cadquery as cq
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import arc22_geometry as G  # noqa: E402
import arc22_params as P  # noqa: E402

BUILD = HERE / "build"
OUT = HERE / "out"
REF = HERE / "reference_cad"
TOL, ANG = 0.05, 0.2  # mesh chord tolerance (mm) / angular tolerance (rad)

WHITE = (0.95, 0.96, 0.97)
BLUE = (0.10, 0.62, 0.86)
COLORS = {"WHITE": WHITE, "BLUE": BLUE}


def load(name):
    return cq.Shape.importBrep(str(BUILD / f"{name}.brep"))


def mesh(shape, tol=TOL, ang=ANG):
    verts, tris = shape.tessellate(tol, ang)
    v = np.array([(p.x, p.y, p.z) for p in verts], dtype=float)
    f = np.array(tris, dtype=np.int64).reshape(-1, 3)
    return v, f


def print_transform(side: str, bed: float) -> np.ndarray:
    """4x4: exterior down, open seam up, footprint centred on the bed."""
    if side == "LEFT":   # rotate +90° about X: (x, y, z) -> (x, -z, y)
        R = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], float)
    else:                # rotate -90° about X: (x, y, z) -> (x, z, -y)
        R = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], float)
    M = np.eye(4)
    M[:3, :3] = R
    return M


def finish_transform(M, verts_list, bed):
    allv = np.vstack([apply(M, v) for v in verts_list])
    mn, mx = allv.min(0), allv.max(0)
    T = np.eye(4)
    T[:3, 3] = [bed / 2 - (mn[0] + mx[0]) / 2, bed / 2 - (mn[1] + mx[1]) / 2, -mn[2]]
    return T @ M


def apply(M, v):
    return v @ M[:3, :3].T + M[:3, 3]


def write_stl(path, v, f):
    tri = v[f]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    ln = np.linalg.norm(n, axis=1, keepdims=True)
    n = np.divide(n, ln, out=np.zeros_like(n), where=ln > 0)
    data = np.zeros(len(f), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    data["n"], data["v"] = n, tri
    with open(path, "wb") as fh:
        fh.write(b"ARC22 binary STL".ljust(80, b" "))
        fh.write(np.uint32(len(f)).tobytes())
        fh.write(data.tobytes())


def write_obj(obj_path, mtl_path, parts):
    """parts: list of (group, material, v, f). One OBJ, one MTL, same folder."""
    with open(mtl_path, "w") as m:
        m.write("# ARC-22 materials — keep this file next to its OBJ\n")
        for name, rgb in COLORS.items():
            m.write(f"newmtl ARC22_{name}\nKd {rgb[0]:.3f} {rgb[1]:.3f} {rgb[2]:.3f}\n"
                    f"Ka 0 0 0\nKs 0.1 0.1 0.1\nNs 20\nd 1\nillum 2\n\n")
    off = 1
    with open(obj_path, "w") as o:
        o.write(f"# ARC-22 FitFirst shell — units mm — material regions share one transform\n"
                f"mtllib {mtl_path.name}\n")
        for group, mat, v, f in parts:
            o.write(f"o {group}\ng {group}\nusemtl ARC22_{mat}\n")
            o.write("".join(f"v {a:.4f} {b:.4f} {c:.4f}\n" for a, b, c in v))
            o.write("".join(f"f {i + off} {j + off} {k + off}\n" for i, j, k in f))
            off += len(v)


def write_3mf(path, parts, title):
    """Core-spec 3MF: one build object made of two mesh components (WHITE, BLUE)
    with a basematerials colour each. Import status in Bambu Studio is UNTESTED."""
    res = ['<basematerials id="1">']
    for name, rgb in COLORS.items():
        hexc = "#%02X%02X%02XFF" % tuple(int(c * 255) for c in rgb)
        res.append(f'<base name="ARC22_{name}" displaycolor="{hexc}"/>')
    res.append("</basematerials>")
    comps = []
    for i, (group, mat, v, f) in enumerate(parts):
        oid = i + 2
        pindex = list(COLORS).index(mat)
        vs = "".join(f'<vertex x="{a:.4f}" y="{b:.4f}" z="{c:.4f}"/>' for a, b, c in v)
        ts = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in f)
        res.append(f'<object id="{oid}" name="{group}" type="model" pid="1" pindex="{pindex}">'
                   f"<mesh><vertices>{vs}</vertices><triangles>{ts}</triangles></mesh></object>")
        comps.append(f'<component objectid="{oid}"/>')
    parent = len(parts) + 2
    res.append(f'<object id="{parent}" name="{title}" type="model"><components>{"".join(comps)}'
               "</components></object>")
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<model unit="millimeter" xml:lang="en-US" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
             f'<metadata name="Title">{title}</metadata>'
             '<metadata name="Designer">arc22-scanner (CadQuery)</metadata>'
             f'<resources>{"".join(res)}</resources>'
             f'<build><item objectid="{parent}"/></build></model>')
    ct = ('<?xml version="1.0" encoding="UTF-8"?>'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
          "</Types>")
    rels = ('<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)


def step_assembly(path, items):
    asm = cq.Assembly(name=path.stem)
    for name, shape, rgb in items:
        asm.add(shape, name=name, color=cq.Color(*rgb, 1.0))
    asm.save(str(path), exportType="STEP")


def main() -> int:
    p = P.load()
    man = json.loads((BUILD / "manifest.json").read_text())
    for d in (OUT / "step", OUT / "print" / "stl", OUT / "print" / "3mf", REF):
        d.mkdir(parents=True, exist_ok=True)

    regions = {k: load(k) for k in ("LEFT_WHITE", "LEFT_BLUE", "RIGHT_WHITE", "RIGHT_BLUE")}
    shells = {"LEFT": load("LEFT"), "RIGHT": load("RIGHT")}

    print("• STEP (assembly coordinates)")
    step_assembly(OUT / "step" / "ARC22_ASSEMBLY.step",
                  [(k, v, COLORS[k.split("_")[1]]) for k, v in regions.items()])
    for side in ("LEFT", "RIGHT"):
        cq.exporters.export(cq.Workplane().add(shells[side]), str(OUT / "step" / f"ARC22_{side}.step"))
        step_assembly(OUT / "step" / f"ARC22_{side}_2COLOR.step",
                      [(f"{side}_{m}", regions[f"{side}_{m}"], COLORS[m]) for m in ("WHITE", "BLUE")])

    print("• printable meshes (one shared transform per shell)")
    transforms = {}
    for side in ("LEFT", "RIGHT"):
        meshes = {m: mesh(regions[f"{side}_{m}"]) for m in ("WHITE", "BLUE")}
        M = finish_transform(print_transform(side, p.BED), [v for v, _ in meshes.values()], p.BED)
        transforms[side] = M.tolist()
        parts = []
        for m, (v, f) in meshes.items():
            vt = apply(M, v)
            write_stl(OUT / "print" / "stl" / f"ARC22_{side}_{m}.stl", vt, f)
            parts.append((f"ARC22_{side}_{m}", m, vt, f))
        write_obj(OUT / "print" / f"ARC22_{side}.obj", OUT / "print" / f"ARC22_{side}.mtl", parts)
        write_3mf(OUT / "print" / "3mf" / f"ARC22_{side}_2COLOR.3mf", parts, f"ARC22_{side}")
        allv = np.vstack([pp[2] for pp in parts])
        print(f"  {side}: print extents {np.ptp(allv, axis=0).round(1).tolist()} mm")
    (OUT / "print" / "PRINT_TRANSFORMS.json").write_text(json.dumps(dict(
        note="4x4 row-major; applied identically to WHITE and BLUE of the same shell. "
             "Assembly → print: exterior down, open seam up, centred on a 256 mm P1S bed.",
        transforms=transforms), indent=2))

    print("• reference CAD (not printable)")
    mods = G.modules(p)
    palette = {"display": (0.10, 0.12, 0.16), "camera": (0.15, 0.35, 0.20), "esp32": (0.10, 0.25, 0.45),
               "battery": (0.35, 0.35, 0.40), "charger": (0.45, 0.15, 0.40), "button": (0.75, 0.75, 0.75)}
    hard_items, field_items = [], []
    for name, m in mods.items():
        for k, s in m.hard.items():
            hard_items.append((f"{name}__{k}", s, palette[name]))
        for k, s in m.fields.items():
            field_items.append((f"{name}__{k}", s, (1.0, 0.6, 0.1)))
    step_assembly(REF / "ARC22_REFERENCE_MODULES.step", hard_items)
    step_assembly(REF / "ARC22_CLEARANCE_FIELDS.step", field_items)
    step_assembly(REF / "ARC22_WIRE_ROUTES.step",
                  [(k, load(f"route_{k}"), (0.95, 0.45, 0.1)) for k in man["routes"]])
    # topology: one sphere per node, one rod per connection
    centers = {}
    for name, m in mods.items():
        c = m.hard_all().BoundingBox().center
        centers[name] = (c.x, c.y, c.z)
    centers["run_pigtail"] = (40.0, -10.0, 70.0)
    topo = []
    for n, c in centers.items():
        topo.append((f"node_{n}", cq.Solid.makeSphere(5, cq.Vector(*c)), (0.9, 0.9, 0.2)))
    for a, b, label in man["topology"]:
        pa, pb = cq.Vector(*centers[a]), cq.Vector(*centers[b])
        d = pb - pa
        topo.append((f"link_{a}_{b}", cq.Solid.makeCylinder(1.5, d.Length, pa, d.normalized()),
                     (0.2, 0.2, 0.2)))
    step_assembly(REF / "ARC22_TOPOLOGY.step", topo)
    (REF / "topology.json").write_text(json.dumps(dict(
        nodes={k: [round(x, 1) for x in v] for k, v in centers.items()},
        links=[dict(a=a, b=b, signals=s) for a, b, s in man["topology"]]), indent=2))
    mesh_checks(regions)
    print("done →", OUT)
    return 0


def mesh_checks(regions) -> None:
    """RECORDED mesh checks on the files a slicer will actually load."""
    import trimesh
    rows = []
    for side in ("LEFT", "RIGHT"):
        for m in ("WHITE", "BLUE"):
            f = OUT / "print" / "stl" / f"ARC22_{side}_{m}.stl"
            tm = trimesh.load(f)
            tm.merge_vertices(digits_vertex=4)
            brep_v = G.vol(regions[f"{side}_{m}"])
            rows.append(dict(file=f.name, triangles=int(len(tm.faces)), watertight=bool(tm.is_watertight),
                             winding_consistent=bool(tm.is_winding_consistent), bodies=int(tm.body_count),
                             mesh_cm3=round(tm.volume / 1000, 2), brep_cm3=round(brep_v / 1000, 2),
                             volume_error_pct=round(abs(tm.volume - brep_v) / brep_v * 100, 3)))
    ok = all(r["watertight"] and r["winding_consistent"] and r["volume_error_pct"] < 1.0 for r in rows)
    out = HERE.parent / "docs" / "validation"
    out.mkdir(exist_ok=True)
    (out / "mesh_checks.json").write_text(json.dumps(dict(all_pass=ok, meshes=rows), indent=2))
    md = ["# Recorded mesh checks (auto-generated by `cad/export_arc22.py`)", "",
          "Checks on the exported STL regions. Watertight + consistent winding + volume matching the "
          "B-rep means the slicer receives closed solids. It says nothing about how Bambu Studio "
          "assigns filaments — that is a PHYSICAL/slicer check (docs/PRINTING.md).", "",
          "| File | Triangles | Watertight | Winding | Bodies | Mesh cm³ | B-rep cm³ | Δ % |",
          "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['file']} | {r['triangles']} | {r['watertight']} | {r['winding_consistent']} | "
                  f"{r['bodies']} | {r['mesh_cm3']} | {r['brep_cm3']} | {r['volume_error_pct']} |")
    (out / "mesh_checks.md").write_text("\n".join(md) + "\n")
    print("  mesh checks:", "PASS" if ok else "FAIL")


if __name__ == "__main__":
    raise SystemExit(main())
