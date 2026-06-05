#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"

echo "Starting Lumeward macOS build..."
python -m PyInstaller --noconfirm packaging/pyinstaller/Lumeward.spec
echo "Folder build complete: dist/Lumeward"

if command -v hdiutil >/dev/null 2>&1; then
  mkdir -p dist/installers
  rm -f dist/installers/Lumeward-1.0.0-beta.1.dmg
  hdiutil create -volname "Lumeward" -srcfolder dist/Lumeward -ov -format UDZO dist/installers/Lumeward-1.0.0-beta.1.dmg
  echo "DMG build complete: dist/installers/Lumeward-1.0.0-beta.1.dmg"
else
  echo "hdiutil not found. Skipping DMG; folder build is ready."
fi
