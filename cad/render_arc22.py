#!/usr/bin/env python3
"""
render_arc22.py — step 5 of the rebuild order.

Pure-numpy z-buffer renderer (no OpenGL needed) for the docs images:
  docs/img/arc22_hero_front.png      assembled, front-left
  docs/img/arc22_hero_rear.png       assembled, rear (touch window, button, USB-C)
  docs/img/arc22_exploded.png        LEFT | modules | RIGHT
  docs/img/arc22_left_interior.png   inside the LEFT shell with modules + cable routes
  docs/img/arc22_fields.png          reserved wire/air fields (orange) vs supports
  docs/img/arc22_section_*.png       2-D sections
  docs/img/fit_samples.png           the three print-first fit samples
Renders are regenerated from cad/build; they are never the source of truth.
"""
from __future__ import annotations

import json
import pathlib
import sys

import cadquery as cq
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import arc22_geometry as G  # noqa: E402

BUILD = HERE / "build"
IMG = HERE.parent / "docs" / "img"

C_WHITE = (0.93, 0.95, 0.96)
C_BLUE = (0.10, 0.62, 0.86)
C_ORANGE = (1.0, 0.55, 0.12)
MOD_COL = {"display": (0.12, 0.14, 0.18), "camera": (0.16, 0.45, 0.26), "esp32": (0.12, 0.30, 0.55),
           "battery": (0.42, 0.42, 0.48), "charger": (0.55, 0.20, 0.50), "button": (0.80, 0.80, 0.80)}
BG = np.array([1.0, 1.0, 1.0])


def tess(shape, tol=0.08, ang=0.15):
    v, f = shape.tessellate(tol, ang)
    return np.array([(p.x, p.y, p.z) for p in v], float), np.array(f, np.int64).reshape(-1, 3)


def load(name):
    return cq.Shape.importBrep(str(BUILD / f"{name}.brep"))


