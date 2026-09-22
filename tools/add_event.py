"""Add an entry to the Events page's "Current & upcoming" list.

Registers an optional image and appends one item to ``content/site.json``'s
``upcoming`` list, then rebuilds the site. The landing-page pop-up (see
``announcement`` in site.json) automatically features the first upcoming
entry that has an image, so giving one here also puts it in the pop-up.

Example:
    python3 tools/add_event.py \\
        --title "Aktwechsel - 35mm Workshop" \\
        --date "26 Sept 2026, 13:00-17:00" \\
        --place "Kino im Blauen Salon, HfG Karlsruhe" \\
        --blurb "Hands-on introduction to analogue 35mm film projection." \\
        --image content/incoming/aktwechsel.jpg \\
        --link "https://hfg-karlsruhe.de/aktuelles/aktwechsel-35mm-workshop-26092026/" \\
        --link-label "Details and registration"
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from media_tools import ROOT, register_image, slugify, unique_slug

CONTENT = ROOT / "content"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--title", required=True, help="Event title")
    ap.add_argument("--date", default=None, help='e.g. "26 Sept 2026, 13:00-17:00"')
    ap.add_argument("--place", default=None, help="Venue")
    ap.add_argument("--blurb", default=None, help="One short description line")
    ap.add_argument("--image", default=None, help="Path to an image (shown on the Events page and, "
                     "if it's the first upcoming entry with one, in the landing-page pop-up)")
    ap.add_argument("--link", default=None, help="URL with more information, if any")
    ap.add_argument("--link-label", default=None, help='Link text (default: "More information")')
    ap.add_argument("--slug", default=None, help="Override the auto-generated event id")
    ap.add_argument("--first", action="store_true", help="Insert at the top of the list instead of the end")
    ap.add_argument("--no-build", action="store_true", help="Skip rebuilding the site afterwards")
    args = ap.parse_args()

    site_path = CONTENT / "site.json"
    media_path = CONTENT / "media_index.json"
    site = json.loads(site_path.read_text(encoding="utf-8"))
    media = json.loads(media_path.read_text(encoding="utf-8"))

    site.setdefault("upcoming", [])
    taken_slugs = {e["slug"] for e in site["upcoming"] if e.get("slug")}
    slug = args.slug or unique_slug(slugify(args.title, "event"), taken_slugs)

    event = {"slug": slug, "title": args.title}
    for key, val in (("date", args.date), ("place", args.place), ("blurb", args.blurb),
                      ("link", args.link), ("link_label", args.link_label)):
        if val:
            event[key] = val

    if args.image:
        image_path = Path(args.image).expanduser().resolve()
        if not image_path.is_file():
            sys.exit(f"Image not found: {image_path}")
        if image_path.suffix.lstrip(".").lower() not in {"jpg", "jpeg", "png", "gif", "webp"}:
            sys.exit(f"Unsupported image type: {image_path.suffix}")
        try:
            event["image"] = register_image(image_path, media, slug)
        except ValueError as e:
            sys.exit(str(e))

    if args.first:
        site["upcoming"].insert(0, event)
    else:
        site["upcoming"].append(event)

    site_path.write_text(json.dumps(site, indent=1, ensure_ascii=False), encoding="utf-8")
    media_path.write_text(json.dumps(media, indent=1, ensure_ascii=False), encoding="utf-8")

    print(f"Added event '{slug}' ({args.title}).")

    if not args.no_build:
        subprocess.run([sys.executable, str(ROOT / "tools" / "build.py")], check=True, cwd=ROOT)
        print("Rebuilt the site.")


if __name__ == "__main__":
    main()
