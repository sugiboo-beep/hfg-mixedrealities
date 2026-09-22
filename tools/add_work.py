"""Add one student project ("work") to a project page's Contributions section.

Registers one or more images, writes a body-text record and appends an entry
to ``content/site.json``'s ``works`` list, then rebuilds the site. The first
--image becomes the card thumbnail everywhere; all images given show as a
gallery on the work's own page. Run with --help for usage, or see the example
at the bottom of this file's docstring.

Example:
    python3 tools/add_work.py \\
        --project the-floor-is-lava \\
        --title "The Garden of Forking Paths" \\
        --author "Jane Doe" \\
        --image content/incoming/jane-1.jpg \\
        --image content/incoming/jane-2.jpg \\
        --body "First paragraph of the write-up." \\
        --body "Second paragraph, if any." \\
        --link "https://umbau.hfg-karlsruhe.de/posts/the-garden-of-forking-paths" \\
        --link-label "Read on UMBAU"
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
    ap.add_argument("--project", required=True, help="Project slug, e.g. the-floor-is-lava")
    ap.add_argument("--title", required=True, help="Title of the student's work")
    ap.add_argument("--author", required=True, help="Student name")
    ap.add_argument("--image", action="append", required=True, dest="images",
                     help="Path to an image; repeat for more. The first one is used as the card thumbnail.")
    ap.add_argument("--body", action="append", default=[], help="One paragraph of body text; repeat for more")
    ap.add_argument("--link", default=None, help="URL where the work was published, if any")
    ap.add_argument("--link-label", default=None, help='Link text, e.g. "Read on UMBAU" (default: "View the contribution")')
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

    image_paths = [Path(p).expanduser().resolve() for p in args.images]
    for p in image_paths:
        if not p.is_file():
            sys.exit(f"Image not found: {p}")
        if p.suffix.lstrip(".").lower() not in {"jpg", "jpeg", "png", "gif", "webp"}:
            sys.exit(f"Unsupported image type: {p.suffix}")

    taken_slugs = {w["slug"] for w in site["works"]}
    slug = args.slug or unique_slug(slugify(args.author, "work"), taken_slugs)
    if slug in taken_slugs:
        sys.exit(f"Work slug '{slug}' already exists; pass --slug to override.")

    hashes = []
    for i, image_path in enumerate(image_paths):
        base_name = f"{slug}-cover" if i == 0 else f"{slug}-{i + 1}"
        try:
            hashes.append(register_image(image_path, media, base_name))
        except ValueError as e:
            sys.exit(str(e))

    blocks = [
        {"kind": "p", "lines": [args.title]},
        {"kind": "p", "lines": [args.author]},
    ]
    for paragraph in args.body:
        blocks.append({"kind": "p", "lines": [paragraph]})
    text[slug] = {"title": args.author, "type": "page", "blocks": blocks, "images": hashes, "captions": {}}

    work = {
        "slug": slug,
        "source": slug,
        "title": args.title,
        "author": args.author,
        "cover": hashes[0],
        "project": args.project,
        "skip": 2,
    }
    if args.subtitle:
        work["subtitle"] = args.subtitle
    if args.note:
        work["note"] = args.note
    if args.link:
        work["link"] = args.link
        if args.link_label:
            work["link_label"] = args.link_label
    site["works"].append(work)

    site_path.write_text(json.dumps(site, indent=1, ensure_ascii=False), encoding="utf-8")
    text_path.write_text(json.dumps(text, indent=1, ensure_ascii=False), encoding="utf-8")
    media_path.write_text(json.dumps(media, indent=1, ensure_ascii=False), encoding="utf-8")

    print(f"Added work '{slug}' ({args.title} — {args.author}) to project '{args.project}'.")

    if not args.no_build:
        subprocess.run([sys.executable, str(ROOT / "tools" / "build.py")], check=True, cwd=ROOT)
        print("Rebuilt the site.")


if __name__ == "__main__":
    main()
