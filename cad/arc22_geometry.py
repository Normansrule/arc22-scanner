"""
ARC-22 geometry library (CadQuery). Imported by build_arc22.py and the other
scripts; it never writes files itself.

Everything is built in ASSEMBLY coordinates (see arc22_params.py). Every module
is modelled as:
  hard   - things that physically exist (PCB, glass, lens, parts, header,
           the plugged-in Dupont housings)           -> nothing may intersect
  field  - reserved air for wires/strain relief/open backs/USB plug
                                                     -> no shell material allowed
  bare   - the ONLY zones where printed supports may touch the part
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import cadquery as cq

V = cq.Vector
PXZ = cq.Plane(origin=(0, 0, 0), xDir=(1, 0, 0), normal=(0, -1, 0))  # local (x,y) = (X,Z)
BIG = 400.0


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
def box(x0, x1, y0, y1, z0, z1) -> cq.Shape:
    x0, x1 = sorted((x0, x1))
    y0, y1 = sorted((y0, y1))
    z0, z1 = sorted((z0, z1))
    return cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def cyl_x(y, z, r, x0, x1) -> cq.Shape:
    return cq.Solid.makeCylinder(r, x1 - x0, V(x0, y, z), V(1, 0, 0))


def cyl_y(x, z, r, y0, y1) -> cq.Shape:
    y0, y1 = sorted((y0, y1))
    return cq.Solid.makeCylinder(r, y1 - y0, V(x, y0, z), V(0, 1, 0))


def fuse(shapes) -> cq.Shape | None:
    shapes = [s for s in shapes if s is not None]
    if not shapes:
        return None
    out = shapes[0]
    if len(shapes) > 1:
        out = out.fuse(*shapes[1:])
    return safe_clean(out)


def safe_clean(shape):
    """clean() merges coplanar faces but can break validity on complex booleans."""
    try:
        c = shape.clean()
        if c.isValid():
            return c
    except Exception:
        pass
    return shape


def drop_slivers(shape, min_vol=2.0):
    """Remove tiny solids left by boolean round-off at region boundaries."""
    keep = [s for s in shape.Solids() if s.Volume() >= min_vol]
    if not keep:
        return shape
    return keep[0] if len(keep) == 1 else cq.Compound.makeCompound(keep)


def vol(shape) -> float:
    if shape is None:
        return 0.0
    try:
        return abs(shape.Volume())
    except Exception:
        return 0.0


def inter_vol(a, b) -> float:
    if a is None or b is None:
        return 0.0
    ba, bb = a.BoundingBox(), b.BoundingBox()
    if (ba.xmax < bb.xmin or bb.xmax < ba.xmin or ba.ymax < bb.ymin or bb.ymax < ba.ymin
            or ba.zmax < bb.zmin or bb.zmax < ba.zmin):
        return 0.0
    return vol(a.intersect(b))


def halfspace_y(lo, hi) -> cq.Shape:
    return box(-BIG, BIG, lo, hi, -BIG, BIG)


def polyline_tube(points, r) -> cq.Shape:
    """Chain of cylinders + spheres: a reserved cable corridor."""
    parts = []
    for a, b in zip(points[:-1], points[1:]):
        a, b = V(*a), V(*b)
        d = b - a
        parts.append(cq.Solid.makeCylinder(r, d.Length, a, d.normalized()))
    for p in points:
        parts.append(cq.Solid.makeSphere(r, V(*p), angleDegrees1=-90, angleDegrees2=90))
    return fuse(parts)


# ---------------------------------------------------------------------------
# outer form
# ---------------------------------------------------------------------------
def d_profile(p, d=0.0) -> cq.Workplane:
    """Side silhouette: straight rear, straight top/bottom, elliptical front bow."""
    r = p.REAR_CORNER_R
    xb, L, H = p.BOW_START_X, p.BODY_X, p.BODY_Z
    a, b = L - xb, H / 2
    k = r * (1 - math.cos(math.pi / 4))
    w = (cq.Workplane(PXZ).moveTo(r, 0).lineTo(xb, 0)
         .ellipseArc(a, b, -90, 90, startAtCurrent=True)
         .lineTo(r, H).threePointArc((k, H - k), (0, H - r))
         .lineTo(0, r).threePointArc((k, k), (r, 0)).close())
    if abs(d) > 1e-9:
        w = w.offset2D(d, "arc")
    return w


def loop_cut_profile(p, g=0.0) -> cq.Workplane:
    """Hand-loop opening in the side view, open downward (the grip bar is added after)."""
    x0, x1, z1, r = p.LOOP_X0, p.LOOP_X1, p.LOOP_Z1, p.LOOP_CORNER_R
    k = r * (1 - math.cos(math.pi / 4))
    w = (cq.Workplane(PXZ).moveTo(x0, -60).lineTo(x0, z1 - r)
         .threePointArc((x0 + k, z1 - k), (x0 + r, z1)).lineTo(x1 - r, z1)
         .threePointArc((x1 - k, z1 - k), (x1, z1 - r)).lineTo(x1, -60).close())
    if abs(g) > 1e-9:
        w = w.offset2D(g, "arc")
    return w


def _mouth_fillet(solid: cq.Shape, p) -> cq.Shape:
    """Round the hand-loop mouths on the outer skin (skipped if OCC refuses)."""
    edges = []
    for f in solid.Faces():
        c = f.Center()
        if not (p.LOOP_X0 - 1 < c.x < p.LOOP_X1 + 1 and c.z < p.LOOP_Z1 + 1):
            continue
        if abs(f.normalAt(c).y) > 0.3:
            continue
        for e in f.Edges():
            if abs(e.tangentAt(0.5).y) < 0.9:
                mid = e.positionAt(0.5)
                if abs(mid.y) > p.GRIP_HALF_W + 2:
                    edges.append(e)
    for r in (p.LOOP_EDGE_R, p.LOOP_EDGE_R * 0.75, p.LOOP_EDGE_R * 0.5):
        try:
            out = solid.fillet(r, edges)
            if out.isValid():
                return out
        except Exception:
            pass
    return solid


def body(p, d=0.0, mouth_fillet=False) -> cq.Shape:
    """Solid enclosed by the skin offset by d (d=0 outer, d=-WALL cavity)."""
    upper = d_profile(p, d).extrude(p.BODY_Y / 2 + d, both=True)
    upper = upper.edges("not |Y").fillet(p.SIDE_FILLET_R + d).val()
    upper = upper.cut(loop_cut_profile(p, -d).extrude(BIG / 2, both=True).val())
    if mouth_fillet:
        upper = _mouth_fillet(upper, p)
    # grip bar: rounded cross-section, runs GRIP_OVERLAP into each leg
    gw, gr = p.GRIP_HALF_W + d, p.GRIP_R + d
    z0, z1 = -d, p.LOOP_Z0 + d
    bar = (cq.Workplane("YZ", origin=(p.LOOP_X0 - p.GRIP_OVERLAP, 0, 0))
           .center(0, (z0 + z1) / 2).rect(2 * gw, z1 - z0).extrude(
               p.LOOP_X1 - p.LOOP_X0 + 2 * p.GRIP_OVERLAP)
           .edges("|X").fillet(gr).val())
    # the bar ends inside the legs; trim it to the silhouette so it never pokes out under the bow
    bar = bar.intersect(d_profile(p, d).extrude(BIG / 2, both=True).val())
    # integrated camera fairing (nose on the upper bow)
    fr = p.FAIR_R + d
    fair = (cq.Workplane("YZ", origin=(p.FAIR_X0, 0, p.CAM_AXIS_Z)).circle(fr)
            .extrude(p.FAIR_FRONT_X + d - p.FAIR_X0)
            .faces(">X").edges().fillet(p.FAIR_FRONT_FILLET + d).val())
    return upper.fuse(bar, fair).clean()


# ---------------------------------------------------------------------------
# modules
# ---------------------------------------------------------------------------
@dataclass
class Module:
    name: str
    hard: dict = field(default_factory=dict)
    fields: dict = field(default_factory=dict)
    bare: dict = field(default_factory=dict)
    insert_shell: str = "LEFT"  # installed into this shell first
    # waypoints (offsets from the seated position), far -> seated; default: lowered along -Y
    insert_path: list = field(default_factory=lambda: [(0.0, 80.0, 0.0), (0.0, 0.0, 0.0)])

    def hard_all(self):
        return fuse(list(self.hard.values()))

    def field_all(self):
        return fuse(list(self.fields.values()))


def display(p) -> Module:
    m = Module("display")
    W, H = p.DISP_PCB_W, p.DISP_PCB_H
    z0, z1, cz = p.DISP_Z0, p.DISP_Z1, p.DISP_CZ
    pf, pb = p.DISP_PCB_FRONT_X, p.DISP_PCB_BACK_X
    m.hard["pcb"] = box(pf, pb, -W / 2, W / 2, z0, z1)
    gz = cz + p.DISP_GLASS_OFF_Z
    m.hard["glass"] = box(p.DISP_GLASS_FRONT_X, pf, -p.DISP_GLASS_W / 2, p.DISP_GLASS_W / 2,
                          gz - p.DISP_GLASS_H / 2, gz + p.DISP_GLASS_H / 2)
    m.hard["back_parts"] = box(pb, pb + p.DISP_BACK_POP, -W / 2 + p.DISP_BARE_SIDE,
                               W / 2 - p.DISP_BARE_SIDE, z0 + p.DISP_BARE_END_HDR,
                               z1 - p.DISP_BARE_END_FAR)
    hz = z0 + p.DISP_HDR_INSET
    hl = p.DISP_HDR_PINS * 2.54
    m.hard["header"] = box(pb, pb + p.DISP_HDR_SPACER + 6.0, -hl / 2, hl / 2, hz - 1.27, hz + 1.27)
    m.hard["plugs"] = box(pb + p.DISP_HDR_SPACER, pb + p.PLUG_DEPTH, -hl / 2 - 0.3, hl / 2 + 0.3,
                          hz - p.DUPONT_HOUSING_W / 2, hz + p.DUPONT_HOUSING_W / 2)
    # reserved wire volume behind the header: exit + relaxed bend + strain relief
    near = p.PLUG_DEPTH + p.WIRE_STRAIGHT_EXIT
    m.fields["hdr_wires_near"] = box(pb + p.DISP_HDR_SPACER, pb + near, -hl / 2 - 2, hl / 2 + 2,
                                     z0 - 1.0, hz + 4.0)
    m.fields["hdr_wires_bend"] = box(pb + near, pb + p.WIRE_FIELD, -hl / 2 - p.WIRE_BEND_R,
                                     hl / 2 + p.WIRE_BEND_R, z0 - 2.0, hz + p.WIRE_BEND_R + 8.0)
    # possible pins at the far (SD) end
    m.fields["far_pins"] = box(pb, pb + 0.6 * p.WIRE_FIELD, -14, 14, z1 - 12, z1)
    # open back: air behind the whole PCB
    m.fields["open_back"] = box(pb, pb + p.DISP_BACK_POP + 1.5, -W / 2 + p.DISP_BARE_SIDE,
                                W / 2 - p.DISP_BARE_SIDE, z0 + p.DISP_BARE_END_HDR,
                                z1 - p.DISP_BARE_END_FAR)
    # keep-out air in front of the glass (nothing touches glass)
    m.fields["glass_air"] = box(p.WALL, pf, -p.DISP_GLASS_W / 2 - 0.3, p.DISP_GLASS_W / 2 + 0.3,
                                gz - p.DISP_GLASS_H / 2 - 0.3, gz + p.DISP_GLASS_H / 2 + 0.3)
    for sy in (-1, 1):
        for sz, blen, edge in ((-1, p.DISP_BARE_END_HDR, z0), (1, p.DISP_BARE_END_FAR, z1)):
            m.bare[f"c{sy:+d}{sz:+d}"] = (sy, sz, edge, blen)
    return m


def camera(p) -> Module:
    m = Module("camera")
    W, H = p.CAM_PCB_W, p.CAM_PCB_H
    cf, cb = p.CAM_PCB_FRONT_X, p.CAM_PCB_BACK_X
    cz = p.CAM_PCB_CZ
    zb, zt = cz - H / 2, cz + H / 2
    ay, az = p.CAM_OPT_OFF_Y, p.CAM_AXIS_Z
    m.hard["pcb"] = box(cb, cf, -W / 2, W / 2, zb, zt)
    hold_l = p.CAM_LENS_PROJ * 0.55
    s = p.CAM_HOLDER_SQ / 2
    m.hard["holder"] = box(cf, cf + hold_l, ay - s, ay + s, az - s, az + s)
    m.hard["lens"] = cyl_x(ay, az, p.CAM_LENS_D / 2, cf + hold_l - 0.1, p.CAM_LENS_FRONT_X)
    bc = p.CAM_BARE_CORNER
    m.hard["back_parts"] = box(cb - p.CAM_BACK_POP, cb, -W / 2 + bc, W / 2 - bc, zb + bc, zt - bc)
    hz = zb + p.CAM_HDR_INSET
    hl = p.CAM_HDR_PINS * 2.54
    m.hard["header"] = box(cb - 2.5 - 6.0, cb, -hl / 2, hl / 2, hz - 1.27, hz + 1.27)
    m.hard["plugs"] = box(cb - p.PLUG_DEPTH, cb - 2.5, -hl / 2 - 0.3, hl / 2 + 0.3,
                          hz - p.DUPONT_HOUSING_W / 2, hz + p.DUPONT_HOUSING_W / 2)
    # header may point back OR down on your unit: reserve both
    near = p.PLUG_DEPTH + p.WIRE_STRAIGHT_EXIT
    m.fields["wires_back_near"] = box(cb - near, cb - 2.5, -hl / 2 - 2, hl / 2 + 2, zb - 1.0, hz + 4.0)
    m.fields["wires_back_bend"] = box(cb - p.WIRE_FIELD, cb - near, -hl / 2 - p.WIRE_BEND_R,
                                      hl / 2 + p.WIRE_BEND_R, zb - 6.0, hz + p.WIRE_BEND_R)
    m.fields["wires_down"] = box(cb - 4.0, cf + 0.3, -hl / 2 - 0.5, hl / 2 + 0.5, zb - p.WIRE_FIELD, zb)
    m.fields["open_back"] = box(cb - p.CAM_BACK_POP - 1.5, cb, -W / 2 + bc, W / 2 - bc,
                                zb + bc, zt - bc)
    m.fields["lens_air"] = cyl_x(ay, az, p.CAM_LENS_D / 2 + p.LENS_RADIAL_GAP - 0.05,
                                 cf + hold_l, p.FAIR_FRONT_X + 2)
    for sy in (-1, 1):
        for sz in (-1, 1):
            m.bare[f"c{sy:+d}{sz:+d}"] = (sy, sz)
    return m


def esp32(p) -> Module:
    m = Module("esp32")
    x0, x1, cz, W = p.ESP_X0, p.ESP_X1, p.ESP_CZ, p.ESP_W
    tf, bk = p.ESP_TOP_FACE_Y, p.ESP_BACK_FACE_Y
    zb, zt = cz - W / 2, cz + W / 2
    bc = p.ESP_BARE_CORNER
    m.hard["pcb"] = box(x0, x1, tf, bk, zb, zt)
    m.hard["top_parts"] = box(x0 + bc, x1, tf - p.ESP_TOP_POP, tf, zb + 0.5, zt - 0.5)
    m.hard["top_parts_mid"] = box(x0, x1, tf - p.ESP_TOP_POP, tf, zb + bc, zt - bc)
    us = p.ESP_USB_HALF_SPAN
    m.hard["usb"] = box(x1 - 7.5, x1 + p.ESP_USB_PROJ, tf - 3.3, tf, cz - us, cz + us)
    hx = p.ESP_CX + p.ESP_HDR_OFF_X
    hl = p.ESP_HDR_LEN
    for side, zr in (("lo", zb + 1.27), ("hi", zt - 1.27)):
        m.hard[f"header_{side}"] = box(hx - hl / 2, hx + hl / 2, bk, bk + p.ESP_HDR_SPACER + 6.0,
                                       zr - 1.27, zr + 1.27)
        m.hard[f"plugs_{side}"] = box(hx - hl / 2 - 0.3, hx + hl / 2 + 0.3,
                                      bk + p.ESP_HDR_SPACER, bk + p.ESP_HDR_SPACER + p.DUPONT_HOUSING_L,
                                      zr - p.DUPONT_HOUSING_W / 2, zr + p.DUPONT_HOUSING_W / 2)
    near = p.ESP_HDR_SPACER + p.DUPONT_HOUSING_L + p.WIRE_STRAIGHT_EXIT
    wf = near + p.WIRE_BEND_R + p.WIRE_STRAIN
    for side, zr in (("lo", zb + 1.27), ("hi", zt - 1.27)):
        m.fields[f"wires_near_{side}"] = box(hx - hl / 2 - 2, hx + hl / 2 + 2, bk + p.ESP_HDR_SPACER,
                                             bk + near, zr - 3.0, zr + 3.0)
    m.fields["wires_bend"] = box(hx - hl / 2 - 5, hx + hl / 2 + 5, bk + near, bk + wf,
                                 zb - p.WIRE_BEND_R - 7, zt + p.WIRE_BEND_R + 7)
    uy = tf - 1.65  # receptacle centre line
    pz = max(us - p.USB_PLUG_W / 2 + 0.5, 0.0)  # plug may sit on either port
    m.fields["prog_usb"] = box(x1 + p.ESP_USB_PROJ, x1 + p.ESP_USB_PROJ + p.PROG_CORRIDOR_L,
                               uy - p.USB_PLUG_T / 2, uy + p.USB_PLUG_T / 2,
                               cz - pz - p.USB_PLUG_W / 2, cz + pz + p.USB_PLUG_W / 2)
    m.fields["prog_exit"] = box(x1 + p.ESP_USB_PROJ + 14, x1 + p.ESP_USB_PROJ + p.PROG_CORRIDOR_L,
                                uy - p.USB_PLUG_T / 2, 0.0,
                                cz - pz - p.USB_PLUG_W / 2, cz + pz + p.USB_PLUG_W / 2)
    for sx in (-1, 1):
        for sz in (-1, 1):
            m.bare[f"c{sx:+d}{sz:+d}"] = (sx, sz)
    return m


def battery(p) -> Module:
    m = Module("battery")
    x0, z0 = p.BAT_X0, p.BAT_Z0
    x1, z1 = x0 + p.BAT_W, z0 + p.BAT_L
    m.hard["pack"] = box(x0, x1, -p.BAT_T / 2, p.BAT_T / 2, z0, z1)
    m.fields["leads"] = box(x0 + 3, x1 - 3, -p.BAT_T / 2, p.BAT_T / 2, z1 + p.FOAM_T + 0.2, z1 + 14)
    return m


def charger(p) -> Module:
    m = Module("charger")
    x0, z0, cy = p.CHG_X0, p.CHG_Z0, p.CHG_CY
    x1 = x0 + p.CHG_L
    bc = p.CHG_BARE_CORNER
    m.hard["pcb"] = box(x0, x1, cy - p.CHG_W / 2, cy + p.CHG_W / 2, z0, z0 + 1.6)
    # parts on both faces: everywhere except the two bare front corners
    for zz in ((z0 + 1.6, z0 + p.CHG_H), (z0 - 1.5, z0)):
        m.hard[f"parts_{'top' if zz[0] > z0 else 'bottom'}"] = box(
            x0, x1 - bc, cy - p.CHG_W / 2, cy + p.CHG_W / 2, *zz).fuse(
            box(x0, x1, cy - p.CHG_W / 2 + bc, cy + p.CHG_W / 2 - bc, *zz))
    uy = cy + p.CHG_USB_OFF_Y
    m.hard["usb_c"] = box(x0 - 0.6, x0 + 7.4, uy - 4.5, uy + 4.5, z0 + 1.6, z0 + 1.6 + 3.3)
    m.fields["wires"] = box(x1 + p.EDGE_GAP + 2.3, x1 + 22, cy - p.CHG_W / 2 - 3, cy + p.CHG_W / 2 + 3,
                            z0 - 5, z0 + p.CHG_H + 6)
    uz = z0 + 1.6 + 1.65
    rec_floor = -5 + 5 + p.USB_OVERMOLD_DEPTH
    m.fields["plug_overmold_air"] = (cq.Workplane("YZ", origin=(-8, 0, 0)).center(uy, uz)
                                     .slot2D(p.USB_OVERMOLD_W - 0.2, p.USB_OVERMOLD_H - 0.2)
                                     .extrude(8 + rec_floor).val())
    m.fields["plug_metal_air"] = (cq.Workplane("YZ", origin=(rec_floor - 0.01, 0, 0)).center(uy, uz)
                                  .slot2D(8.4, 2.6).extrude(x0 - 0.6 - rec_floor + 0.02).val())
    for sy in (-1, 1):
        for sx in (-1, 1):
            m.bare[f"c{sx:+d}{sy:+d}"] = (sx, sy)
    return m


def button(p) -> Module:
    m = Module("button")
    # lowered behind the panel, then pushed out through the hole; nut from inside
    m.insert_path = [(p.WALL + 3.0, 80.0, 0.0), (p.WALL + 3.0, 0.0, 0.0), (0.0, 0.0, 0.0)]
    m.hard["body"] = cq.Solid.makeCylinder(p.BTN_BODY_D / 2, p.BTN_DEPTH,
                                           V(p.WALL, p.BTN_Y, p.BTN_Z), V(1, 0, 0))
    m.hard["cap"] = cq.Solid.makeCylinder(p.BTN_HOLE_D / 2 - 0.4, p.WALL + 2.0,
                                          V(-2.0, p.BTN_Y, p.BTN_Z), V(1, 0, 0))
    m.fields["leads"] = box(p.WALL + p.BTN_DEPTH, p.WALL + p.BTN_DEPTH + 8, p.BTN_Y - 8,
                            p.BTN_Y + 8, p.BTN_Z - 8, p.BTN_Z + 8)
    return m


def modules(p) -> dict[str, Module]:
    return {m.name: m for m in (display(p), camera(p), esp32(p), battery(p), charger(p), button(p))}


# ---------------------------------------------------------------------------
# retention features (all gentle: foam-lined slots, pads, lay-in clips, ribs)
# ---------------------------------------------------------------------------
def display_slots(p) -> list:
    """Corner slots: front jaw on bare PCB front, back jaw on bare back corner,
    side + end stops; each slot is open toward the seam (lay-in along Y)."""
    out = []
    W = p.DISP_PCB_W
    pf, pb = p.DISP_PCB_FRONT_X, p.DISP_PCB_BACK_X
    g = p.FOAM_T + p.SLOT_EXTRA / 2
    stop = 2.0
    for sy in (-1, 1):
        ey = sy * W / 2
        for sz, edge, blen in ((-1, p.DISP_Z0, p.DISP_BARE_END_HDR), (1, p.DISP_Z1, p.DISP_BARE_END_FAR)):
            blk = box(p.WALL - 0.3, pb + g + p.JAW_T,
                      ey + sy * (p.EDGE_GAP + stop), ey - sy * p.DISP_BARE_SIDE,
                      edge + sz * (p.EDGE_GAP + stop), edge - sz * blen)
            slot = box(pf - g, pb + g, ey + sy * p.EDGE_GAP, -sy * BIG,
                       edge + sz * p.EDGE_GAP, -sz * BIG)
            out.append(blk.cut(slot))
    return out


def camera_slots(p) -> list:
    """Top corners: full slot (front jaw, back jaw, side + end stop).
    Bottom corners sit beside the 8-pin header, so: front jaw + side stop only,
    and the bottom end stop stays outside the header span."""
    out = []
    W, H = p.CAM_PCB_W, p.CAM_PCB_H
    cf, cb = p.CAM_PCB_FRONT_X, p.CAM_PCB_BACK_X
    cz = p.CAM_PCB_CZ
    g = p.FOAM_T + p.SLOT_EXTRA / 2
    bc = p.CAM_BARE_CORNER
    stop = 1.8
    hl = p.CAM_HDR_PINS * 2.54
    for sy in (-1, 1):
        ey = sy * W / 2
        for sz in (-1, 1):
            ez = cz + sz * H / 2
            xb = cb - g - p.JAW_T if sz > 0 else cb - g
            blk = box(xb, BIG, ey + sy * (p.EDGE_GAP + stop), ey - sy * bc,
                      ez + sz * (p.EDGE_GAP + stop), ez - sz * bc)
            slot = box(cb - g, cf + g, ey + sy * p.EDGE_GAP, -sy * BIG, ez + sz * p.EDGE_GAP, -sz * BIG)
            blk = blk.cut(slot)
            if sz < 0:
                # keep the bottom end stop (and everything behind the front jaw) clear of the header span
                blk = blk.cut(box(cb - 20, cf + g, -hl / 2 - 1.0, hl / 2 + 1.0, ez - 20, ez + bc + 1))
                blk = blk.cut(box(cb - 20, BIG, -hl / 2 - 1.0, hl / 2 + 1.0, ez - 20, ez - p.EDGE_GAP))
            out.append(blk)
    return out


def esp32_supports(p) -> tuple[list, list]:
    """Antenna end (X0): component-side pads on the bare corners + end stops.
    USB end (X1): the corners carry USB-C/buttons, so NO pads there; the end
    stop is a small tab on the clip beam outside the USB/plug span.
    All four corners: lay-in snap clips beside the long edges (beam deflects
    along Z, hook laps the bare back-face corner beyond the header ends)."""
    out, clips = [], []
    wall_y = -p.INNER_SIDE_Y - 0.3
    tf, bk = p.ESP_TOP_FACE_Y, p.ESP_BACK_FACE_Y
    bc = p.ESP_BARE_CORNER
    W = p.ESP_W
    for sx, ex in ((-1, p.ESP_X0), (1, p.ESP_X1)):
        for sz in (-1, 1):
            ez = p.ESP_CZ + sz * W / 2
            if sx < 0:
                out.append(box(ex, ex - sx * bc, wall_y, tf - p.FOAM_T, ez, ez - sz * bc))
                out.append(box(ex + sx * p.EDGE_GAP, ex + sx * (p.EDGE_GAP + 1.8), wall_y, bk - 0.2,
                               ez, ez - sz * bc))
            cz0 = ez + sz * p.EDGE_GAP
            beam = box(ex - sx * 0.5, ex - sx * (bc - 0.3), wall_y, bk + 1.6,
                       cz0, cz0 + sz * p.CLIP_T)
            xa, xb = sorted((ex - sx * 0.5, ex - sx * (bc - 0.3)))
            z_in = ez - sz * p.CLIP_HOOK
            pts = [(bk + 0.15, cz0), (bk + 0.15, z_in), (bk + 0.9, z_in), (bk + 2.1, cz0)]
            hook = (cq.Workplane("YZ", origin=(xa, 0, 0)).polyline(pts).close()
                    .extrude(xb - xa).val())
            out.append(beam)
            out.append(hook)
            clips.append(hook)
            if sx > 0:
                # end tab: a short arm from the beam past the board end, catching the
                # PCB edge only in the strip outside the USB-C / plug span
                z_tab = max(p.ESP_USB_HALF_SPAN, p.USB_PLUG_W / 2 + max(p.ESP_USB_HALF_SPAN - p.USB_PLUG_W / 2 + 0.5, 0)) + 0.3
                if z_tab < W / 2 - 0.3:
                    arm = box(ex - sx * 0.5, ex + sx * (p.EDGE_GAP + 1.6), tf - 0.2, bk + 1.6,
                              cz0, cz0 + sz * p.CLIP_T)
                    tab = box(ex + sx * p.EDGE_GAP, ex + sx * (p.EDGE_GAP + 1.6), tf - 0.2, bk + 1.6,
                              p.ESP_CZ + sz * z_tab, cz0 + sz * 0.01)
                    out.append(arm.fuse(tab))
    return out, clips


def battery_cradle(p, cav) -> list:
    out = []
    x0, z0 = p.BAT_X0, p.BAT_Z0
    x1, z1 = x0 + p.BAT_W, z0 + p.BAT_L
    g = p.FOAM_T + 0.1
    hole = box(x0 - g, x1 + g, -p.BAT_T / 2 - g, p.BAT_T / 2 + g, z0 - g, z1 + g)
    leg = box(p.LOOP_X1 + p.WALL - 0.2, BIG, -BIG, BIG, -BIG, BIG)
    levels = [(z0 - g - 2.4, z0 - g)]
    for f in (0.2, 0.5, 0.8):
        zc = z0 + f * p.BAT_L
        levels.append((zc - 1.2, zc + 1.2))
    levels.append((z1 + g, z1 + g + 2.4))
    for i, (a, b) in enumerate(levels):
        sl = cav.intersect(box(-BIG, BIG, -BIG, BIG, a, b)).intersect(leg)
        rib = sl.cut(hole)
        if i == len(levels) - 1:  # top: tabs only, leave room for the leads
            rib = rib.cut(box(x0 + 2.5, x1 - 2.5, -BIG, BIG, a - 1, b + 1))
        out.append(rib)
    return out


def charger_slots(p) -> list:
    out = []
    x0, z0, cy = p.CHG_X0, p.CHG_Z0, p.CHG_CY
    x1 = x0 + p.CHG_L
    g = p.FOAM_T + p.SLOT_EXTRA / 2
    pcb_t = 1.6
    for sx, ex in ((-1, x0), (1, x1)):
        for sy in (-1, 1):
            ey = cy + sy * p.CHG_W / 2
            if sx < 0:
                continue  # rear edge is located by the USB-C against the wall
            bc = p.CHG_BARE_CORNER
            blk = box(ex + sx * (p.EDGE_GAP + 2.0), ex - sx * bc, ey + sy * (p.EDGE_GAP + 2.0),
                      ey - sy * bc, z0 - g - p.JAW_T - 1.6, z0 + pcb_t + g + p.JAW_T)
            slot = box(ex + sx * p.EDGE_GAP, -sx * BIG, ey + sy * p.EDGE_GAP, -sy * BIG,
                       z0 - g, z0 + pcb_t + g)
            blk = blk.cut(slot)
            # tether down to the leg floor/side so it is attached to the shell
            teth = box(ex + sx * (p.EDGE_GAP + 2.0), ex + sx * 0.3, ey + sy * (p.EDGE_GAP + 2.0),
                       ey + sy * 0.3, -BIG, z0 - g)
            out.append(blk.fuse(teth))
    return out


# ---------------------------------------------------------------------------
# screws, openings, seam, accents, routes
# ---------------------------------------------------------------------------
def screw_features(p, outer):
    bosses, cuts, table = [], [], []
    for name, x, z in p.screws:
        col = cyl_y(x, z, p.BOSS_D / 2, -BIG / 2, BIG / 2).intersect(outer)
        bosses.append(col)
        seat = p.SCREW_SEAT_TO_SEAM
        cuts.append(cyl_y(x, z, p.M2_WELL_D / 2, seat, BIG / 2))
        cuts.append(cyl_y(x, z, p.M2_CLEAR_D / 2, -0.01, seat + 0.01))
        length = 12.0
        tip = seat - length
        pilot_depth = -tip + 2.0
        cuts.append(cyl_y(x, z, p.M2_PILOT_D / 2, -pilot_depth, 0.01))
        bb = col.BoundingBox()
        table.append(dict(name=name, x=x, z=z, length=length, seat_to_seam=seat,
                          engagement=length - seat, pilot_depth=pilot_depth,
                          left_skin=round(-bb.ymin - pilot_depth, 2),
                          well_depth=round(bb.ymax - seat, 2)))
    return bosses, cuts, table


def openings(p) -> dict:
    o = {}
    # touch window (active area + margin) with an outer chamfer for fingertips
    ww = p.DISP_ACTIVE_W + 2 * p.WINDOW_MARGIN
    wh = p.DISP_ACTIVE_H + 2 * p.WINDOW_MARGIN
    wy = p.DISP_ACTIVE_OFF_Y
    wz = p.DISP_CZ + p.DISP_ACTIVE_OFF_Z
    c = p.WINDOW_CHAMFER
    win = (cq.Workplane("YZ", origin=(-0.5, 0, 0)).center(wy, wz).rect(ww + 2 * (c + 0.5), wh + 2 * (c + 0.5))
           .workplane(offset=c + 0.5).rect(ww, wh).loft().val())
    win = win.fuse(box(-1, p.WALL + 1.0, wy - ww / 2, wy + ww / 2, wz - wh / 2, wz + wh / 2))
    o["touch_window"] = win
    # lens aperture: radial clearance so nothing rubs the lens, outward flare for the view cone
    lr = p.CAM_LENS_D / 2 + p.LENS_RADIAL_GAP
    ap = cyl_x(p.CAM_OPT_OFF_Y, p.CAM_AXIS_Z, lr, p.CAM_LENS_FRONT_X - 8, p.FAIR_FRONT_X + 5)
    flare = cq.Solid.makeCone(lr, lr + 4.0, 4.0, V(p.FAIR_FRONT_X - 2.5, p.CAM_OPT_OFF_Y, p.CAM_AXIS_Z),
                              V(1, 0, 0))
    o["lens_aperture"] = ap.fuse(flare)
    # latching power button
    o["button_hole"] = cq.Solid.makeCylinder(p.BTN_HOLE_D / 2, 20, V(-10, p.BTN_Y, p.BTN_Z), V(1, 0, 0))
    # charger USB-C with an overmold recess on the outside
    uy = p.CHG_CY + p.CHG_USB_OFF_Y
    uz = p.CHG_Z0 + 1.6 + 1.65
    slot = (cq.Workplane("YZ", origin=(-5, 0, 0)).center(uy, uz)
            .slot2D(p.USB_SLOT_W, p.USB_SLOT_H).extrude(p.WALL + 6).val())
    rec = (cq.Workplane("YZ", origin=(-5, 0, 0)).center(uy, uz)
           .slot2D(p.USB_OVERMOLD_W, p.USB_OVERMOLD_H).extrude(5 + p.USB_OVERMOLD_DEPTH).val())
    o["usb_c"] = slot.fuse(rec)
    return o


def seam_lip(p):
    inner = body(p, -p.WALL)
    mid = body(p, -p.WALL * 0.45)
    lip = mid.cut(inner).intersect(halfspace_y(-0.01, p.LIP_H))
    g_out = body(p, -p.WALL * 0.45 + p.LIP_CLEAR)
    g_in = body(p, -p.WALL - p.LIP_CLEAR)
    groove = g_out.cut(g_in).intersect(halfspace_y(-0.01, p.LIP_H + p.LIP_CLEAR))
    # no lip across the camera nose: its doubly-curved wall is too thin to split cleanly
    nose = cyl_x(0, p.CAM_AXIS_Z, p.FAIR_R + 1.0, p.FAIR_X0 - 5, BIG)
    return lip.cut(nose), groove.cut(nose)


def accent_tool(p) -> cq.Shape:
    """Solid whose intersection with a shell is the BLUE material region."""
    parts = []
    # D-outline stripe along both rounded shoulders
    a = d_profile(p, -9.0).extrude(BIG / 2, both=True).val()
    b = d_profile(p, -15.0).extrude(BIG / 2, both=True).val()
    stripe = a.cut(b)
    parts.append(stripe.cut(halfspace_y(-44.0, 44.0)))
    # lens ring on the fairing face
    lr = p.CAM_LENS_D / 2 + p.LENS_RADIAL_GAP
    ring = cyl_x(p.CAM_OPT_OFF_Y, p.CAM_AXIS_Z, lr + 5.5, p.FAIR_FRONT_X - 7, p.FAIR_FRONT_X + 3).cut(
        cyl_x(p.CAM_OPT_OFF_Y, p.CAM_AXIS_Z, lr + 0.01, p.FAIR_FRONT_X - 8, p.FAIR_FRONT_X + 4))
    parts.append(ring)
    # frame around the touch window
    ww = p.DISP_ACTIVE_W + 2 * p.WINDOW_MARGIN + 2 * p.WINDOW_CHAMFER
    wh = p.DISP_ACTIVE_H + 2 * p.WINDOW_MARGIN + 2 * p.WINDOW_CHAMFER
    wz = p.DISP_CZ + p.DISP_ACTIVE_OFF_Z
    frame = (cq.Workplane("YZ", origin=(-1, 0, 0)).center(p.DISP_ACTIVE_OFF_Y, wz)
             .rect(ww + 7, wh + 7).extrude(p.WALL + 1.01).edges("|X").fillet(3.0).val())
    parts.append(frame)
    # liner on the hand-loop ceiling and leg faces
    grown = loop_cut_profile(p, 1.4).extrude(BIG / 2, both=True).val()
    core = loop_cut_profile(p, 0.0).extrude(BIG / 2, both=True).val()
    parts.append(grown.cut(core).intersect(box(-BIG, BIG, -BIG, BIG, p.LOOP_Z0 - 2.0, BIG)))
    return fuse(parts)


def routes(p) -> dict:
    r = p.ROUTE_R
    ex = p.ESP_BACK_FACE_Y + 20
    return {
        "camera_to_esp32": ([(p.CAM_PCB_BACK_X - 24, -4, p.CAM_PCB_CZ - 8),
                             (p.ESP_X1 + 8, -18, p.ESP_CZ - 4), (p.ESP_X1 - 8, ex, p.ESP_CZ)], r),
        "esp32_to_display": ([(p.ESP_X0 + 6, ex, p.ESP_CZ - 14), (42, -16, 108),
                              (p.DISP_PCB_BACK_X + 18, -6, p.DISP_Z0 + 12)], r + 1),
        "power_trunk_to_charger": ([(p.DISP_PCB_BACK_X + 20, -4, p.DISP_Z0 + 8), (36, -8, 72),
                                    (34, -6, p.CHG_Z0 + 8)], r),
        "battery_to_charger": ([(p.BAT_X0 + p.BAT_W / 2, 0, p.BAT_Z0 + p.BAT_L + 12), (146, -4, 121),
                                (138, -4, 100), (60, -4, 100), (40, -6, 88), (34, -6, p.CHG_Z0 + 8)], r),
        "button_to_charger": ([(p.WALL + p.BTN_DEPTH + 4, p.BTN_Y, p.BTN_Z), (32, -8, p.CHG_Z0 + 12)], 4.0),
    }


def topology() -> list[tuple[str, str, str]]:
    return [
        ("camera", "esp32", "SPI (CS, MOSI, MISO, SCLK) + I2C (SDA, SCL) + VCC + GND"),
        ("esp32", "display", "SPI (CS, DC, RESET, MOSI, SCK) + touch (T_CS, T_DIN, T_CLK, T_DO, T_IRQ) + BL + VCC + GND"),
        ("battery", "charger", "BATT (JST, factory leads)"),
        ("charger", "run_pigtail", "5V output"),
        ("run_pigtail", "esp32", "system 5V + GND"),
        ("button", "charger", "EN to GND (closed = output off)"),
    ]
