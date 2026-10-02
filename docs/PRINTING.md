# Two-colour printing — Bambu Lab P1S

ARC-22 prints as **exactly two pieces**: the LEFT shell and the RIGHT shell. Each one is white with cyan/blue accent regions that are printed **in the same job** as aligned material regions — not glued-on parts. The machine is a Bambu Lab **P1S** with an Automatic Material System (AMS) or manual filament change (not the A1 mini: its bed is too small).

## Files (in `cad/out/print/`)

| Use | Files | Notes |
|---|---|---|
| **Preferred: aligned STL regions** | `stl/ARC22_LEFT_WHITE.stl` + `stl/ARC22_LEFT_BLUE.stl`, and the same for RIGHT | four **material regions** of two pieces — not four enclosure parts |
| OBJ with colours | `ARC22_LEFT.obj` + `ARC22_LEFT.mtl` (and RIGHT) | keep each OBJ next to its MTL; groups `ARC22_LEFT_WHITE` / `_BLUE` |
| Optional 3MF | `3mf/ARC22_LEFT_2COLOR.3mf` (and RIGHT) | core-spec 3MF, one object with two coloured parts. **Not a validated Bambu Studio project** |
| Editable | `cad/out/step/` | STEP stays in assembly coordinates |

All meshes of one shell share **one** transform (`PRINT_TRANSFORMS.json`): exterior down, open seam up, centred on a 256 mm bed. Footprint 218 × 218 mm; heights 60.6 mm (LEFT, includes the seam lip) and 59.0 mm (RIGHT). The recorded mesh checks are in [docs/validation/mesh_checks.md](validation/mesh_checks.md).

## Import — the safe way (aligned STLs)
1. Bambu Studio → new project → import **both** `ARC22_LEFT_WHITE.stl` and `ARC22_LEFT_BLUE.stl` **at once**. When asked *"Load these files as a single object with multiple parts?"* answer **Yes**.
2. The parts must sit exactly on top of each other. **Never move, drop, scale, rotate or re-arrange an accent part on its own**; transform the whole object only.
3. In the object list assign filament 1 = white PETG to the WHITE part and filament 2 = cyan/blue PETG to the BLUE part — explicitly, part by part.
4. Repeat for RIGHT on a second plate (or a second project).
5. Save the project from **your installed Bambu Studio** and print from that saved project.

**Known past problems — not claimed fixed:** earlier 3MFs imported grey/single-colour and showed *"invalid config, load geometry only"*. The 3MF here is a plain core-spec file built without Bambu's project metadata, so expect to assign filaments yourself. If it misbehaves, use the STL route above. Record what you saw in [VALIDATION.md](VALIDATION.md).

## Starting settings (untested — tune them)
| Setting | Start at |
|---|---|
| Layer height | 0.16–0.20 mm |
| Walls | 4 |
| Top / bottom shells | 5 / 5 |
| Infill | 20–25 % (gyroid or grid) |
| Material | PETG for both colours (same temperatures, good layer bonding at colour boundaries) |
| Plate | textured PEI; glue stick as release agent for PETG on smooth plates |
| Brim | 5 mm if corners lift |
| Supports | tree, **build-plate-only first**; add supports under pad/jaw overhangs only where the preview shows them |
| Prime/purge | prime tower on; flush volumes per Bambu's white↔blue suggestion |

## Orientation and supports
- **Exterior down, open seam up** (already applied in the files). The curved shoulders and the bow sit on supports; the inner ribs, slot blocks, clips and screw bosses grow straight up.
- After slicing, **inspect the sliced toolpaths layer by layer**: colour boundaries in the right place, accent stripe present on both shoulders, the window frame and lens ring blue, no support **inside** a corner slot or a clip that you cannot reach to remove.
- Confirm removal access for every support before printing; a snapped clip is a reprint.

## Bed fit
256 × 256 × 256 mm build volume, but leave room for the prime tower, brim, purge and the printer's exclusion zones. The recorded check allows a 10 mm margin all round (218 ≤ 236). If your slicer refuses, rotate the object in the plate **as one object** — never split or scale it.

## After printing
Remove supports, clear every slot and clip with a flush cutter, check the lip/groove seam closes by hand on the **empty** halves (Stage 3), then fit foam.
