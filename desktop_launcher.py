#!/usr/bin/env python3
"""
JobMind Match cross-platform desktop launcher (PyInstaller entry point).

Starts Uvicorn, opens the dashboard in the default browser, and keeps running
until the console window is closed or Ctrl+C is pressed.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import shutil
import subprocess
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


def _running_marker_path() -> Path:
    return user_data_dir() / "running.json"


def _write_running_marker(pid: int, port: int) -> None:
    try:
        _running_marker_path().write_text(json.dumps({"pid": pid, "port": port}), encoding="utf-8")
    except OSError:
        pass


def _remove_running_marker() -> None:
    try:
        _running_marker_path().unlink(missing_ok=True)
    except OSError:
        pass


def _read_running_marker() -> dict | None:
    try:
        return json.loads(_running_marker_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _pid_is_running(pid: int) -> bool:
    if sys.platform == "win32":
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        try:
            exit_code = ctypes.c_ulong()
            if not ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                return False
            return exit_code.value == STILL_ACTIVE
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _quit_running_instance() -> int:
    """Handles `--quit`: used by the Start Menu "Quit" shortcut and by the
    installer's [UninstallRun] step (with waituntilterminated), so this must
    not return until the running instance has actually exited — a "close
    request sent" that returns early would let the uninstaller/updater race
    a still-locked .exe, the exact bug already found and fixed in the
    update-flow's own PID-wait helper (see app/routes/web.py). Reads the
    real port from the marker file written at startup rather than assuming
    --port's default, since the running instance may have been started with
    a different one."""
    marker = _read_running_marker()
    if not marker:
        print("JobMind Match is not running.")
        return 0

    pid = marker.get("pid")
    port = marker.get("port")

    if not isinstance(pid, int) or not _pid_is_running(pid):
        print("JobMind Match is not running.")
        _remove_running_marker()
        return 0

    if isinstance(port, int):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/app/quit", data=b"", timeout=3)
        except (urllib.error.URLError, TimeoutError, OSError):
            pass  # server may already be down; fall through to the PID wait below

    deadline = time.time() + 10.0
    while time.time() < deadline and _pid_is_running(pid):
        time.sleep(0.2)

    if _pid_is_running(pid):
        # The graceful request didn't land (e.g. server already wedged) —
        # force it rather than leaving the caller (uninstaller/updater)
        # waiting on a process that will never exit on its own.
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
        else:
            import signal

            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
        deadline = time.time() + 5.0
        while time.time() < deadline and _pid_is_running(pid):
            time.sleep(0.2)

    _remove_running_marker()
    print("JobMind Match closed." if not _pid_is_running(pid) else "Warning: could not confirm JobMind Match closed.")
    return 0


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
    parser.add_argument(
        "--quit", action="store_true",
        help="Ask the already-running instance to close, wait for it to actually exit, then exit",
    )
    args = parser.parse_args()

    if args.quit:
        return _quit_running_instance()

    port = args.port

    base_url = configure_environment(port)
    dashboard_url = f"{base_url}/dashboard"

    print()
    print("=" * 60)
    print("  JobMind Match")
    print(f"  Starting server on {base_url} ...")
    print("=" * 60)
    print()

    _write_running_marker(os.getpid(), port)

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

    _remove_running_marker()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
