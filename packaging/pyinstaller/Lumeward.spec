# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None
root = Path(SPECPATH).resolve().parents[1]
crewai_datas = collect_data_files("crewai", includes=["translations/*.json"])
litellm_datas = collect_data_files("litellm", includes=["*.json", "**/*.json"])
tiktoken_hiddenimports = collect_submodules("tiktoken_ext")


a = Analysis(
    [str(root / "backend" / "desktop" / "main.py")],
    pathex=[str(root)],
    binaries=[],
    datas=crewai_datas + litellm_datas,
    hiddenimports=[
        "crewai",
        "ddgs",
        "fastapi",
        "keyring",
        "litellm",
        "argon2",
        "argon2.low_level",
        "passlib.handlers.argon2",
        "qasync",
        "qdrant_client",
        "sentence_transformers",
        "starlette",
        "trafilatura",
        "uvicorn",
    ] + tiktoken_hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Lumeward",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name="Lumeward",
)
