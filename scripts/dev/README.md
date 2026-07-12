# Developer Scripts

- `preflight.py`: checks local install/build prerequisites without modifying files.
- `windows/build_windows.ps1`: Windows folder build plus optional Inno Setup installer.
- `macos/build_macos.sh`: macOS folder build plus optional DMG.
- `linux/build_linux.sh`: Linux folder build plus optional AppImage.

Beta 1.0 packaging uses `packaging/pyinstaller/Lumeward.spec` as the single PyInstaller source of truth.

Install packaging dependencies with:

```powershell
.\venv_win\Scripts\python.exe -m pip install uv
.\venv_win\Scripts\python.exe -m uv pip sync --torch-backend cpu requirements-packaging.lock.txt
```

Edit `requirements-packaging.in` for direct packaging dependency changes, then
regenerate `requirements-packaging.lock.txt` with `uv pip compile --universal --no-strip-markers --torch-backend cpu`.
- `windows/ollama_server_open_firewall.ps1`: Open firewall for Ollama host access.
- `windows/ollama_server_close_firewall.ps1`: Close firewall rule for Ollama host access.
