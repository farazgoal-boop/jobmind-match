#!/usr/bin/env python3
"""
JobMind Match cross-platform desktop launcher (PyInstaller entry point).

Starts Uvicorn, opens the dashboard in the default browser, and keeps running
until the console window is closed or Ctrl+C is pressed.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def disable_windows_quickedit() -> None:
    """Windows enables QuickEdit Mode by default on any freshly-spawned
    console window. The moment a user clicks/selects text in it — including
    the click that can happen while restoring a minimized window — QuickEdit
    pauses the console buffer, which blocks any thread mid-write to stdout.
    Since the server thread logs through that same console, one accidental
    click freezes the entire app (server included) until the selection is
    cancelled. Dev runs happen inside an already-running terminal (VS Code,
    Windows Terminal) where this is usually off already, which is why this
    only shows up in the packaged .exe's own console window.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        STD_INPUT_HANDLE = -10
        ENABLE_EXTENDED_FLAGS = 0x0080
        ENABLE_QUICK_EDIT_MODE = 0x0040

        handle = kernel32.GetStdHandle(STD_INPUT_HANDLE)
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return
        new_mode = (mode.value & ~ENABLE_QUICK_EDIT_MODE) | ENABLE_EXTENDED_FLAGS
        kernel32.SetConsoleMode(handle, new_mode)
    except Exception:
        pass


def bundle_root() -> Path:
    if is_frozen():
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def user_data_dir() -> Path:
    path = Path.home() / ".jobmind-match"
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_user_env(data_dir: Path, root: Path) -> None:
    env_path = data_dir / ".env"
    if env_path.exists():
        return
    example = root / ".env.example"
    if example.exists():
        shutil.copy2(example, env_path)


def configure_environment(port: int) -> str:
    root = bundle_root()
    data_dir = user_data_dir()

    os.environ.setdefault("JOBMIND_APP_ROOT", str(root))

    if is_frozen():
        os.environ["JOBMIND_APP_ROOT"] = str(root)
        os.environ["DATABASE_URL"] = f"sqlite:///{(data_dir / 'jobmind.db').as_posix()}"
        os.environ.setdefault("APP_ENV", "desktop")

    ensure_user_env(data_dir, root)

    from dotenv import load_dotenv

    load_dotenv(data_dir / ".env", override=False)

    if is_frozen():
        os.environ["DATABASE_URL"] = f"sqlite:///{(data_dir / 'jobmind.db').as_posix()}"

    return f"http://127.0.0.1:{port}"


def wait_for_server(base_url: str, timeout: float = 90.0) -> bool:
    deadline = time.time() + timeout
    probe = f"{base_url.rstrip('/')}/dashboard"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(probe, timeout=2) as response:
                if response.status == 200:
                    return True
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(0.25)
    return False


def run_uvicorn(port: int) -> None:
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=port,
        log_level="info",
        # Per-request access lines flood the console during a busy session
        # (e.g. lead hunting), growing the scrollback fast enough that a
        # restore-from-minimize redraw can itself stall for a noticeable
        # moment. Real errors still surface via the "warning"+ app loggers.
        access_log=False,
    )


def main() -> int:
    disable_windows_quickedit()

    parser = argparse.ArgumentParser(description="JobMind Match desktop launcher")
    parser.add_argument("--port", type=int, default=8000, help="HTTP port (default: 8000)")
    args = parser.parse_args()
    port = args.port

    base_url = configure_environment(port)
    dashboard_url = f"{base_url}/dashboard"

    print()
    print("=" * 60)
    print("  JobMind Match")
    print(f"  Starting server on {base_url} ...")
    print("=" * 60)
    print()

    server_thread = threading.Thread(target=run_uvicorn, args=(port,), daemon=True)
    server_thread.start()

    time.sleep(1.5)

    if not wait_for_server(base_url):
        print("Warning: server is still starting; opening the browser anyway.")

    try:
        webbrowser.open(dashboard_url)
    except Exception as exc:
        print(f"Could not open browser automatically: {exc}")
        print(f"Open manually: {dashboard_url}")

    print(
        f"JobMind Match is running at {base_url} — close this window to stop the app"
    )
    print()

    try:
        while server_thread.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nShutting down JobMind Match...")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
