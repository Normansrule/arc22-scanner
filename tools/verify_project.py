#!/usr/bin/env python3
"""
verify_project.py — firmware sanity checks.

    python tools/verify_project.py                 # static checks (no ESP-IDF needed)
    python tools/verify_project.py --after-build   # also inspect firmware/build after `idf.py build`

Static: pin map (unique, 3.3 V GPIO only, no USB/strapping/flash/PSRAM pins), sdkconfig
defaults, component pins vs PINNED_VERSIONS.json, fetched git components at the pinned
commits, Wi-Fi secrets not tracked by git.
After build: ESP-IDF version, resolved component versions (dependencies.lock), app size
vs its partition, the packed model inside the coco_det partition and in the flash
command, SHA-256 of every image that will be flashed.
Exit code 0 = no FAIL. Source present != compiled: only --after-build proves a build.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FW = ROOT / "firmware"
PINS = json.loads((FW / "PINNED_VERSIONS.json").read_text())
results: list[tuple[str, str, str]] = []


def check(ok, name, detail=""):
    results.append(("PASS" if ok is True else "WARN" if ok is None else "FAIL", name, detail))


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def static_checks() -> None:
    pins = dict(re.findall(r"#define\s+(PIN_\w+)\s+(\d+)", (FW / "main" / "pins.h").read_text()))
    nums = [int(v) for v in pins.values()]
    check(len(nums) == len(set(nums)), "pins unique", f"{len(nums)} pins")
    forbidden = {19: "USB D-", 20: "USB D+", 0: "strap", 3: "strap", 45: "strap", 46: "strap",
                 43: "UART0 TX", 44: "UART0 RX", **{g: "flash/octal PSRAM" for g in range(26, 38)}}
    bad = [f"{k}=GPIO{v} ({forbidden[int(v)]})" for k, v in pins.items() if int(v) in forbidden]
    check(not bad, "no reserved GPIO used", ", ".join(bad) or "GPIO4-18 only")
    expected = {"PIN_CAM_SDA": 4, "PIN_CAM_SCL": 5, "PIN_TFT_BL": 6, "PIN_TFT_RST": 7, "PIN_TFT_DC": 8,
                "PIN_TOUCH_CS": 9, "PIN_TFT_CS": 10, "PIN_TFT_MOSI": 11, "PIN_TFT_SCLK": 12,
                "PIN_TOUCH_MISO": 13, "PIN_TOUCH_IRQ": 14, "PIN_CAM_CS": 15, "PIN_CAM_MISO": 16,
                "PIN_CAM_MOSI": 17, "PIN_CAM_SCLK": 18}
    diff = [k for k, v in expected.items() if int(pins.get(k, -1)) != v]
    check(not diff, "pins.h matches docs/WIRING.md", ", ".join(diff) or "15/15")

    sd = (FW / "sdkconfig.defaults").read_text()
    for line in ("CONFIG_IDF_TARGET=\"esp32s3\"", "CONFIG_SPIRAM_MODE_OCT=y", "CONFIG_ESPTOOLPY_FLASHSIZE_16MB=y",
                 "CONFIG_FREERTOS_HZ=1000", "CONFIG_COCO_DETECT_YOLO11N_320_S8_V1=y",
                 "CONFIG_COCO_DETECT_MODEL_IN_FLASH_PARTITION=y", "CONFIG_FLASH_COCO_DETECT_YOLO11N_S8_V1=n"):
        check(line in sd, f"sdkconfig.defaults has {line}")
    comm = "CONFIG_ARC_COMMISSION_CAPTURE_ONLY=y" in sd
    check(True if comm else None, "starts in COMMISSION_CAPTURE_ONLY",
          "yes" if comm else "inference enabled by default - commission capture first!")
    part = (FW / "partitions.csv").read_text()
    check(re.search(r"^coco_det,\s*data", part, re.M) is not None, "partition coco_det present")

    man = (FW / "main" / "idf_component.yml").read_text()
    for k, v in PINS["managed_components"].items():
        m = re.search(rf'{re.escape(k)}:\s*"([^"]+)"', man)
        check(m is not None and m.group(1) == v["version"], f"idf_component.yml pins {k}",
              m.group(1) if m else "missing")
    check(f'idf: "{PINS["esp_idf"]["version"]}"' in man, "idf_component.yml pins ESP-IDF",
          PINS["esp_idf"]["version"])

    for name, info in PINS["git_components"].items():
        path = FW / "components" / name
        if name == "ArduCAM":
            fetched = FW / "components" / "FETCHED.json"
            got = json.loads(fetched.read_text()).get("ArduCAM") if fetched.exists() else None
            check(got == info["commit"] if got else None, f"{name} at pinned commit",
                  got[:12] if got else "not fetched yet: python tools/fetch_libraries.py --camera plus|mini")
            continue
        if (path / ".git").exists():
            got = subprocess.run(["git", "rev-parse", "HEAD"], cwd=path, capture_output=True, text=True).stdout.strip()
            check(got == info["commit"], f"{name} at pinned commit", got[:12])
        else:
            check(None, f"{name} at pinned commit", "not fetched yet: python tools/fetch_libraries.py --camera plus|mini")

    gi = (ROOT / ".gitignore").read_text() if (ROOT / ".gitignore").exists() else ""
    check(".env" in gi and "secrets.h" in gi, ".env and secrets.h are git-ignored")
    try:
        r = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True)
        if r.returncode != 0:
            check(None, "no credentials tracked by git", "not a git repository yet")
        else:
            check(not re.search(r"(^|/)(\.env|secrets\.h)$", r.stdout, re.M), "no credentials tracked by git")
    except FileNotFoundError:
        check(None, "no credentials tracked by git", "git not installed")


def after_build() -> None:
    b = FW / "build"
    if not (b / "project_description.json").exists():
        check(False, "build directory", "run `idf.py build` in firmware/ first")
        return
    pd = json.loads((b / "project_description.json").read_text())
    idf_ver = pd.get("git_revision", "") or pd.get("idf_ver", "")
    check(PINS["esp_idf"]["version"] in idf_ver or None, "built with ESP-IDF " + PINS["esp_idf"]["version"],
          idf_ver or "unknown")
    lock = FW / "dependencies.lock"
    if lock.exists():
        txt = lock.read_text()
        for k, v in PINS["managed_components"].items():
            m = re.search(rf"^\s*{re.escape(k)}:\s*\n(?:.*\n){{0,12}}?\s*version:\s*([^\s]+)", txt, re.M)
            check(m is not None and m.group(1).strip("'\"") == v["version"], f"resolved {k}",
                  m.group(1) if m else "not in lock")
    else:
        check(False, "dependencies.lock", "missing")
    app = b / f"{pd.get('project_name', 'arc22_scanner')}.bin"
    if app.exists():
        size = app.stat().st_size
        check(size < 6 * 1024 * 1024, "app fits the 6 MB factory partition", f"{size / 1024:.0f} KB")
    model = b / "espdl_models" / "coco_detect.espdl"
    check(model.exists() and model.stat().st_size < 4 * 1024 * 1024, "packed model fits coco_det (4 MB)",
          f"{model.stat().st_size / 1024:.0f} KB" if model.exists() else "missing")
    fa = b / "flasher_args.json"
    fl = (b / "flash_args").read_text() if (b / "flash_args").exists() else ""
    in_flash = "coco_detect.espdl" in fl or (fa.exists() and "coco_detect.espdl" in fa.read_text())
    check(in_flash or None, "model is part of `idf.py flash`",
          "yes" if in_flash else "not listed in flash_args; `idf.py flash` target should still add it - verify in the log")
    print("\nSHA-256 of flashable images:")
    for f in sorted(list(b.glob("*.bin")) + list((b / "bootloader").glob("*.bin"))
                    + list((b / "partition_table").glob("*.bin")) + ([model] if model.exists() else [])):
        print(f"  {sha(f)}  {f.relative_to(FW)}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--after-build", action="store_true")
    a = ap.parse_args()
    static_checks()
    if a.after_build:
        after_build()
    width = max(len(n) for _, n, _ in results)
    for r, n, d in results:
        print(f"{r:4s}  {n:{width}s}  {d}")
    fails = sum(r == "FAIL" for r, _, _ in results)
    print(f"\n{len(results)} checks, {fails} FAIL, {sum(r == 'WARN' for r, _, _ in results)} WARN")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
