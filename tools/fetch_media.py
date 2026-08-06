"""Download every image the source site holds and record the hash -> local file mapping.

The source is a Cargo site; its media live on ``freight.cargo.site`` and are served only with a
``Referer`` from the site itself. Raster images are pulled at two widths (1800 px for the lightbox,
700 px for gallery thumbnails); GIFs are pulled at their original size so animation survives.
"""

import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEDIA = ROOT / "content" / "source" / "media.json"
INDEX = ROOT / "content" / "media_index.json"

REFERER = "https://1019911-copy4.cargo.site/"
AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120 Safari/537.36"
)
SIZES = {"assets/img/full": 1800, "assets/img/thumb": 700}


class MediaFetcher:
    """Pull the site's media library into the local assets tree."""

    def __init__(self, records: list[dict]):
        self.items = {}
        for record in records:
            for item in record["media"]:
                self.items[item["hash"]] = item

    @staticmethod
    def filename(media_hash: str, name: str) -> str:
        base, ext = os.path.splitext(name)
        base = re.sub(r"[^A-Za-z0-9]+", "-", base).strip("-").lower() or "img"
        return f"{base}-{media_hash[:6].lower()}{ext.lower()}"

    def url(self, media_hash: str, name: str, width: int | None) -> str:
        size = f"w/{width}" if width else "t/original"
        return f"https://freight.cargo.site/{size}/i/{media_hash}/{name}"

    def fetch(self, url: str, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            ["curl", "-sS", "-A", AGENT, "-H", f"Referer: {REFERER}", "-o", str(target), "-w", "%{http_code}", url],
            capture_output=True,
            text=True,
        )
        if result.stdout.strip() != "200":
            raise RuntimeError(f"{result.stdout.strip()} for {url}")

    def run(self) -> dict:
        index = {}
        for media_hash, item in self.items.items():
            name = self.filename(media_hash, item["name"])
            animated = item["file_type"].lower() == "gif"
            for directory, width in SIZES.items():
                self.fetch(
                    self.url(media_hash, item["name"], None if animated else width),
                    ROOT / directory / name,
                )
            index[media_hash] = {
                "file": name,
                "name": item["name"],
                "w": item["width"],
                "h": item["height"],
                "type": item["file_type"],
            }
            print(f"{media_hash[:8]}  {name}")
        return index


if __name__ == "__main__":
    fetcher = MediaFetcher(json.loads(MEDIA.read_text(encoding="utf-8")))
    INDEX.write_text(json.dumps(fetcher.run(), indent=1), encoding="utf-8")
    print(f"{len(fetcher.items)} images")
