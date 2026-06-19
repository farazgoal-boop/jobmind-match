# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for JobMind Match desktop bundle (onedir)."""
import os
from pathlib import Path

block_cipher = None
ROOT = Path(SPECPATH)

icon_file = os.environ.get("PYINSTALLER_ICON", "").strip()
if icon_file and not Path(icon_file).is_file():
    icon_file = ""

datas = [
    (str(ROOT / "app" / "templates"), "app/templates"),
    (str(ROOT / "app" / "static"), "app/static"),
    (str(ROOT / ".env.example"), "."),
]

hiddenimports = [
    "uvicorn.logging",
    "uvicorn.loops.auto",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan.on",
    "uvicorn.loops.uvloop",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.http.httptools_impl",
    "uvicorn.protocols.websockets.wsproto_impl",
    "uvicorn.protocols.websockets.websockets_impl",
    "sqlmodel",
    "email_validator",
    "apscheduler.schedulers.background",
    "apscheduler.triggers.cron",
    "sklearn.utils._cython_blas",
    "sklearn.neighbors._partition_nodes",
    "sklearn.tree._utils",
    "sklearn.utils._typedefs",
    "sklearn.metrics.pairwise",
    "sklearn.feature_extraction.text",
    "jinja2.ext",
    "multipart",
    "anyio._backends._asyncio",
    "httptools",
    "websockets",
    "watchfiles",
    "uvloop",
    "h11",
    "wsproto",
]

a = Analysis(
    ["desktop_launcher.py"],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="JobMindMatch",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file or None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="JobMindMatch",
)
