# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path


PROJECT_DIR = Path(SPECPATH)
ASSET_DIR = PROJECT_DIR / "assets"

a = Analysis(
    [str(PROJECT_DIR / "main.py")],
    pathex=[str(PROJECT_DIR)],
    binaries=[],
    datas=[
        (str(ASSET_DIR / "fonts"), "assets/fonts"),
        (str(ASSET_DIR / "images"), "assets/images"),
        (str(ASSET_DIR / "music"), "assets/music"),
        (str(ASSET_DIR / "sounds"), "assets/sounds"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="DEADLAST",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(PROJECT_DIR / "icon.ico"),
)
