"""
JobMind Match desktop launcher.
Opens the app in a clean window (Edge/Chrome app mode). No CMD.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from datetime import datetime
from pathlib import Path

CREATE_NO_WINDOW = 0x08000000
DASHBOARD_URL = "http://127.0.0.1:8000/dashboard"


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parents[1]


def log_path(root: Path) -> Path:
    return root / "jobmind-launcher.log"


def log(root: Path, message: str) -> None:
    try:
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with log_path(root).open("a", encoding="utf-8") as handle:
            handle.write(f"[{stamp}] {message}\n")
    except OSError:
        pass


def python_path(root: Path) -> Path:
    bundled = root / "runtime" / "python" / "python.exe"
    if bundled.exists():
        return bundled
    return root / ".venv" / "Scripts" / "python.exe"


def server_up() -> bool:
    try:
        with urllib.request.urlopen(DASHBOARD_URL, timeout=2) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def server_listen_addresses() -> set[str]:
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | "
                "Select-Object -ExpandProperty LocalAddress",
            ],
            capture_output=True,
            text=True,
            creationflags=CREATE_NO_WINDOW,
            timeout=12,
            check=False,
        )
        return {line.strip() for line in result.stdout.splitlines() if line.strip()}
    except (OSError, subprocess.TimeoutExpired):
        return set()


def server_allows_lan() -> bool:
    addrs = server_listen_addresses()
    return bool(addrs & {"0.0.0.0", "::", "*"})


def start_server(root: Path) -> None:
    if server_up() and not server_allows_lan():
        log(root, "Restarting server for mobile LAN (was localhost-only)")
        stop_server()
        time.sleep(2)

    if server_up():
        return
    python_bin = python_path(root)
    if not python_bin.exists():
        raise FileNotFoundError(f"Missing virtual environment: {python_bin}")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(root)

    subprocess.Popen(
        [
            str(python_bin),
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
            "--log-level",
            "warning",
        ],
        cwd=str(root),
        env=env,
        creationflags=CREATE_NO_WINDOW,
    )


def wait_server(timeout: int = 180) -> bool:
    for _ in range(timeout):
        if server_up():
            return True
        time.sleep(1)
    return False


def stop_server() -> None:
    cmd = (
        "Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | "
        "ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", cmd],
        creationflags=CREATE_NO_WINDOW,
        check=False,
    )


def show_info(message: str) -> None:
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(0, message, "JobMind Match", 0x40)
    except Exception:
        pass


def show_error(message: str) -> None:
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(0, message, "JobMind Match", 0x10)
    except Exception:
        pass


def browser_app_paths() -> list[Path]:
    program_files = os.environ.get("PROGRAMFILES", r"C:\Program Files")
    program_files_x86 = os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")
    return [
        Path(program_files_x86) / "Microsoft/Edge/Application/msedge.exe",
        Path(program_files) / "Microsoft/Edge/Application/msedge.exe",
        Path(program_files_x86) / "Google/Chrome/Application/chrome.exe",
        Path(program_files) / "Google/Chrome/Application/chrome.exe",
    ]


def open_app_window(root: Path) -> bool:
    for browser in browser_app_paths():
        if not browser.exists():
            continue
        try:
            subprocess.Popen(
                [
                    str(browser),
                    f"--app={DASHBOARD_URL}",
                    "--window-size=1440,900",
                    "--start-maximized",
                ],
                cwd=str(root),
                creationflags=CREATE_NO_WINDOW,
            )
            log(root, f"Opened app window via {browser.name}")
            return True
        except OSError as exc:
            log(root, f"Failed browser launch {browser}: {exc}")

    try:
        webbrowser.open(DASHBOARD_URL)
        log(root, "Opened dashboard in default browser")
        return True
    except Exception as exc:
        log(root, f"Default browser failed: {exc}")
        return False


def main() -> int:
    root = app_root()
    log(root, "Launcher started")

    if len(sys.argv) > 1 and sys.argv[1] == "--quit":
        stop_server()
        log(root, "Launcher quit")
        return 0

    if not python_path(root).exists():
        log(root, "Python runtime missing")
        show_error(
            "JobMind Match is not fully installed.\n\n"
            "Please run the setup installer again."
        )
        return 1

    try:
        start_server(root)
        log(root, "Server start requested")
    except FileNotFoundError:
        log(root, "Server start failed: runtime missing")
        show_error(
            "JobMind Match is not fully installed.\n\n"
            "Please run the setup installer again."
        )
        return 1

    if not server_up():
        show_info(
            "JobMind Match is starting.\n\n"
            "First launch may take 1–2 minutes. Please wait…"
        )

    if not wait_server(timeout=240):
        log(root, "Server did not become ready")
        show_error(
            "JobMind Match could not start.\n\n"
            "Try: Start Menu → Open JobMind (if app won't start)\n"
            "Or run setup\\OPEN_JOBMIND.bat from the install folder."
        )
        return 1

    if not open_app_window(root):
        log(root, "UI open failed")
        show_error("JobMind Match could not open its window.")
        return 1

    log(root, "Launcher finished successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
