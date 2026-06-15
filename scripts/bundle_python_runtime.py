"""
Bundle Python 3.11 embed + pip + app dependencies for the Windows installer.
Output: installer/runtime/python/  (shipped inside setup.exe)
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = ROOT / "installer" / "runtime" / "python"
CACHE_DIR = ROOT / "installer" / "cache"
PYTHON_VERSION = "3.11.9"
EMBED_NAME = f"python-{PYTHON_VERSION}-embed-amd64.zip"
EMBED_URL = f"https://www.python.org/ftp/python/{PYTHON_VERSION}/{EMBED_NAME}"
GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"
PTH_NAME = "python311._pth"
MARKER = RUNTIME_DIR / ".bundled-ok"


def run(cmd: list[str], *, cwd: Path | None = None) -> None:
    print(">", " ".join(cmd))
    subprocess.run(cmd, cwd=str(cwd or ROOT), check=True)


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        print(f"Using cached {dest.name}")
        return
    print(f"Downloading {url}")
    urllib.request.urlretrieve(url, dest)


def configure_embed(runtime_dir: Path) -> None:
    site_packages = runtime_dir / "Lib" / "site-packages"
    site_packages.mkdir(parents=True, exist_ok=True)
    pth = runtime_dir / PTH_NAME
    pth.write_text(
        "python311.zip\n.\nLib\\site-packages\n\nimport site\n",
        encoding="utf-8",
    )


def main() -> int:
    if MARKER.exists() and (RUNTIME_DIR / "python.exe").exists():
        try:
            run([str(RUNTIME_DIR / "python.exe"), "-c", "import uvicorn, sklearn"])
            print("Bundled runtime already ready.")
            return 0
        except subprocess.CalledProcessError:
            print("Existing bundle incomplete, rebuilding...")
            if MARKER.exists():
                MARKER.unlink(missing_ok=True)

    if RUNTIME_DIR.exists():
        shutil.rmtree(RUNTIME_DIR)
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

    embed_zip = CACHE_DIR / EMBED_NAME
    download(EMBED_URL, embed_zip)
    with zipfile.ZipFile(embed_zip, "r") as archive:
        archive.extractall(RUNTIME_DIR)

    configure_embed(RUNTIME_DIR)
    python_exe = RUNTIME_DIR / "python.exe"
    if not python_exe.exists():
        raise SystemExit(f"Missing {python_exe}")

    get_pip = CACHE_DIR / "get-pip.py"
    download(GET_PIP_URL, get_pip)
    run([str(python_exe), str(get_pip), "--no-warn-script-location"])

    requirements = ROOT / "requirements.txt"
    run(
        [
            str(python_exe),
            "-m",
            "pip",
            "install",
            "-r",
            str(requirements),
            "--no-warn-script-location",
            "--disable-pip-version-check",
        ]
    )

    run([str(python_exe), "-c", "import uvicorn, sklearn, fastapi"])
    cleanup_runtime(runtime_dir)
    MARKER.write_text(f"python={PYTHON_VERSION}\n", encoding="utf-8")
    print(f"Bundled runtime ready: {RUNTIME_DIR}")
    return 0


def cleanup_runtime(runtime_dir: Path) -> None:
    """Remove caches and test folders to shrink the installer."""
    site_packages = runtime_dir / "Lib" / "site-packages"
    for pattern in ("__pycache__", "tests", "test"):
        for path in site_packages.rglob(pattern):
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
    for path in site_packages.rglob("*.pyc"):
        path.unlink(missing_ok=True)
    for path in site_packages.rglob("*.pyo"):
        path.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
