"""Draw the site's social thumbnail and favicon from the palette.

The card is generated rather than hand-drawn so it stays in step with ``assets/css/site.css``:
the colours are read out of the stylesheet's custom properties, and a change there flows through
to the image on the next build.
"""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSS = ROOT / "assets" / "css" / "site.css"
OUT = ROOT / "assets" / "img" / "meta"


class Palette:
    """The custom properties the stylesheet defines on ``:root``."""

    def __init__(self, css: str):
        block = css[css.index(":root {") : css.index("}", css.index(":root {"))]
        self.values = dict(re.findall(r"--([a-z-]+):\s*([^;]+);", block))

    def __getitem__(self, name: str) -> str:
        return self.values[name].strip()


class Thumbnail:
    """A 1200x630 card: the wordmark over a band of the site's section hues."""

    WIDTH = 1200
    HEIGHT = 630

    def __init__(self, palette: Palette):
        self.p = palette
        self.hues = [palette[n] for n in ("green", "blue", "violet", "pink", "amber")]

    def bands(self) -> str:
        """A stripe per section hue along the lower edge, widths stepping unevenly."""
        spans = [0.26, 0.18, 0.22, 0.14, 0.20]
        out, x = [], 0.0
        for hue, span in zip(self.hues, spans):
            w = span * self.WIDTH
            out.append(
                f'<rect x="{x:.1f}" y="{self.HEIGHT - 96}" width="{w:.1f}" height="96" fill="{hue}"/>'
            )
            x += w
        return "\n  ".join(out)

    def marks(self) -> str:
        """Tilted frames, echoing the collage on the home page."""
        placed = [(770, 120, 190, 250, -4), (930, 250, 150, 200, 3), (700, 330, 160, 130, 6)]
        out = []
        for i, (x, y, w, h, rot) in enumerate(placed):
            hue = self.hues[i % len(self.hues)]
            out.append(
                f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="none" stroke="{hue}"'
                f' stroke-width="3" transform="rotate({rot} {x + w / 2} {y + h / 2})"/>'
            )
        return "\n  ".join(out)

    def svg(self) -> str:
        return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{self.WIDTH}" height="{self.HEIGHT}"
     viewBox="0 0 {self.WIDTH} {self.HEIGHT}">
  <rect width="{self.WIDTH}" height="{self.HEIGHT}" fill="{self.p['paper']}"/>
  {self.marks()}
  <g font-family="Futura, 'Avenir Next', 'Century Gothic', sans-serif" fill="{self.p['ink']}">
    <text x="80" y="196" font-size="86" letter-spacing="-1">MIXED</text>
    <text x="80" y="286" font-size="86" letter-spacing="-1" fill="{self.p['green']}">REALITIES</text>
    <text x="80" y="376" font-size="86" letter-spacing="-1">DIGITALITIES</text>
  </g>
  <g font-family="Helvetica Neue, Helvetica, Arial, sans-serif" fill="{self.p['ink-soft']}">
    <text x="80" y="440" font-size="30" letter-spacing="4" font-weight="300">LAB</text>
    <text x="80" y="492" font-size="23" letter-spacing="3">MEDIENKUNST &#183; HFG KARLSRUHE</text>
  </g>
  <rect x="80" y="{self.HEIGHT - 96}" width="0" height="0" fill="none"/>
  {self.bands()}
  <rect x="0" y="{self.HEIGHT - 104}" width="{self.WIDTH}" height="8" fill="{self.p['acid']}"/>
</svg>"""

    def favicon(self) -> str:
        """A neon square carrying the lab's initial, small enough to read in a tab."""
        return f"""<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
  <rect width="64" height="64" fill="{self.p['ink']}"/>
  <rect x="6" y="6" width="52" height="52" fill="none" stroke="{self.p['acid']}" stroke-width="4"/>
  <text x="32" y="45" text-anchor="middle" font-size="34"
        font-family="Futura, 'Avenir Next', 'Century Gothic', sans-serif"
        fill="{self.p['acid']}">M</text>
</svg>"""


#: Preferred rasteriser: it renders the same font stack the site uses, so the card matches the page.
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def render(svg_path: Path, png_path: Path, width: int, height: int) -> bool:
    """Rasterise the SVG. The SVG stays the source of truth; the PNG is for platforms needing one."""
    attempts = [
        [
            CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
            f"--window-size={width},{height}", f"--screenshot={png_path}",
            "--default-background-color=00000000", str(svg_path),
        ],
        ["rsvg-convert", "-w", str(width), str(svg_path), "-o", str(png_path)],
    ]
    for cmd in attempts:
        try:
            subprocess.run(cmd, capture_output=True, timeout=60)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
        if png_path.exists() and png_path.stat().st_size > 2000:
            return True
    return False


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    thumb = Thumbnail(Palette(CSS.read_text(encoding="utf-8")))

    (OUT / "thumbnail.svg").write_text(thumb.svg(), encoding="utf-8")
    (OUT / "favicon.svg").write_text(thumb.favicon(), encoding="utf-8")

    ok = render(OUT / "thumbnail.svg", OUT / "thumbnail.png", thumb.WIDTH, thumb.HEIGHT)
    for name in ("thumbnail.svg", "favicon.svg", "thumbnail.png" if ok else ""):
        if name and (OUT / name).exists():
            print(f"  {OUT.relative_to(ROOT)}/{name}  {(OUT / name).stat().st_size:,} bytes")
    if not ok:
        print("  PNG not written: no rasteriser available")
