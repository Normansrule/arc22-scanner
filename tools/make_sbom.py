#!/usr/bin/env python3
"""
make_sbom.py — write a CycloneDX 1.5 Software Bill of Materials (SBOM) for the repository.

    python tools/make_sbom.py > sbom.cdx.json

Lists every pinned firmware dependency (with commit hashes where known), the detection
model, and the Python packages of the CAD pipeline. Standard library only.
"""
from __future__ import annotations

import datetime
import json
import pathlib
import re
import uuid

ROOT = pathlib.Path(__file__).resolve().parent.parent
PINS = json.loads((ROOT / "firmware" / "PINNED_VERSIONS.json").read_text())


def comp(name, version, purl, kind="library", commit=None, note=None):
    c = {"type": kind, "name": name, "version": version, "purl": purl}
    if commit:
        c["properties"] = [{"name": "git:commit", "value": commit}]
    if note:
        c.setdefault("properties", []).append({"name": "note", "value": note})
    return c


def main() -> None:
    comps = [comp("esp-idf", PINS["esp_idf"]["version"], f"pkg:github/espressif/esp-idf@{PINS['esp_idf']['tag']}",
                  "framework", PINS["esp_idf"]["commit"])]
    for k, v in PINS["managed_components"].items():
        ns, n = k.split("/")
        comps.append(comp(n, v["version"], f"pkg:generic/{ns}/{n}@{v['version']}", commit=v.get("git_tag_commit")))
    for k, v in PINS["git_components"].items():
        repo = v["git"].removeprefix("https://github.com/")
        comps.append(comp(k, v.get("tag", v["commit"][:7]), f"pkg:github/{repo}@{v['commit']}", commit=v["commit"]))
    m = PINS["model"]
    comps.append(comp(m["name"], "coco_detect-0.4.0", "pkg:generic/espressif/coco_detect_yolo11n_320_s8_v1@0.4.0",
                      "machine-learning-model", note=f"{m['classes']} COCO classes, input {m['input']}"))
    for line in (ROOT / "cad" / "requirements.txt").read_text().splitlines():
        mm = re.match(r"^([A-Za-z0-9_.\-]+)==([^\s#]+)", line.strip())
        if mm:
            comps.append(comp(mm.group(1), mm.group(2), f"pkg:pypi/{mm.group(1).lower()}@{mm.group(2)}"))
    lock = json.loads((ROOT / "app" / "package-lock.json").read_text())
    for name in ("electron", "electron-builder"):
        meta = lock["packages"].get(f"node_modules/{name}", {})
        if meta:
            comps.append(comp(name, meta["version"], f"pkg:npm/{name}@{meta['version']}",
                              note="desktop app build (app/package-lock.json pins every transitive package)"))
    for name, ver, purl in (("three", "0.186.1", "pkg:npm/three@0.186.1"),
                            ("@fontsource/chakra-petch", "5.3.0", "pkg:npm/%40fontsource/chakra-petch@5.3.0"),
                            ("@fontsource/atkinson-hyperlegible", "5.3.0",
                             "pkg:npm/%40fontsource/atkinson-hyperlegible@5.3.0")):
        comps.append(comp(name, ver, purl, note="vendored in docs/app/lib"))
    bom = {"bomFormat": "CycloneDX", "specVersion": "1.5", "serialNumber": f"urn:uuid:{uuid.uuid4()}", "version": 1,
           "metadata": {"timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                        "component": {"type": "device", "name": "arc22-scanner", "version": "0.1.0"}},
           "components": comps}
    print(json.dumps(bom, indent=2))


if __name__ == "__main__":
    main()
