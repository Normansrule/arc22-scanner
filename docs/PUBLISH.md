# Publish — repository, website, apps and manufacturing package

Copy-paste blocks for a **fresh** Ubuntu terminal (also Ubuntu under Windows Subsystem for Linux, WSL). Each block is safe to paste again. Put `arc22-scanner.zip` in your Downloads folder first.

| Form | Where it lives | How it is made |
|---|---|---|
| **Website** — build guide | `https://<you>.github.io/arc22-scanner/` | GitHub Pages from `/docs` |
| **Web app** — ARC-22 Studio, installable from the browser | `https://<you>.github.io/arc22-scanner/app/` | the same Pages site (`docs/app`) |
| **Desktop app** — ARC-22 Studio for Windows, macOS, Linux | the repository's **Releases** page | `release` workflow, on a version tag |
| **Manufacturing ZIP** — print files, STEP, BOM, pin-by-pin wiring, harness, build docs | the repository's **Releases** page | `release` workflow, on a version tag |

## 1 · Publish or update the repository

Puts the ZIP in its **own** folder `~/arc22-scanner` (never in your home folder itself), commits, creates the public repository if needed, pushes `main`, turns on Pages, and prints the URLs. Re-running it with a newer `arc22-scanner.zip` updates the files and commits the changes; your untracked local files (for example `measurements/my_units.toml`) are kept. It looks for the ZIP in `~/Downloads`, then in the Windows Downloads folder.

```bash
(
set -e
# 1) Install git, unzip, rsync, curl and the GitHub CLI (gh); if this Ubuntu has no 'gh' package, add GitHub's official apt repository
sudo apt-get update -y && sudo apt-get install -y git unzip rsync curl ca-certificates && { sudo apt-get install -y gh || { sudo mkdir -p -m 755 /etc/apt/keyrings && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg >/dev/null && sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list >/dev/null && sudo apt-get update -y && sudo apt-get install -y gh; }; }
# 2) Find the newest arc22-scanner.zip: ~/Downloads first, then the Windows Downloads folder (WSL)
ZIP="$(ls -t "$HOME"/Downloads/arc22-scanner.zip /mnt/c/Users/*/Downloads/arc22-scanner.zip 2>/dev/null | head -n1)"; [ -f "$ZIP" ] || { echo "arc22-scanner.zip not found in ~/Downloads or the Windows Downloads folder"; exit 1; }; echo "Using $ZIP"
# 3) Sign in to GitHub once (interactive: a browser code). The 'workflow' scope lets you push .github/workflows
gh auth status -h github.com >/dev/null 2>&1 || gh auth login -h github.com -p https -w -s workflow
# 4) Make sure the login has the 'workflow' scope, and let git use gh's credentials for https://github.com
gh auth status -h github.com 2>&1 | grep -q "workflow" || gh auth refresh -h github.com -s workflow; gh auth setup-git
# 5) Unpack to a temporary folder, then copy into ~/arc22-scanner (new files added, changed files updated, .git kept)
TMP="$(mktemp -d)"; unzip -q "$ZIP" -d "$TMP"; mkdir -p "$HOME/arc22-scanner"; rsync -a --exclude .git "$TMP/arc22-scanner/" "$HOME/arc22-scanner/"; rm -rf "$TMP"; cd "$HOME/arc22-scanner"
# 6) Start the repository in THIS folder on branch main (first time only)
[ -d .git ] || git init -q -b main
# 7) Commit as your GitHub account (repo-local identity, only if none is set) and put your username into every repository link
LOGIN="$(gh api user --jq .login)"; GID="$(gh api user --jq .id)"; git config user.name >/dev/null || git config user.name "$(gh api user --jq '.name // .login')"; git config user.email >/dev/null || git config user.email "$GID+$LOGIN@users.noreply.github.com"; grep -rlI --exclude-dir=.git --exclude-dir=node_modules --exclude=PUBLISH.md "github.com/OWNER/" . | xargs -r sed -i "s#github.com/OWNER/#github.com/$LOGIN/#g"
# 8) Stage everything and commit (skipped when nothing changed)
git add -A && { git diff --cached --quiet && echo "Nothing new to commit" || git commit -q -m "ARC-22: import $(date +%F) from arc22-scanner.zip"; }
# 9) Create the public GitHub repository once and connect it as origin
gh repo view "$LOGIN/arc22-scanner" >/dev/null 2>&1 || gh repo create "$LOGIN/arc22-scanner" --public --description "ARC-22: open-source Subnautica-style handheld scanner: printable two-colour shells, BOM, pin-by-pin wiring, ESP32-S3 on-device object detection, web + desktop app"; git remote get-url origin >/dev/null 2>&1 || git remote add origin "https://github.com/$LOGIN/arc22-scanner.git"
# 10) Push main
git push -u origin main
# 11) Turn on GitHub Pages from /docs on main (or update it if it already exists)
gh api -X POST "repos/$LOGIN/arc22-scanner/pages" -f "source[branch]=main" -f "source[path]=/docs" >/dev/null 2>&1 || gh api -X PUT "repos/$LOGIN/arc22-scanner/pages" -f "source[branch]=main" -f "source[path]=/docs" >/dev/null
# 12) Print where everything lives (the first Pages build takes a minute or two)
PAGES="$(gh api "repos/$LOGIN/arc22-scanner/pages" --jq .html_url)"; echo; echo "Repository:  https://github.com/$LOGIN/arc22-scanner"; echo "Build guide: $PAGES"; echo "Web app:     ${PAGES%/}/app/"; echo "Releases:    https://github.com/$LOGIN/arc22-scanner/releases (manufacturing ZIP + desktop app, after block 3)"
)
```

## 2 · Set up your machine to keep building (once)

See [DEVELOP.md](DEVELOP.md) — Python environment for the CAD pipeline, Node.js 22 for the desktop app, and the ESP-IDF 5.4.2 firmware toolchain.

## 3 · Release the manufacturing ZIP and desktop app

A version tag makes GitHub Actions build `arc22-manufacturing-<version>.zip` and the desktop installers (on real Windows, macOS and Linux machines) and attach them, with the source ZIP, SBOM and checksums, to a new Release. Bump the number each time.

```bash
(
set -e
# 1) Go to the repository and make sure everything is committed and pushed
cd "$HOME/arc22-scanner" && git add -A && { git diff --cached --quiet || git commit -q -m "Prepare release"; } && git push
# 2) Pick the next version: v0.1.0 the first time, then v0.1.1, v0.2.0 ...
VERSION="v0.1.0"
# 3) Tag and push the tag — this starts the 'release' workflow
git tag -a "$VERSION" -m "ARC-22 $VERSION" && git push origin "$VERSION"
# 4) Follow the build live; the installers appear on the Releases page when it finishes (~10 min)
sleep 5; gh run watch "$(gh run list --workflow release.yml --limit 1 --json databaseId --jq '.[0].databaseId')" --exit-status; gh release view "$VERSION" --web || true
)
```

The installers are **not code-signed**. Windows SmartScreen shows "Windows protected your PC" → *More info* → *Run anyway*; on macOS right-click the app → *Open* the first time ([APP.md](APP.md)).

## After publishing
- **Actions** tab: `ci` (CAD pipeline, static checks, web-app data, desktop package), `firmware` (*Run workflow* for a real build log), `codeql`.
- **Settings → Code security**: turn on Dependabot alerts.
- Two GitHub accounts? `gh auth status` shows which one block 1 publishes as; `gh auth switch` changes it before you paste.
