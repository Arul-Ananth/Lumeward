# Desktop Runtime

- `backend/desktop/main.py` boots Qt and ensures the local desktop identity.
- `backend/desktop/telemetry_manager.py` coordinates collectors and delegates async work to `backend/desktop/services/telemetry_runtime.py`.
- Local desktop storage uses SQLite and embedded Qdrant. When an Enterprise
  Server URL is configured, generation and explicitly shared context use the
  authenticated server workspace while local UI preferences remain on the device.
- Enterprise HTTP connections use separate connect, ordinary-request and
  generation budgets. Configure them with `ENTERPRISE_CONNECT_TIMEOUT_SECONDS`,
  `ENTERPRISE_REQUEST_TIMEOUT_SECONDS` and
  `ENTERPRISE_GENERATION_TIMEOUT_SECONDS`; generation defaults to five minutes.

## Linux / WSL Setup

Use the repo-level Linux desktop lock file:

```bash
cd /mnt/c/Dev/lumeward
python3 -m venv .venv_linux
source .venv_linux/bin/activate
python -m pip install --upgrade pip setuptools wheel uv
python -m uv pip sync --torch-backend cpu requirements-desktop-linux.lock.txt
python backend/main.py --mode desktop
```

Recommended Debian/Ubuntu packages:

```bash
sudo apt update
sudo apt install -y python3-venv libgl1 libglib2.0-0 libxkbcommon-x11-0 libdbus-1-3 libxcb-cursor0 libxcb-icccm4 libxcb-keysyms1 libxcb-render-util0 libxcb-xinerama0 gnome-keyring libsecret-1-0 libsecret-1-dev dbus-user-session
```

This Linux lock file includes:
- `crewai[google-genai]` for `.env` setups that use `LLM_PROVIDER=google`
- `secretstorage` and `keyrings.alt` to improve Linux keyring reproducibility
