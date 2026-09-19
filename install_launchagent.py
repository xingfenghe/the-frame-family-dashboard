"""Write and load the LaunchAgent that refreshes the dashboard every 15 minutes, 07:30-21:00.

    python3 install_launchagent.py            # write + load
    python3 install_launchagent.py --uninstall

Times outside the window are skipped entirely, so nothing runs overnight.
"""
import os
import plistlib
import subprocess
import sys
from pathlib import Path

LABEL = "com.frame-dashboard.refresh"
PLIST = Path.home() / "Library/LaunchAgents" / f"{LABEL}.plist"
HERE = Path(__file__).parent.resolve()
PYTHON = HERE / ".venv/bin/python"
DOMAIN = f"gui/{os.getuid()}"


def times(first=(7, 30), last=(21, 0), step=15):
    return [{"Hour": h, "Minute": m}
            for h in range(first[0], last[0] + 1) for m in range(0, 60, step)
            if first <= (h, m) <= last]


def install():
    PLIST.parent.mkdir(parents=True, exist_ok=True)
    PLIST.write_bytes(plistlib.dumps({
        "Label": LABEL,
        "ProgramArguments": [str(PYTHON), "-W", "ignore", str(HERE / "dashboard.py"), "--push"],
        "WorkingDirectory": str(HERE),
        "StartCalendarInterval": times(),
        "StandardOutPath": str(Path.home() / "Library/Logs/frame-dashboard.log"),
        "StandardErrorPath": str(Path.home() / "Library/Logs/frame-dashboard.log"),
    }))
    subprocess.run(["launchctl", "bootout", f"{DOMAIN}/{LABEL}"], capture_output=True)
    subprocess.run(["launchctl", "bootstrap", DOMAIN, str(PLIST)], check=True)
    print(f"loaded {LABEL}; log: ~/Library/Logs/frame-dashboard.log")


if __name__ == "__main__":
    if "--uninstall" in sys.argv:
        subprocess.run(["launchctl", "bootout", f"{DOMAIN}/{LABEL}"], capture_output=True)
        PLIST.unlink(missing_ok=True)
        print("removed")
    else:
        install()
