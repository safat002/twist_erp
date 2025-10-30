import atexit
import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path

from django.conf import settings
try:
    # Preserve staticfiles' enhanced runserver behavior when available
    from django.contrib.staticfiles.management.commands.runserver import (
        Command as BaseRunserver,
    )
except Exception:  # pragma: no cover - fallback for minimal setups
    from django.core.management.commands.runserver import Command as BaseRunserver


def _npm_executable() -> str:
    """Return the platform-appropriate npm executable name."""
    return "npm.cmd" if os.name == "nt" else "npm"


def _start_frontend_if_possible() -> subprocess.Popen | None:
    """Start the Vite dev server (npm run dev) if npm and frontend exist.

    Returns the Popen handle or None if not started.
    """
    # Only start in the autoreload child process to avoid double-spawn
    if os.environ.get("RUN_MAIN") != "true":
        return None

    project_root = Path(settings.BASE_DIR).parent
    frontend_dir = project_root / "frontend"

    # Allow opting out via env var
    if os.environ.get("DISABLE_AUTO_FRONTEND") == "1":
        return None

    # Quick sanity checks
    npm = _npm_executable()
    if shutil.which(npm) is None:
        print("[dev] npm not found on PATH; skipping frontend autostart.", file=sys.stderr)
        return None
    if not frontend_dir.exists():
        print(f"[dev] frontend directory not found at {frontend_dir}; skipping.", file=sys.stderr)
        return None

    # If node_modules missing, install dependencies once
    node_modules = frontend_dir / "node_modules"
    try:
        if not node_modules.exists():
            print("[dev] Installing frontend dependencies (first run)...", flush=True)
            lockfile = frontend_dir / "package-lock.json"
            install_cmd = [npm, "ci"] if lockfile.exists() else [npm, "install"]
            subprocess.run(install_cmd, cwd=str(frontend_dir), check=True)
    except Exception as exc:
        print(f"[dev] Failed to install frontend deps: {exc}", file=sys.stderr)
        return None

    # Launch Vite dev server
    try:
        print("[dev] Starting frontend (npm run dev) ...", flush=True)
        # Creation flags ensure better signal handling on Windows
        creationflags = 0
        if os.name == "nt":
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]

        proc = subprocess.Popen(
            [npm, "run", "dev"],
            cwd=str(frontend_dir),
            stdout=sys.stdout,
            stderr=sys.stderr,
            text=True,
            creationflags=creationflags,
        )

        # _drain_initial_output() # Removed this line

        # Ensure child is terminated on exit
        def _cleanup():
            if proc.poll() is None:
                try:
                    if os.name == "nt":
                        proc.send_signal(signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
                    else:
                        proc.terminate()
                except Exception:
                    pass

        atexit.register(_cleanup)
        return proc
    except Exception as exc:
        print(f"[dev] Failed to start frontend: {exc}", file=sys.stderr)
        return None


class Command(BaseRunserver):
    help = "Runs the Django development server and auto-starts the frontend dev server."

    def inner_run(self, *args, **options):  # type: ignore[override]
        # Attempt to start frontend before backend binds the port
        _start_frontend_if_possible()
        return super().inner_run(*args, **options)
