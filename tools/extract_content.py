"""Convert the scraped Cargo page payloads into the structured content model used by the build.

Reads ``content/source/pages.json`` (the ``__PRELOADED_STATE__`` page records pulled from
1019911-copy4.cargo.site) and ``content/media_index.json`` (hash -> local file mapping written by
the image download step), and emits ``content/text.json``: for every page, a title, a list of
prose blocks, and the ordered list of image hashes referenced by its galleries.
"""

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "content" / "source" / "pages.json"
MEDIA = ROOT / "content" / "media_index.json"
OUT = ROOT / "content" / "text.json"
OUT_MD = ROOT / "content" / "text.md"


class CargoContent:
    """Parse one Cargo page's rich-text ``content`` field."""

    #: Elements whose text is gallery or navigation scaffolding rather than prose.
    _DROP = re.compile(
        r"<(gallery-[a-z]+)\b.*?</\1>|<span class=\"cg-dropdown-wrap\">.*?</span></span>",
        re.S,
    )
    #: Column wrappers separate prose regions but contribute no text of their own.
    _COLUMN = re.compile(r"</?(column-set|column-unit)\b[^>]*>", re.I)
    _TAG = re.compile(r"<[^>]+>")
    _BREAK = re.compile(r"(?:<br\s*/?>\s*){2,}", re.I)

    def __init__(self, content: str):
        self.content = content or ""

    @property
    def image_hashes(self) -> list[str]:
        """Media hashes in the order the page's galleries place them, placeholders removed."""
        return [h for h in re.findall(r'hash="([^"]+)"', self.content) if h != "placeholder"]

    @property
    def captions(self) -> dict[str, str]:
        """Map media hash -> caption text for gallery items that carry a ``figcaption``."""
        out = {}
        for m in re.finditer(r'<media-item[^>]*hash="([^"]+)"[^>]*>(.*?)</media-item>', self.content, re.S):
            cap = re.search(r"<figcaption[^>]*>(.*?)</figcaption>", m.group(2), re.S)
            if cap:
                text = self._plain(cap.group(1))
                if text:
                    out[m.group(1)] = text
        return out

    @property
    def links(self) -> dict[str, str]:
        """Map media hash -> the page slug that gallery item links to."""
        out = {}
        for m in re.finditer(r"<media-item[^>]*>", self.content):
            tag = m.group(0)
            h = re.search(r'hash="([^"]+)"', tag)
            href = re.search(r'href="([^"]+)"', tag)
            if h and href:
                out[h.group(1)] = href.group(1)
        return out

    @property
    def freeform(self) -> list[dict]:
        """Collage placements the source site stores on each freeform gallery item.

        ``freeform-x`` and ``freeform-scale`` are percentages of the gallery's width;
        ``freeform-y`` is in the same unit, so it runs past 100 for a tall collage.
        ``freeform-z`` is the stacking order.
        """
        out = []
        for m in re.finditer(r"<media-item[^>]*>", self.content):
            tag = m.group(0)
            attrs = dict(re.findall(r'([a-z-]+)="([^"]*)"', tag))
            if "freeform-x" not in attrs or attrs.get("hash") == "placeholder":
                continue
            out.append(
                {
                    "hash": attrs["hash"],
                    "x": float(attrs["freeform-x"]),
                    "y": float(attrs["freeform-y"]),
                    "scale": float(attrs.get("freeform-scale", 25)),
                    "z": int(attrs.get("freeform-z", 1)),
                }
            )
        return out

    @property
    def blocks(self) -> list[dict]:
        """Prose split into paragraphs, with right-aligned passages marked as ``aside``."""
        body = self._COLUMN.sub("<br /><br />", self._DROP.sub("", self.content))
        blocks = []
        for chunk in re.split(r"(<div style=\"text-align: right\">.*?</div>)", body, flags=re.S):
            aside = chunk.startswith('<div style="text-align: right"')
            for para in self._BREAK.split(chunk):
                text = self._plain(para, keep_breaks=True)
                if text:
                    blocks.append({"kind": "aside" if aside else "p", "lines": text.split("\n")})
        return blocks

    @classmethod
    def _plain(cls, fragment: str, keep_breaks: bool = False) -> str:
        text = re.sub(r"<br\s*/?>", "\n" if keep_breaks else " ", fragment, flags=re.I)
        text = cls._TAG.sub("", text)
        text = html.unescape(text)
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
        return "\n".join(line for line in lines if line)


def main() -> None:
    pages = json.loads(SOURCE.read_text(encoding="utf-8"))
    media = json.loads(MEDIA.read_text(encoding="utf-8"))

    out = {}
    for purl, page in pages.items():
        parsed = CargoContent(page.get("content"))
        hashes = [h for h in parsed.image_hashes if h in media]
        seen, ordered = set(), []
        for h in hashes:
            if h not in seen:
                seen.add(h)
                ordered.append(h)
        out[purl] = {
            "title": page.get("title"),
            "type": page.get("page_type"),
            "blocks": parsed.blocks,
            "images": ordered,
            "captions": parsed.captions,
            "links": parsed.links,
            "freeform": [f for f in parsed.freeform if f["hash"] in media],
        }

    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")

    lines = ["# Text archived from https://1019911-copy4.cargo.site", ""]
    for purl, rec in out.items():
        if not rec["blocks"] and not rec["images"]:
            continue
        lines += [f"## {rec['title']}  ({purl})", ""]
        for block in rec["blocks"]:
            lines += ["> " + "\n> ".join(block["lines"]) if block["kind"] == "aside" else "\n".join(block["lines"]), ""]
        if rec["images"]:
            lines += ["Images: " + ", ".join(media[h]["name"] for h in rec["images"] if h in media), ""]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    for purl, rec in out.items():
        print(f"{purl:56} blocks {len(rec['blocks']):3d}  images {len(rec['images']):3d}")


if __name__ == "__main__":
    main()
