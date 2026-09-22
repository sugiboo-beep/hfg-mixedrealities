"""Shared helpers for the content-adding scripts (add_work.py, add_event.py): turning a local
image file into a registered, thumbnailed site asset with a stable media hash.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FULL_DIR = ROOT / "assets" / "img" / "full"
THUMB_DIR = ROOT / "assets" / "img" / "thumb"
THUMB_WIDTH = 700
IMAGE_EXTS = {"jpg", "jpeg", "png", "gif", "webp"}


def slugify(text: str, fallback: str = "item") -> str:
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug or fallback


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


def register_image(image_path: Path, media: dict, base_name: str) -> str:
    """Copy ``image_path`` into assets/img/{full,thumb}, add it to ``media`` (mutated in place)
    and return its new media hash. ``base_name`` seeds the on-disk filename (e.g. a slug)."""
    ext = image_path.suffix.lstrip(".").lower()
    data = image_path.read_bytes()
    media_hash = hashlib.sha1(data).hexdigest()[:24].upper()
    if media_hash in media:
        raise ValueError(f"'{image_path.name}' is already registered (duplicate content hash).")

    filename = f"{base_name}.{ext}"
    if (FULL_DIR / filename).exists():
        filename = f"{base_name}-{media_hash[:6].lower()}.{ext}"

    full_path = FULL_DIR / filename
    thumb_path = THUMB_DIR / filename
    full_path.write_bytes(data)
    width, height = image_dims(full_path)
    make_thumb(full_path, thumb_path, width)

    media[media_hash] = {"file": filename, "name": image_path.name, "w": width, "h": height, "type": ext}
    print(f"  image: {full_path.relative_to(ROOT)} (thumb: {thumb_path.relative_to(ROOT)})")
    return media_hash
