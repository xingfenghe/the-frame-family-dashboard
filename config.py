"""Shared config. Copy config.example.json to config.json and edit it."""
import json
import os
from pathlib import Path

HERE = Path(__file__).parent
CONFIG = json.loads((HERE / "config.json").read_text(encoding="utf-8"))

TV_HOST = CONFIG["tv_host"]
ART_DIR = Path(os.path.expanduser(CONFIG["art_dir"]))
STATE_DIR = Path(os.path.expanduser(CONFIG.get("state_dir", "~/.config/frame-dashboard")))
CHROME = CONFIG.get("chrome", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")

# Card wording. Override any of these in config.json -> "strings".
STRINGS = {
    "weekdays": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    "date": "{month}/{day}",     # also gets {year}
    "today": "TODAY",
    "tomorrow": "TOMORROW",
    "all_day": "all day",
    "nothing": "nothing scheduled",
    "more": "{n} more",
    "updated": "updated {time}",
    "weather": "{lo}° / {hi}° · rain {rain}%",
    **CONFIG.get("strings", {}),
}
