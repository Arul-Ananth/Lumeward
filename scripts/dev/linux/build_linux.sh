#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"

echo "Starting Lumeward Linux build..."
python -m PyInstaller --noconfirm packaging/pyinstaller/Lumeward.spec
echo "Folder build complete: dist/Lumeward"

if command -v appimagetool >/dev/null 2>&1; then
  mkdir -p dist/appimage/Lumeward.AppDir/usr/bin dist/installers
  cp -a dist/Lumeward/. dist/appimage/Lumeward.AppDir/usr/bin/
  cat > dist/appimage/Lumeward.AppDir/AppRun <<'EOF'
#!/usr/bin/env bash
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/bin/Lumeward" "$@"
EOF
  chmod +x dist/appimage/Lumeward.AppDir/AppRun
  cat > dist/appimage/Lumeward.AppDir/Lumeward.desktop <<'EOF'
[Desktop Entry]
Name=Lumeward
Exec=Lumeward
Type=Application
Categories=Utility;
EOF
  appimagetool dist/appimage/Lumeward.AppDir dist/installers/Lumeward-1.0.0-beta.1.AppImage
  echo "AppImage build complete: dist/installers/Lumeward-1.0.0-beta.1.AppImage"
else
  echo "appimagetool not found. Skipping AppImage; folder build is ready."
fi
