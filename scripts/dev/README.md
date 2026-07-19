# Developer Scripts

- `preflight.py`: checks local install/build prerequisites without modifying files.
- `windows/start_server.ps1`: starts the local server with the bundled Qdrant
  directory after validating its executable, configuration and storage path.
- `windows/build_windows.ps1`: Windows folder build plus optional Inno Setup installer.
- `macos/build_macos.sh`: macOS folder build plus optional DMG.
- `linux/build_linux.sh`: Linux folder build plus optional AppImage.

Beta 1.0 packaging uses `packaging/pyinstaller/Lumeward.spec` as the single PyInstaller source of truth.

Local Windows server development:

```powershell
.\scripts\dev\windows\start_server.ps1
```

The default Qdrant directory is `qdrant` at the repository root. Override it
with `-QdrantDirectory D:\path\to\qdrant`. The launcher uses `.venv` when
available and otherwise falls back to `venv_win`; do not activate a different
environment before running it.

Install packaging dependencies with:

```powershell
.\venv_win\Scripts\uv.exe sync --extra packaging
```

Edit `requirements-packaging.in` for direct packaging dependency changes, then
regenerate `requirements-packaging.lock.txt` with `uv pip compile --universal --no-strip-markers --torch-backend cpu`.
- `windows/ollama_server_open_firewall.ps1`: Open firewall for Ollama host access.
- `windows/ollama_server_close_firewall.ps1`: Close firewall rule for Ollama host access.