class Scene:
    def __init__(self):
        self.parts = []  # (V, F, rgb, edges?)

    def add(self, shape, rgb, offset=(0, 0, 0), edges=True, tol=0.08):
        v, f = tess(shape, tol)
        self.parts.append((v + np.array(offset), f, np.array(rgb), edges))

    def add_mesh(self, v, f, rgb, edges=True):
        self.parts.append((np.asarray(v, float), np.asarray(f), np.array(rgb), edges))

    def render(self, path, az=-55, el=22, size=(1400, 1050), ss=2, margin=0.06, light=(-0.35, -0.55, 0.75),
               callouts=None):
        W, H = size[0] * ss, size[1] * ss
        a, e = np.radians(az), np.radians(el)
        fwd = -np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])
        right = np.cross(fwd, [0, 0, 1.0])
        right /= np.linalg.norm(right)
        up = np.cross(right, fwd)
        Lg = np.array(light, float)
        Lg /= np.linalg.norm(Lg)
        allv = np.vstack([p[0] for p in self.parts])
        X, Y = allv @ right, allv @ up
        span = max(np.ptp(X) / (1 - 2 * margin) / W, np.ptp(Y) / (1 - 2 * margin) / H)
        cx, cy = (X.max() + X.min()) / 2, (Y.max() + Y.min()) / 2

        def proj(v):
            return ((v @ right - cx) / span + W / 2, H / 2 - (v @ up - cy) / span, v @ fwd)

        zbuf = np.full((H, W), np.inf)
        img = np.ones((H, W, 3)) * BG
        edge_jobs = []
        for V, F, rgb, edges in self.parts:
            px, py, pz = proj(V)
            tri = V[F]
            n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
            ln = np.linalg.norm(n, axis=1)
            ok = ln > 1e-12
            n[ok] /= ln[ok, None]
            facing = n @ fwd
            n[facing > 0] *= -1  # two-sided
            diff = np.clip(n @ Lg, 0, 1)
            hv = Lg - fwd
            hv /= np.linalg.norm(hv)
            spec = np.clip(n @ hv, 0, 1) ** 40
            shade = 0.38 + 0.62 * diff
            cols = np.clip(rgb[None, :] * shade[:, None] + 0.18 * spec[:, None], 0, 1)
            for i in np.nonzero(ok)[0]:
                i0, i1, i2 = F[i]
                xs = np.array([px[i0], px[i1], px[i2]])
                ys = np.array([py[i0], py[i1], py[i2]])
                zs = np.array([pz[i0], pz[i1], pz[i2]])
                x0, x1 = max(int(xs.min()), 0), min(int(xs.max()) + 1, W - 1)
                y0, y1 = max(int(ys.min()), 0), min(int(ys.max()) + 1, H - 1)
                if x0 > x1 or y0 > y1:
                    continue
                den = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
                if abs(den) < 1e-9:
                    continue
                gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
                w0 = ((ys[1] - ys[2]) * (gx - xs[2]) + (xs[2] - xs[1]) * (gy - ys[2])) / den
                w1 = ((ys[2] - ys[0]) * (gx - xs[2]) + (xs[0] - xs[2]) * (gy - ys[2])) / den
                w2 = 1 - w0 - w1
                inside = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
                if not inside.any():
                    continue
                z = w0 * zs[0] + w1 * zs[1] + w2 * zs[2]
                sub = zbuf[y0:y1 + 1, x0:x1 + 1]
                m = inside & (z < sub)
                sub[m] = z[m]
                img[y0:y1 + 1, x0:x1 + 1][m] = cols[i]
            if edges:
                tm = trimesh.Trimesh(V, F, process=True)
                fe = tm.face_adjacency_edges[tm.face_adjacency_angles > np.radians(30)]
                edge_jobs.append((tm.vertices, fe))
        # feature edges with a depth test
        for Vt, E in edge_jobs:
            if len(E) == 0:
                continue
            ex, ey, ez = proj(Vt)
            for a_, b_ in E:
                n_ = int(max(abs(ex[a_] - ex[b_]), abs(ey[a_] - ey[b_]))) + 2
                t = np.linspace(0, 1, n_)
                xs = (ex[a_] + (ex[b_] - ex[a_]) * t).astype(int)
                ys = (ey[a_] + (ey[b_] - ey[a_]) * t).astype(int)
                zs = ez[a_] + (ez[b_] - ez[a_]) * t
                ok = (xs >= 0) & (xs < W) & (ys >= 0) & (ys < H)
                xs, ys, zs = xs[ok], ys[ok], zs[ok]
                vis = zs <= zbuf[ys, xs] + 0.35 * span * 3
                img[ys[vis], xs[vis]] = img[ys[vis], xs[vis]] * 0.45
        # downsample (anti-alias)
        img = img.reshape(size[1], ss, size[0], ss, 3).mean(axis=(1, 3))
        path.parent.mkdir(parents=True, exist_ok=True)
        if not callouts:
            plt.imsave(path, np.clip(img, 0, 1))
            print("  wrote", path.relative_to(HERE.parent))
            return
        # numbered callouts: (xyz anchor, label, (dx, dy) label offset in pixels)
        dpi = 100
        fig = plt.figure(figsize=(size[0] / dpi, size[1] / dpi), dpi=dpi)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.imshow(np.clip(img, 0, 1))
        ax.set_xlim(0, size[0])
        ax.set_ylim(size[1], 0)
        ax.axis("off")
        for i, (p, label, (dx, dy)) in enumerate(callouts, 1):
            v = np.asarray(p, float)
            px, py = ((v @ right - cx) / span + W / 2) / ss, (H / 2 - (v @ up - cy) / span) / ss
            tx, ty = px + dx, py + dy
            ax.plot([px, tx], [py, ty], color="#17303d", lw=1.2, zorder=4)
            ax.plot([px], [py], "o", ms=5, color="#17303d", zorder=5)
            ax.text(tx, ty, str(i), ha="center", va="center", fontsize=12, weight="bold", color="white", zorder=6,
                    bbox=dict(boxstyle="circle,pad=0.35", fc="#1a9fdb", ec="white", lw=1.5))
            ax.text(tx + (22 if dx >= 0 else -22), ty, label, ha="left" if dx >= 0 else "right", va="center",
                    fontsize=11.5, color="#17303d", zorder=6,
                    bbox=dict(boxstyle="round,pad=0.25", fc=(1, 1, 1, 0.85), ec="none"))
        fig.savefig(path, dpi=dpi)
        plt.close(fig)
        print("  wrote", path.relative_to(HERE.parent))


def shells(scene, dy_left=0.0, dy_right=0.0):
    for side, dy in (("LEFT", dy_left), ("RIGHT", dy_right)):
        scene.add(load(f"{side}_WHITE"), C_WHITE, (0, dy, 0))
        scene.add(load(f"{side}_BLUE"), C_BLUE, (0, dy, 0))


def modules(scene, man, offset=(0, 0, 0), fields=False):
    for mod, info in man["modules"].items():
        for part in info["hard"]:
            scene.add(load(f"mod_{mod}__hard__{part}"), MOD_COL[mod], offset, edges=False, tol=0.2)
        if fields:
            for part in info["fields"]:
                scene.add(load(f"mod_{mod}__field__{part}"), C_ORANGE, offset, edges=False, tol=0.3)


