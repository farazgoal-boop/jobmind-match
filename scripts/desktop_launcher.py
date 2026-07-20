"""
JobMind Match desktop launcher.
Opens the app in a clean window (Edge/Chrome app mode). No CMD.
"""
from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import threading
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
        ctypes.windll.user32.MessageBoxW(0, message, "JobMind Match", 0x40)
    except Exception:
        pass


def show_info_async(message: str) -> None:
    """Win32 MessageBox blocks the calling thread until dismissed. Showing
    the 'please wait' hint this way used to stall the whole launcher —
    server polling and opening the app window — on whether a user noticed
    and clicked OK on a small dialog that can appear behind other windows.
    Run it on its own thread so it's purely informational and never blocks
    startup; close_starting_dialog() dismisses it once the app is ready."""
    threading.Thread(target=show_info, args=(message,), daemon=True).start()


def close_starting_dialog() -> None:
    try:
        WM_CLOSE = 0x0010
        user32 = ctypes.windll.user32

        @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        def _enum_cb(hwnd, _lparam):
            length = user32.GetWindowTextLengthW(hwnd)
            if length:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                if buf.value == "JobMind Match":
                    pid = ctypes.c_ulong()
                    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    if pid.value == os.getpid():
                        user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
            return True

        user32.EnumWindows(_enum_cb, 0)
    except Exception:
        pass


def show_error(message: str) -> None:
    try:
        ctypes.windll.user32.MessageBoxW(0, message, "JobMind Match", 0x10)
    except Exception:
        pass


def browser_profile_dir() -> Path:
    # Chromium is single-instance per user-data-dir: if the user's regular
    # Edge/Chrome is already running (very common — "continue running
    # background apps" is on by default), a second `--app=` launch just
    # forwards the request via IPC to that existing instance and silently
    # DROPS every command-line flag we passed, including the occlusion-
    # tracking fix below. A dedicated profile dir forces a genuinely
    # separate instance so our flags are always honored.
    base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    profile = base / "JobMindMatch" / "AppWindowProfile"
    profile.mkdir(parents=True, exist_ok=True)
    return profile


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
                    f"--user-data-dir={browser_profile_dir()}",
                    # Chromium's Native Window Occlusion Tracking throttles/
                    # repaints windows it thinks are covered, and has a known
                    # bug where an --app= window comes back solid black after
                    # being minimized and restored instead of repainting.
                    # These flags turn that tracking off for this window.
                    "--disable-features=CalculateNativeWinOcclusion",
                    "--disable-backgrounding-occluded-windows",
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
        show_info_async(
            "JobMind Match is starting.\n\n"
            "First launch may take 1–2 minutes. Please wait…"
        )

    ready = wait_server(timeout=240)
    close_starting_dialog()
    if not ready:
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
