from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def setup_project_path() -> Path:
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.append(str(PROJECT_ROOT))
    return PROJECT_ROOT


def use_temp_data_dir() -> tempfile.TemporaryDirectory:
    temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    os.environ["DATA_DIR"] = temp_dir.name
    return temp_dir
