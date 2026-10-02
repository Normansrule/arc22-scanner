#!/usr/bin/env bash
# Regenerate every CAD output, check, fit sample and render — in the required order.
# Usage: bash scripts/rebuild_all.sh        (run from the repository root)
set -euo pipefail
cd "$(dirname "$0")/.."
python cad/build_arc22.py        # 1. shells, material regions, modules, routes  -> cad/build/
python cad/validate_arc22.py     # 2. recorded CAD checks                        -> docs/validation/
python cad/export_arc22.py       # 3. STEP / OBJ+MTL / STL / 3MF / reference CAD -> cad/out/, cad/reference_cad/
python cad/fit_samples_arc22.py  # 4. print-first fit samples                    -> cad/out/fit_samples/
python cad/render_arc22.py       # 5. documentation images                       -> docs/img/
python tools/build_web_data.py   # 6. ARC-22 Studio data + web meshes            -> docs/app/models, docs/app/data
python tools/build_mfg.py         # 7. BOM, pin-by-pin tables, harness + wiring drawings -> docs/, hardware/harness/
echo "All outputs regenerated. Read docs/validation/cad_checks.md before printing anything."