def section(path, title, y=None, x=None, z=None):
    """2-D section of shells (grey), hard parts (dark) and fields (orange outline)."""
    man = json.loads((BUILD / "manifest.json").read_text())
    if y is not None:
        origin, normal, axes, lab = [0, y, 0], [0, 1, 0], (0, 2), ("X (front →)", "Z (up)")
    elif x is not None:
        origin, normal, axes, lab = [x, 0, 0], [1, 0, 0], (1, 2), ("Y (right →)", "Z (up)")
    else:
        origin, normal, axes, lab = [0, 0, z], [0, 0, 1], (0, 1), ("X (front →)", "Y (right →)")
    fig, ax = plt.subplots(figsize=(8, 8))

    def draw(shape, style):
        v, f = tess(shape, 0.1)
        tm = trimesh.Trimesh(v, f, process=True)
        sec = tm.section(plane_origin=origin, plane_normal=normal)
        if sec is None:
            return
        for ent in sec.entities:
            pts = sec.vertices[ent.points]
            ax.plot(pts[:, axes[0]], pts[:, axes[1]], **style)

    for side in ("LEFT", "RIGHT"):
        draw(load(side), dict(color="#5b6770", lw=1.1))
    for mod, info in man["modules"].items():
        for part in info["hard"]:
            draw(load(f"mod_{mod}__hard__{part}"), dict(color=np.array(MOD_COL[mod]) * 0.9, lw=1.0))
        for part in info["fields"]:
            draw(load(f"mod_{mod}__field__{part}"), dict(color="#ff8c1a", lw=0.8, ls="--"))
    for k in man["routes"]:
        draw(load(f"route_{k}"), dict(color="#e0561b", lw=0.6, ls=":"))
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=10)
    ax.set_xlabel(lab[0])
    ax.set_ylabel(lab[1])
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    print("  wrote", path.relative_to(HERE.parent))


def main() -> int:
    man = json.loads((BUILD / "manifest.json").read_text())
    p = man["params"]
    print("• assembled views")
    s = Scene()
    shells(s)
    s.render(IMG / "arc22_hero_front.png", az=-50, el=20)
    s.render(IMG / "arc22_hero_rear.png", az=205, el=14)
    print("• exploded")
    s = Scene()
    shells(s, -120, 120)
    modules(s, man)
    s.render(IMG / "arc22_exploded.png", az=-18, el=42, size=(1500, 1100))
    print("• assembly callouts")
    s = Scene()
    shells(s, -120, 120)
    OFF = {"display": (-50, 0, 25), "camera": (40, 0, 30), "esp32": (5, 0, 70), "battery": (35, 0, -30),
           "charger": (-55, 0, -55), "button": (-95, 0, -10)}
    for mod, info in man["modules"].items():
        for part in info["hard"]:
            s.add(load(f"mod_{mod}__hard__{part}"), MOD_COL[mod], OFF[mod], edges=False, tol=0.2)

    def ctr(mod):
        bb = G.fuse([load(f"mod_{mod}__hard__{k}") for k in man["modules"][mod]["hard"]]).BoundingBox()
        o = OFF[mod]
        return (bb.center.x + o[0], bb.center.y + o[1], bb.center.z + o[2])

    scr = man["screws"][0]
    s.render(IMG / "arc22_assembly.png", az=-18, el=42, size=(1600, 1150), margin=0.1, callouts=[
        ((40, -150, 150), "Left shell", (-40, -90)),
        ((70, 150, 200), "Right shell", (110, 70)),
        (ctr("display"), "4.0 in touchscreen", (-110, -40)),
        (ctr("camera"), "OV2640 camera", (120, -60)),
        (ctr("esp32"), "ESP32-S3-N16R8", (40, -110)),
        (ctr("battery"), "Li-ion 4400 mAh", (130, 30)),
        (ctr("charger"), "Charger #6106 + USB-C", (-120, 40)),
        (ctr("button"), "Power button", (-90, -40)),
        ((scr["x"], 125, scr["z"]), "6 × M2 × 12 screws", (90, -45)),
    ])
    print("• LEFT interior with modules and routes")
    s = Scene()
    s.add(load("LEFT_WHITE"), C_WHITE)
    s.add(load("LEFT_BLUE"), C_BLUE)
    modules(s, man)
    for k in man["routes"]:
        s.add(load(f"route_{k}"), C_ORANGE, edges=False, tol=0.3)
    s.render(IMG / "arc22_left_interior.png", az=90, el=8, size=(1300, 1300))
    print("• reserved fields")
    s = Scene()
    s.add(load("LEFT_WHITE"), C_WHITE)
    s.add(load("_features").intersect(cq.Solid.makeBox(400, 200, 400, cq.Vector(-100, -200, -100))),
          (0.35, 0.75, 0.95))
    modules(s, man, fields=True)
    s.render(IMG / "arc22_fields.png", az=90, el=8, size=(1300, 1300))
    print("• sections")
    section(IMG / "arc22_section_esp32.png", "Section Y = −40 mm (through the plugged ESP32 header rows, looking from +Y)",
            y=-40.0)
    section(IMG / "arc22_section_seam.png", "Section Y = −1 mm (display, camera, battery, charger)", y=-1.0)
    section(IMG / "arc22_section_display.png", "Section X = 12 mm (just behind the display PCB)", x=12.0)
    fs = HERE / "out" / "fit_samples"
    if fs.exists():
        print("• fit samples")
        s = Scene()
        for i, f in enumerate(sorted(fs.glob("*.stl"))):
            m = trimesh.load(f)
            v = m.vertices - m.bounds[0] + np.array([i * 175.0, 0, 0])
            s.add_mesh(v, m.faces, C_WHITE if i != 1 else (0.97, 0.97, 0.97))
        s.render(IMG / "fit_samples.png", az=-60, el=35, size=(1500, 800))
    _ = p
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
