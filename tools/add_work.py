"""Add one student project ("work") to a project page's Contributions section.

Registers a cover image, writes a body-text record and appends an entry to
``content/site.json``'s ``works`` list, then rebuilds the site. Run with --help
for usage, or see the example at the bottom of this file's docstring.

Example:
    python3 tools/add_work.py \\
        --project the-floor-is-lava \\
        --title "The Garden of Forking Paths" \\
        --author "Jane Doe" \\
        --image content/incoming/jane-cover.jpg \\
        --body "First paragraph of the write-up." \\
        --body "Second paragraph, if any."
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
FULL_DIR = ROOT / "assets" / "img" / "full"
THUMB_DIR = ROOT / "assets" / "img" / "thumb"
THUMB_WIDTH = 700


def slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug or "work"


def unique_slug(base: str, taken: set[str]) -> str:
    slug = base
    n = 2
    while slug in taken:
        slug = f"{base}-{n}"
        n += 1
    return slug


def image_dims(path: Path) -> tuple[int, int]:
    out = subprocess.run(
        ["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(path)],
        check=True, capture_output=True, text=True,
    ).stdout
    w = int(re.search(r"pixelWidth: (\d+)", out).group(1))
    h = int(re.search(r"pixelHeight: (\d+)", out).group(1))
    return w, h


def make_thumb(full_path: Path, thumb_path: Path, width: int) -> None:
    if width > THUMB_WIDTH:
        subprocess.run(
            ["sips", "--resampleWidth", str(THUMB_WIDTH), str(full_path), "--out", str(thumb_path)],
            check=True, capture_output=True, text=True,
        )
    else:
        thumb_path.write_bytes(full_path.read_bytes())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True, help="Project slug, e.g. the-floor-is-lava")
    ap.add_argument("--title", required=True, help="Title of the student's work")
    ap.add_argument("--author", required=True, help="Student name")
    ap.add_argument("--image", required=True, help="Path to the cover image")
    ap.add_argument("--body", action="append", default=[], help="One paragraph of body text; repeat for more")
    ap.add_argument("--subtitle", default=None)
    ap.add_argument("--note", default=None)
    ap.add_argument("--slug", default=None, help="Override the auto-generated work slug")
    ap.add_argument("--no-build", action="store_true", help="Skip rebuilding the site afterwards")
    args = ap.parse_args()

    site_path = CONTENT / "site.json"
    text_path = CONTENT / "text.json"
    media_path = CONTENT / "media_index.json"
    site = json.loads(site_path.read_text(encoding="utf-8"))
    text = json.loads(text_path.read_text(encoding="utf-8"))
    media = json.loads(media_path.read_text(encoding="utf-8"))

    project = next((p for p in site["projects"] if p["slug"] == args.project), None)
    if project is None:
        available = ", ".join(p["slug"] for p in site["projects"])
        sys.exit(f"No project '{args.project}'. Available: {available}")

    image_path = Path(args.image).expanduser().resolve()
    if not image_path.is_file():
        sys.exit(f"Image not found: {image_path}")

    ext = image_path.suffix.lstrip(".").lower()
    if ext not in {"jpg", "jpeg", "png", "gif", "webp"}:
        sys.exit(f"Unsupported image type: .{ext}")

    taken_slugs = {w["slug"] for w in site["works"]}
    slug = args.slug or unique_slug(slugify(args.author), taken_slugs)
    if slug in taken_slugs:
        sys.exit(f"Work slug '{slug}' already exists; pass --slug to override.")

    data = image_path.read_bytes()
    media_hash = hashlib.sha1(data).hexdigest()[:24].upper()
    if media_hash in media:
        sys.exit("This exact image is already registered (duplicate content hash).")

    filename = f"{slug}-cover.{ext}"
    if (FULL_DIR / filename).exists():
        filename = f"{slug}-cover-{media_hash[:6].lower()}.{ext}"

    full_path = FULL_DIR / filename
    thumb_path = THUMB_DIR / filename
    full_path.write_bytes(data)
    width, height = image_dims(full_path)
    make_thumb(full_path, thumb_path, width)

    media[media_hash] = {"file": filename, "name": image_path.name, "w": width, "h": height, "type": ext}

    blocks = [
        {"kind": "p", "lines": [args.title]},
        {"kind": "p", "lines": [args.author]},
    ]
    for paragraph in args.body:
        blocks.append({"kind": "p", "lines": [paragraph]})
    text[slug] = {"title": args.author, "type": "page", "blocks": blocks, "images": [], "captions": {}}

    work = {
        "slug": slug,
        "source": slug,
        "title": args.title,
        "author": args.author,
        "cover": media_hash,
        "project": args.project,
        "skip": 2,
    }
    if args.subtitle:
        work["subtitle"] = args.subtitle
    if args.note:
        work["note"] = args.note
    site["works"].append(work)

    site_path.write_text(json.dumps(site, indent=1, ensure_ascii=False), encoding="utf-8")
    text_path.write_text(json.dumps(text, indent=1, ensure_ascii=False), encoding="utf-8")
    media_path.write_text(json.dumps(media, indent=1, ensure_ascii=False), encoding="utf-8")

    print(f"Added work '{slug}' ({args.title} — {args.author}) to project '{args.project}'.")
    print(f"  image: {full_path.relative_to(ROOT)} (thumb: {thumb_path.relative_to(ROOT)})")

    if not args.no_build:
        subprocess.run([sys.executable, str(ROOT / "tools" / "build.py")], check=True, cwd=ROOT)
        print("Rebuilt the site.")


if __name__ == "__main__":
    main()
