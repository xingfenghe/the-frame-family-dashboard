"""Control Samsung The Frame (art mode) from a Mac.

Usage:
  frame.py status
  frame.py show <content_id>
  frame.py artmode on|off
  frame.py push <image.jpg> [--force]   # upload, display, delete the previously pushed image
"""
import json
import sys

from samsungtvws import SamsungTVWS

from config import STATE_DIR, TV_HOST

TOKEN = STATE_DIR / "token"                 # TV pairing token — keep it out of version control
STATE = STATE_DIR / "dashboard-state.json"  # content_id of the image we pushed last


def tv(timeout=60):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    return SamsungTVWS(TV_HOST, port=8002, token_file=str(TOKEN), timeout=timeout, name="FrameDashboard")


def status():
    t = tv()
    info = t.rest_device_info()["device"]
    out = {"power": info.get("PowerState")}
    if out["power"] == "on":
        art = t.art()
        out["artmode"] = art.get_artmode()
        out["current"] = art.get_current().get("content_id")
    return out


def push(image, force=False):
    """Show image only if the TV is already in art mode (never interrupt someone watching)."""
    art = tv(timeout=120).art()
    if not force and art.get_artmode() != "on":
        return {"skipped": "TV not in art mode"}
    prev = json.loads(STATE.read_text()).get("content_id") if STATE.exists() else None
    cid = art.upload(image, matte="none", portrait_matte="none")
    art.select_image(cid, show=True)
    STATE.write_text(json.dumps({"content_id": cid}))
    if prev and prev != cid:
        art.delete(prev)  # otherwise every refresh leaves another copy on the TV
    return {"shown": cid, "deleted": prev}


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "status":
        r = status()
    elif cmd == "show":
        r = tv().art().select_image(args[0], show=True)
    elif cmd == "artmode":
        r = tv().art().set_artmode(args[0])
    elif cmd == "push":
        r = push(args[0], force="--force" in args)
    else:
        sys.exit(__doc__)
    print(json.dumps(r, ensure_ascii=False))
