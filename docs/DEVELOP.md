# Develop — keep building ARC-22

Everything here runs in an Ubuntu terminal (native or WSL) inside `~/arc22-scanner`, the folder created by [PUBLISH.md](PUBLISH.md) block 1.

## One-time setup

Installs the Python environment for the CAD pipeline (`.venv`, git-ignored), Node.js 22 for the desktop app (official build, checksum-verified, in `~/.local/node`, no sudo), the libraries Electron needs on Linux/WSL, and the app's pinned npm packages.

```bash
(
set -e
cd "$HOME/arc22-scanner"
# 1) System packages: Python venv support, Graphviz (harness drawings), and the libraries an Electron window needs on Linux/WSL
sudo apt-get update -y && sudo apt-get install -y python3-venv python3-pip curl xz-utils graphviz libnss3 libgbm1 libxss1 libxtst6 && { sudo apt-get install -y libasound2t64 libgtk-3-0t64 2>/dev/null || sudo apt-get install -y libasound2 libgtk-3-0; }
# 2) Python environment for the CAD pipeline, with the pinned versions in cad/requirements.txt
[ -d .venv ] || python3 -m venv .venv; .venv/bin/python -m pip install -q --upgrade pip; .venv/bin/python -m pip install -q -r cad/requirements.txt
# 3) Node.js 22 (Electron needs >= 22.12): keep a recent enough system node, otherwise install the official build after checking its SHA-256
OK="$(node -e 'const [a,b]=process.versions.node.split(".").map(Number);console.log(a>22||(a===22&&b>=12))' 2>/dev/null || echo false)"
if [ "$OK" != true ]; then T="$(mktemp -d)"; curl -fsSL https://nodejs.org/dist/latest-v22.x/SHASUMS256.txt -o "$T/SUMS"; F="$(grep -o 'node-v22[^ ]*-linux-x64.tar.xz' "$T/SUMS" | head -n1)"; curl -fsSL "https://nodejs.org/dist/latest-v22.x/$F" -o "$T/$F"; (cd "$T" && grep " $F\$" SUMS | sha256sum -c -); mkdir -p "$HOME/.local/node"; tar -xJf "$T/$F" -C "$HOME/.local/node" --strip-components=1; rm -rf "$T"; grep -q '.local/node/bin' "$HOME/.bashrc" || echo 'export PATH="$HOME/.local/node/bin:$PATH"' >> "$HOME/.bashrc"; fi; export PATH="$HOME/.local/node/bin:$PATH"; node --version
# 4) Desktop app dependencies exactly as pinned in app/package-lock.json
(cd app && npm ci --no-audit --no-fund)
# 5) Quick check: the firmware static checks run in the new environment
.venv/bin/python tools/verify_project.py | tail -n 2
echo "Setup done. Open a NEW terminal (or run: source ~/.bashrc) so 'node' is on your PATH."
)
```

## Everyday loop

```bash
cd ~/arc22-scanner && source .venv/bin/activate
bash scripts/rebuild_all.sh                 # after changing measurements/my_units.toml or cad/*.py (~3 min)
python -m http.server 8000 -d docs &        # web app at http://localhost:8000/app/  (stop later with: kill %1)
(cd app && npm start)                       # the same app as a desktop window
git add -A && git commit -m "Describe the change" && git push    # Pages updates itself in ~1 min
```

- **Measurements:** enter them in the app (*Measure*), download `my_units.toml` into `measurements/`, run `rebuild_all.sh`. The CAD, checks, print files, renders and the app's data all regenerate from it.
- **Web app code:** `docs/app/` (plain HTML/CSS/JavaScript modules, no build step). Never edit `app/web/` — it is a copy made by `npm start`.
- **Desktop installers locally:** `cd app && npm run dist:linux` → `app/dist/*.deb` (install with `sudo apt install ./app/dist/*.deb`) and an AppImage. Windows and macOS installers come from the `release` workflow ([PUBLISH.md](PUBLISH.md) block 3).

## Firmware (ESP-IDF 5.4.2)

The firmware pins ESP-IDF **5.4.2**. If you already have another version (for example 5.5.x), the easiest route is Espressif's official container, exactly what CI uses — Docker Desktop with WSL integration works:

```bash
cd ~/arc22-scanner && source .venv/bin/activate
python tools/fetch_libraries.py --camera plus            # or --camera mini (read your camera PCB)
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD":/project -w /project/firmware -e HOME=/tmp espressif/idf:v5.4.2 \
  bash -c 'git config --global --add safe.directory "*" && idf.py set-target esp32s3 && idf.py build'
python tools/verify_project.py --after-build
```

Or install 5.4.2 side by side (it does not touch your other ESP-IDF):

```bash
sudo apt-get install -y git wget flex bison gperf cmake ninja-build ccache libffi-dev libssl-dev dfu-util libusb-1.0-0
mkdir -p ~/esp && [ -d ~/esp/esp-idf-v5.4.2 ] || git clone -b v5.4.2 --recursive --depth 1 --shallow-submodules https://github.com/espressif/esp-idf.git ~/esp/esp-idf-v5.4.2
~/esp/esp-idf-v5.4.2/install.sh esp32s3
grep -q get_idf54 ~/.bashrc || echo "alias get_idf54='. \$HOME/esp/esp-idf-v5.4.2/export.sh'" >> ~/.bashrc
# then, in a new terminal:  get_idf54 && cd ~/arc22-scanner/firmware && idf.py set-target esp32s3 && idf.py build
```

**Flashing from WSL:** the ESP32's USB port is a Windows device. Either share it into WSL with `usbipd` (Windows: `usbipd list`, `usbipd bind --busid <id>`, `usbipd attach --wsl --busid <id>`; then `idf.py -p /dev/ttyACM0 flash monitor`), or flash from Windows with the files in `firmware/build/` (`idf.py` prints the exact `esptool` command). Follow the programming sequence in [SAFETY.md](SAFETY.md) first.
