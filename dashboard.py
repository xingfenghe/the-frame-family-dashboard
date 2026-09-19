"""Render the family dashboard (art + info card) to a 3840x2160 JPEG, optionally push to The Frame.

Usage:
  dashboard.py            # render only -> out/dashboard.jpg
  dashboard.py --push     # render and push (only if the TV is already in art mode)

board.json holds everything the card shows besides the weather:
  "events"  calendar items, written by whatever syncs your calendar (see README)
  "hide"    title substrings to drop (recurring noise)
  "notes"   reminders pinned at the bottom of the card
  "lat"/"lon"  location for the weather line (omit to hide it)

The art directory needs catalog.csv (id,title,artist,...) plus ready/<id>.jpg
(16:9 crops) and optionally raw/<id>.source (uncropped originals).
"""
import csv
import html
import json
import random
import subprocess
import sys
import tempfile
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image

from config import ART_DIR as ART, CHROME, STRINGS

HERE = Path(__file__).parent
OUT = HERE / "out"
NOTES = HERE / "art-notes.json"  # artwork id -> short blurb shown under the painting


def pick_art(now):
    """One artwork per hour, in a fixed shuffled order so neighbouring hours aren't same-category."""
    rows = list(csv.DictReader(open(ART / "catalog.csv", encoding="utf-8")))
    random.Random(20260917).shuffle(rows)
    hours = int(now.timestamp() // 3600)
    return rows[hours % len(rows)]


def weather(board):
    if not board.get("lat"):
        return None
    url = ("https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
           "&current=temperature_2m,weather_code&daily=temperature_2m_max,temperature_2m_min,"
           "precipitation_probability_max&timezone=auto&forecast_days=1").format(**board)
    d = json.load(urllib.request.urlopen(url, timeout=15))
    return {"now": round(d["current"]["temperature_2m"]),
            "hi": round(d["daily"]["temperature_2m_max"][0]),
            "lo": round(d["daily"]["temperature_2m_min"][0]),
            "rain": d["daily"]["precipitation_probability_max"][0]}


def art_image(art, tmp):
    """Full painting (uncropped original) when its shape fits; long scrolls fall back to the 16:9 crop."""
    Image.MAX_IMAGE_PIXELS = None
    try:
        im = Image.open(ART / "raw" / f'{art["id"]}.source')
        im.load()
    except OSError:  # online-only Drive file: background jobs can't download it
        im = None
    if im is None or not 0.5 <= im.width / im.height <= 2.6:
        im = Image.open(ART / "ready" / f'{art["id"]}.jpg')
    im = im.convert("RGB")
    im.thumbnail((2800, 2000))
    path = Path(tmp) / "art.jpg"
    im.save(path, quality=92)
    # wall color: painting's average tone, mostly washed toward warm paper white
    avg = im.resize((1, 1)).getpixel((0, 0))
    wall = "rgb({},{},{})".format(*(round(c * 0.22 + w * 0.78) for c, w in zip(avg, (238, 233, 224))))
    return path, wall


def event_section(label, day, events, now, limit):
    """Keep the card from overflowing: at most `limit` rows, rest summarised."""
    day_events = [e for e in events if e["date"] == day.isoformat()]
    extra = len(day_events) - limit
    rows = []
    for e in day_events[:limit]:
        done = day == now.date() and e["time"] != STRINGS["all_day"] and e["time"] < now.strftime("%H:%M")
        rows.append(f'<li class="{"done" if done else ""}"><span class="t">{html.escape(e["time"])}</span>'
                    f'<span>{html.escape(e["title"])}</span></li>')
    if extra > 0:
        rows.append(f'<li class="more">{STRINGS["more"].format(n=extra)}</li>')
    body = "".join(rows) or f'<li class="empty">{STRINGS["nothing"]}</li>'
    return f"<h2>{label}</h2><ul>{body}</ul>"


def render(now):
    board = json.loads((HERE / "board.json").read_text(encoding="utf-8"))
    art = pick_art(now)
    w = weather(board)
    wx = (f'<div class="wx"><b>{w["now"]}°</b><span>{STRINGS["weather"].format(**w)}</span></div>'
          if w else "")
    events = [e for e in board.get("events", []) if not any(h in e["title"] for h in board.get("hide", []))]
    sections = (event_section(STRINGS["today"], now.date(), events, now, 5)
                + event_section(STRINGS["tomorrow"], now.date() + timedelta(days=1), events, now, 4))
    OUT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        art_path, wall = art_image(art, tmp)
        page = (HERE / "template.html").read_text(encoding="utf-8").format(
            wall=wall,
            art=art_path.as_uri(),
            weekday=STRINGS["weekdays"][now.weekday()],
            date=STRINGS["date"].format(year=now.year, month=now.month, day=now.day),
            weather=wx,
            sections=sections,
            reminders=("".join(f'<div class="rem">{html.escape(n)}</div>' for n in board.get("notes", []))),
            title=html.escape(art["title"]),
            artist=html.escape(art["artist"]),
            note=html.escape(json.loads(NOTES.read_text(encoding="utf-8")).get(art["id"], "") if NOTES.exists() else ""),
            updated=STRINGS["updated"].format(time=now.strftime("%H:%M")),
        )
        src, png = Path(tmp) / "page.html", Path(tmp) / "shot.png"
        src.write_text(page, encoding="utf-8")
        subprocess.run([CHROME, "--headless=new", "--hide-scrollbars", "--allow-file-access-from-files",
                        "--window-size=1920,1080", "--force-device-scale-factor=2",
                        f"--screenshot={png}", src.as_uri()],
                       check=True, capture_output=True, timeout=90)
        jpg = OUT / "dashboard.jpg"
        Image.open(png).convert("RGB").resize((3840, 2160)).save(jpg, quality=92)
    return jpg


if __name__ == "__main__":
    jpg = render(datetime.now())
    print(jpg)
    if "--push" in sys.argv:
        import frame
        print(json.dumps(frame.push(str(jpg), force="--force" in sys.argv), ensure_ascii=False))
