# ARC-22 firmware (ESP-IDF 5.4.2 + Arduino-ESP32 3.2.1 component)

Full instructions: [../docs/FIRMWARE.md](../docs/FIRMWARE.md). Short version, from the repository root:

```bash
python tools/fetch_libraries.py --camera plus     # or --camera mini
cd firmware && idf.py set-target esp32s3 && idf.py build
cd .. && python tools/verify_project.py --after-build
cd firmware && idf.py -p PORT flash monitor
```

The default build is **commissioning only** (display, touch, camera). Not yet compiled or hardware-tested — get a real build log first (`firmware` workflow in GitHub Actions).
