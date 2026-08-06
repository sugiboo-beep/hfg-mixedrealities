"""Render the static site from the content model.

Inputs are ``content/site.json`` (structure, navigation, curated captions), ``content/text.json``
(prose, gallery ordering and collage coordinates extracted from the source pages) and
``content/media_index.json`` (media hash -> downloaded file). Output is plain HTML with no
framework dependency; layout comes from ``assets/css/site.css``.
"""

import hashlib
import html
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"


class Media:
    """Local image library keyed by the source site's media hash."""

    def __init__(self, index: dict, captions: dict):
        self.index = index
        self.captions = captions

    def __contains__(self, media_hash: str) -> bool:
        return media_hash in self.index

    def full(self, media_hash: str) -> str:
        return "assets/img/full/" + self.index[media_hash]["file"]

    def thumb(self, media_hash: str) -> str:
        return "assets/img/thumb/" + self.index[media_hash]["file"]

    def ratio(self, media_hash: str) -> float:
        rec = self.index[media_hash]
        return rec["w"] / rec["h"] if rec["h"] else 1.0

    def size(self, media_hash: str) -> tuple[int, int]:
        rec = self.index[media_hash]
        return rec["w"], rec["h"]

    def caption(self, media_hash: str) -> str:
        return self.captions.get(media_hash, "Untitled")


class Collage:
    """A freeform arrangement, packed onto a canvas 100 units wide.

    Every coordinate is a percentage of the gallery's width, the unit the source site also uses,
    so the whole arrangement scales with its column. Placement is a skyline pack: each image goes
    into whichever lane currently reaches least far down, which keeps the lanes level and leaves no
    holes, while per-image width, indent and rotation vary so the result still reads as hand-placed.
    The source's own ``freeform-scale`` is carried over as a size hint, so images the lab showed
    large stay large.
    """

    #: Widths, as a fraction of a lane, cycled through to give the collage rhythm.
    WIDTHS = (1.0, 0.78, 0.92, 0.7, 1.0, 0.84)
    #: Fraction of the leftover lane space used as an indent, cycled likewise.
    INDENTS = (0.0, 0.62, 0.28, 1.0, 0.15, 0.75)
    #: Vertical breathing room between stacked images, and below the lowest one.
    GUTTER = 4.0
    TAIL = 2.0

    def __init__(self, media: Media, hashes: list[str], hints: dict | None = None, lanes: int = 3):
        self.media = media
        self.hashes = [h for h in hashes if h in media]
        self.hints = hints or {}
        self.lanes = max(1, min(lanes, len(self.hashes) or 1))
        self.items = self._pack()

    def __bool__(self) -> bool:
        return bool(self.items)

    def _weight(self, media_hash: str) -> float:
        """How large this image should read relative to a full lane, from the source's own scale."""
        hint = self.hints.get(media_hash)
        if not hint:
            return 1.0
        #: Source scales run roughly 13-60 units wide; map that onto a 0.78-1.0 lane fraction.
        return min(1.0, max(0.78, 0.78 + (hint - 13.0) / 47.0 * 0.22))

    def _order(self) -> list[str]:
        """Tallest first. A skyline pack levels out only if the bulky images are placed early."""
        return sorted(self.hashes, key=lambda h: self.media.ratio(h))

    def _pack(self) -> list[dict]:
        lane_w = (100.0 - self.GUTTER * (self.lanes - 1)) / self.lanes
        skyline = [0.0] * self.lanes
        items = []

        for i, media_hash in enumerate(self._order()):
            #: Every fifth image runs across two lanes, so the collage has a few large moments.
            #: Held back until every lane has been seeded, or the wide image strands a lane empty.
            wide = self.lanes >= 3 and i >= self.lanes and i % 5 == 2
            if wide:
                #: Pair the two lanes that are both low and level, so no dead space opens above.
                lane = min(
                    range(self.lanes - 1),
                    key=lambda n: (
                        max(skyline[n], skyline[n + 1]) + abs(skyline[n] - skyline[n + 1]),
                        n,
                    ),
                )
                room = lane_w * 2 + self.GUTTER
                y = max(skyline[lane], skyline[lane + 1])
            else:
                lane = min(range(self.lanes), key=lambda n: (skyline[n], n))
                room = lane_w
                y = skyline[lane]

            width = room * self.WIDTHS[i % len(self.WIDTHS)] * self._weight(media_hash)
            x = lane * (lane_w + self.GUTTER) + (room - width) * self.INDENTS[i % len(self.INDENTS)]
            bottom = y + width / self.media.ratio(media_hash) + self.GUTTER

            items.append(
                {
                    "hash": media_hash,
                    "x": round(x, 3),
                    "y": round(y, 3),
                    "w": round(width, 3),
                    "z": i + 1,
                    "tilt": round(((i * 5) % 7 - 3) * 0.55, 2),
                }
            )
            skyline[lane] = bottom
            if wide:
                skyline[lane + 1] = bottom

        return items

    @property
    def height(self) -> float:
        """Container height as a percentage of its width."""
        return max(
            (i["y"] + i["w"] / self.media.ratio(i["hash"]) for i in self.items), default=100.0
        ) + self.TAIL


class Page:
    """One output HTML file, aware of its own depth below the site root."""

    def __init__(self, builder: "SiteBuilder", path: str, title: str, description: str):
        self.builder = builder
        self.path = path
        self.title = title
        self.description = description
        self.depth = path.count("/")

    def url(self, target: str) -> str:
        """Rewrite a root-relative site path for this page's directory depth."""
        if target.startswith(("http://", "https://", "#", "mailto:")):
            return target
        return "../" * self.depth + target

    def asset(self, target: str) -> str:
        """As :meth:`url`, with a content fingerprint so a rebuilt asset is never served stale."""
        digest = hashlib.md5((ROOT / target).read_bytes()).hexdigest()[:8]
        return f"{self.url(target)}?v={digest}"

    def render(self, body: str) -> str:
        meta = self.builder.site["meta"]
        full_title = self.title if self.title == meta["title"] else f"{self.title} — {meta['title']}"
        return TEMPLATE.format(
            title=esc(full_title),
            description=esc(self.description),
            css=self.asset("assets/css/site.css"),
            glightbox_css=self.asset("assets/vendor/glightbox/glightbox.min.css"),
            glightbox_js=self.asset("assets/vendor/glightbox/glightbox.min.js"),
            js=self.asset("assets/js/site.js"),
            header=self.builder.header(self),
            body=body,
            footer=self.builder.footer(self),
        )

    def write(self, body: str) -> None:
        out = ROOT / self.path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(self.render(body), encoding="utf-8")


class SiteBuilder:
    """Assemble every page of the site."""

    def __init__(self):
        self.site = json.loads((CONTENT / "site.json").read_text(encoding="utf-8"))
        self.text = json.loads((CONTENT / "text.json").read_text(encoding="utf-8"))
        self.media = Media(
            json.loads((CONTENT / "media_index.json").read_text(encoding="utf-8")),
            self.site["captions"],
        )
        self.library = json.loads((CONTENT / "source" / "media.json").read_text(encoding="utf-8"))

    # ------------------------------------------------------------ chrome

    def header(self, page: Page) -> str:
        """The left rail: wordmark, grouped navigation and the page controls."""
        groups = []
        for entry in self.site["nav"]:
            children = entry.get("children") or []
            label = esc(entry["label"])
            if entry.get("href"):
                head = f'<a class="group-head" href="{page.url(entry["href"])}"><span data-scramble>{label}</span></a>'
            else:
                head = f'<span class="group-head">{label}</span>'
            links = "".join(
                f'<li><a class="link-sweep" href="{page.url(c["href"])}">{esc(c["label"])}</a></li>'
                for c in children
            )
            sub = f'<ul class="group-list">{links}</ul>' if links else ""
            groups.append(f'<li class="nav-group">{head}{sub}</li>')

        meta = self.site["meta"]
        inst = meta["institution"]
        words = meta["title"].split()
        stack = "".join(f"<span>{esc(w)}</span>" for w in words)

        return f"""<button class="rail-toggle" type="button" aria-expanded="true" aria-controls="rail" aria-label="Toggle navigation">
  <span class="bar"></span><span class="bar"></span>
</button>
<aside class="rail" id="rail">
  <a class="wordmark" href="{page.url('index.html')}">{stack}</a>
  <nav class="rail-nav"><ul>{''.join(groups)}</ul></nav>
  <div class="rail-foot">
    <a class="link-sweep" href="{esc(inst['url'])}" target="_blank" rel="noopener">{esc(inst['label'])}</a>
    <button class="sigil" type="button" aria-label="Unsettle the page" title="Unsettle">&#9670;</button>
  </div>
  <div class="rail-progress"><span></span></div>
</aside>
<div class="rail-scrim" hidden></div>"""

    def footer(self, page: Page) -> str:
        meta = self.site["meta"]
        cols = []
        for entry in self.site["nav"]:
            children = entry.get("children") or []
            if not children:
                continue
            links = "".join(
                f'<li><a class="link-sweep" href="{page.url(c["href"])}">{esc(c["label"])}</a></li>'
                for c in children
            )
            cols.append(f'<div><h3>{esc(entry["label"])}</h3><ul>{links}</ul></div>')

        inst = meta["institution"]
        return f"""<footer class="site-foot">
  <div class="shell">
    <h2 class="foot-mark reveal"><span>Mixed realities,</span><span>digital grounds.</span></h2>
    <div class="foot-cols reveal">
      {''.join(cols)}
      <div>
        <h3>Institution</h3>
        <ul>
          <li><a class="link-sweep" href="{esc(inst['url'])}" target="_blank" rel="noopener">{esc(inst['label'])}</a></li>
          <li><a class="link-sweep" href="{page.url('gallery.html')}">Image archive</a></li>
        </ul>
      </div>
    </div>
    <div class="colophon">
      <span>{esc(meta['title'])} &mdash; {esc(meta['tagline'])}</span>
      <span>Content archived from <a class="link-sweep" href="{esc(meta['source'])}" target="_blank" rel="noopener">{esc(meta['source'].replace('https://', ''))}</a></span>
    </div>
  </div>
  <button class="to-top" type="button" aria-label="Back to top" data-magnet>&#8593;</button>
</footer>"""

    # ----------------------------------------------------------- helpers

    def prose(self, source: str, skip: int = 0) -> str:
        blocks = self.text.get(source, {}).get("blocks", [])[skip:]
        out = []
        for block in blocks:
            body = "<br>".join(esc(line) for line in block["lines"])
            if block["kind"] == "aside":
                out.append(f'<div class="aside reveal">{body}</div>')
            else:
                out.append(f'<p class="reveal">{body}</p>')
        return "\n".join(out)

    def tile(self, page: Page, media_hash: str, gallery: str, caption=None, style="", extra="") -> str:
        cap = caption or self.media.caption(media_hash)
        width, height = self.media.size(media_hash)
        return f"""<a class="tile glightbox reveal" href="{page.url(self.media.full(media_hash))}"
   data-gallery="{gallery}" data-title="{esc(cap)}"{style}{extra}>
  <img src="{page.url(self.media.thumb(media_hash))}" alt="{esc(cap)}" loading="lazy" width="{width}" height="{height}" draggable="false">
  <span class="tile-cap">{esc(cap)}</span>
</a>"""

    def gallery(self, page: Page, hashes: list[str], gallery: str, layout: str = "gallery", captions=None) -> str:
        captions = captions or {}
        tiles = "\n".join(
            self.tile(page, h, gallery, captions.get(h)) for h in hashes if h in self.media
        )
        return f'<div class="{layout}">\n{tiles}\n</div>'

    def collage(self, page: Page, source: str, gallery: str, lanes: int = 3) -> str:
        """Lay a page's images out as a packed freeform collage."""
        record = self.text.get(source, {})
        hashes = [h for h in record.get("images", []) if h in self.media]
        if len(hashes) < 3:
            return ""

        hints = {f["hash"]: f["scale"] for f in record.get("freeform", [])}
        placement = Collage(self.media, hashes, hints, lanes)
        captions = record.get("captions", {})

        tiles = []
        for item in placement.items:
            style = (
                f' style="--x:{item["x"]};--y:{item["y"]};'
                f'--w:{item["w"]};--z:{item["z"]};--tilt:{item["tilt"]}deg"'
            )
            tiles.append(
                self.tile(page, item["hash"], gallery, captions.get(item["hash"]), style)
            )
        return (
            f'<div class="collage" style="--ff-h:{placement.height:.2f}" data-collage>\n'
            + "\n".join(tiles)
            + "\n</div>"
        )

    def library_for(self, source: str) -> list[str]:
        """Every media hash the source site holds for a page, in upload order."""
        for record in self.library:
            if record["purl"] == source:
                return [m["hash"] for m in record["media"]]
        return []

    def placeholder(self) -> str:
        return f'<p class="note reveal">{esc(self.site["placeholder"])}</p>'

    @staticmethod
    def label(left: str, right: str = "") -> str:
        return f'<div class="section-label reveal"><span>{left}</span><span>{right}</span></div>'

    # ------------------------------------------------------------- pages

    def build(self) -> None:
        self.build_home()
        self.build_gallery()
        self.build_projects_index()
        for project in self.site["projects"]:
            self.build_project(project)
        for work in self.site["works"]:
            self.build_work(work)
        for section in self.site["sections"]:
            self.build_section(section)

    def build_home(self) -> None:
        meta = self.site["meta"]
        page = Page(self, "index.html", meta["title"], meta["intro"])

        faces = meta.get("headline_faces", {})
        headline = " ".join(
            f'<span class="word {faces.get(w, "")}">{esc(w)}</span>' for w in meta["title"].split()
        )
        cards = "\n".join(
            f"""<a class="card-work reveal" href="{page.url('works/' + w['slug'] + '.html')}" data-tilt>
  <span class="frame"><img src="{page.url(self.media.thumb(w['cover']))}" alt="{esc(w['title'])}" loading="lazy"></span>
  <span class="meta">
    <span class="by">{esc(w['author'])}</span>
    <span class="name" data-scramble>{esc(w['title'])}</span>
  </span>
</a>"""
            for w in self.site["works"]
        )

        inst = meta["institution"]
        body = f"""<main>
  <section class="hero shell">
    <p class="kicker reveal">{esc(meta['tagline'])} &#183; <a class="link-inline" href="{esc(inst['url'])}" target="_blank" rel="noopener">{esc(inst['label'])}</a></p>
    <h1 data-parallax="0.12">{headline}</h1>
    <div class="hero-meta">
      <span>Media Art</span><span class="dot">&#9670;</span>
      <span>Karlsruhe</span><span class="dot">&#9670;</span>
      <span>Seminars &amp; Field Work</span>
    </div>
    <p class="lede reveal">{esc(meta['intro'])}</p>
    <p class="scroll-hint reveal"><span>Scroll</span></p>
  </section>

  <section class="shell band">
    {self.label('Selected works', 'Archive')}
    {self.collage(page, 'home-page', 'home', lanes=3)}
    <p class="more reveal"><a class="link-inline" href="{page.url('gallery.html')}">Enter the full image archive &#8594;</a></p>
  </section>

  <section class="shell band">
    {self.label('Contributions', 'The Floor is Lava')}
    <div class="cards">{cards}</div>
  </section>

  <section class="shell band">
    {self.label('Projects', f"{len(self.site['projects'])} entries")}
    {self.project_index(page)}
  </section>
</main>
<div class="peek"><img src="" alt=""></div>"""
        page.write(body)

    def project_index(self, page: Page) -> str:
        rows = []
        for i, project in enumerate(self.site["projects"], start=1):
            blocks = self.text.get(project["source"], {}).get("blocks", [])
            raw = blocks[1]["lines"][0] if len(blocks) > 1 else ""
            blurb = esc(raw[:150].rsplit(" ", 1)[0]) + "&#8230;" if len(raw) > 150 else esc(raw)
            subtitle = f'<em>{esc(project["subtitle"])}</em>' if project.get("subtitle") else ""
            cover = project.get("cover")
            peek = page.url(self.media.thumb(cover)) if cover in self.media else ""
            rows.append(
                f"""<a class="index-row reveal" href="{page.url('projects/' + project['slug'] + '.html')}" data-peek="{peek}">
  <span class="num">{i:02d}</span>
  <span class="name"><span data-scramble>{esc(project['title'])}</span>{subtitle}</span>
  <span class="blurb">{blurb}</span>
  <span class="go">&#8594;</span>
</a>"""
            )
        return f'<div class="index-list">{"".join(rows)}</div>'

    def build_projects_index(self) -> None:
        page = Page(self, "projects/index.html", "Projects", "Seminars, collaborations and field work of the lab.")
        body = f"""<main>
  <section class="page-head shell">
    <p class="kicker reveal">Index</p>
    <h1 class="reveal">Projects</h1>
    <p class="lede reveal">Seminars and collaborations developed with museums, archives and cultural institutions, each ending in an exhibition, a publication or a field trip.</p>
  </section>
  <section class="shell band">{self.project_index(page)}</section>
</main>
<div class="peek"><img src="" alt=""></div>"""
        page.write(body)

    def build_project(self, project: dict) -> None:
        source = project["source"]
        record = self.text.get(source, {})
        slug = project["slug"]
        blocks = record.get("blocks", [])
        summary = blocks[1]["lines"][0][:160] if len(blocks) > 1 else project["title"]
        page = Page(self, f"projects/{slug}.html", project["title"], summary)

        images = [h for h in record.get("images", []) if h in self.media]
        subtitle = f'<em>{esc(project["subtitle"])}</em>' if project.get("subtitle") else ""

        collage = self.collage(page, source, slug, lanes=2)
        if collage:
            visual = self.label("Images", str(len(images))) + collage
        elif images:
            visual = self.label("Images", str(len(images))) + self.gallery(
                page, images, slug, captions=record.get("captions", {})
            )
        else:
            visual = self.label("Images", "&#8212;") + self.placeholder()

        works = ""
        if project.get("works_source"):
            linked = self.text.get(project["works_source"], {})
            caps = linked.get("captions", {})
            cards = []
            for h, target in linked.get("links", {}).items():
                work = next((w for w in self.site["works"] if w["slug"] == target), None)
                if h not in self.media or not work:
                    continue
                cards.append(
                    f"""<a class="card-work reveal" href="{page.url('works/' + work['slug'] + '.html')}" data-tilt>
  <span class="frame"><img src="{page.url(self.media.thumb(h))}" alt="{esc(caps.get(h, work['author']))}" loading="lazy"></span>
  <span class="meta"><span class="by">{esc(work['author'])}</span><span class="name" data-scramble>{esc(work['title'])}</span></span>
</a>"""
                )
            if cards:
                works = f"""<section class="shell band">
  {self.label('Contributions', str(len(cards)))}
  <p class="lede reveal">{esc(project['works_intro'])}</p>
  <div class="cards">{''.join(cards)}</div>
</section>"""

        body = f"""<main>
  <section class="page-head shell">
    <p class="kicker reveal">{esc(project.get('kicker', 'Project'))}</p>
    <h1 class="reveal">{esc(project['title'])}{subtitle}</h1>
  </section>
  <section class="shell">
    <div class="cols">
      <div class="c-5"><div class="sticky-col prose">{self.prose(source, skip=1) or self.placeholder()}</div></div>
      <div class="c-7">{visual}</div>
    </div>
  </section>
  {works}
  <section class="shell band">{self.pager(page, 'projects', slug)}</section>
</main>"""
        page.write(body)

    def build_work(self, work: dict) -> None:
        source = work["source"]
        record = self.text.get(source, {})
        page = Page(self, f"works/{work['slug']}.html", f"{work['title']} — {work['author']}", work["title"])
        images = [h for h in record.get("images", []) if h in self.media]
        parent = next(p for p in self.site["projects"] if p["slug"] == work["project"])

        subtitle = f'<em>{esc(work["subtitle"])}</em>' if work.get("subtitle") else ""
        note = f'<span>{esc(work["note"])}</span>' if work.get("note") else ""

        if images:
            text_class, aside = "c-7", f"""<div class="c-5">
        <div class="sticky-col">{self.gallery(page, images, work['slug'], layout='gallery gallery-tight')}</div>
      </div>"""
        else:
            text_class, aside = "c-8 c-centre", ""

        body = f"""<main>
  <section class="page-head shell">
    <p class="kicker reveal"><a class="link-inline" href="{page.url('projects/' + parent['slug'] + '.html')}">{esc(parent['title'])}</a></p>
    <h1 class="reveal">{esc(work['title'])}{subtitle}</h1>
    <p class="hero-meta reveal"><span>{esc(work['author'])}</span>{note}</p>
  </section>
  <section class="shell">
    <div class="cols">
      <div class="{text_class}"><div class="prose">{self.prose(source, skip=work.get('skip', 2))}</div></div>
      {aside}
    </div>
  </section>
  <section class="shell band">{self.pager(page, 'works', work['slug'])}</section>
</main>"""
        page.write(body)

    def build_section(self, section: dict) -> None:
        source = section["source"]
        record = self.text.get(source, {})
        page = Page(self, f"{section['slug']}.html", section["title"], f"{section['title']} — {section['group']}")
        images = [h for h in record.get("images", []) if h in self.media] or [
            h for h in self.library_for(source) if h in self.media
        ]
        prose = self.prose(source) or self.placeholder()
        if images:
            text_class = "c-6"
            aside = f'<div class="c-6">{self.gallery(page, images, section["slug"])}</div>'
        else:
            text_class, aside = "c-8", ""

        body = f"""<main>
  <section class="page-head shell">
    <p class="kicker reveal">{esc(section['group'])}</p>
    <h1 class="reveal">{esc(section['title'])}</h1>
  </section>
  <section class="shell">
    <div class="cols">
      <div class="{text_class}"><div class="prose">{prose}</div></div>
      {aside}
    </div>
  </section>
  <section class="shell band">{self.pager(page, 'sections', section['slug'])}</section>
</main>"""
        page.write(body)

    def build_gallery(self) -> None:
        page = Page(self, "gallery.html", "Image archive", "Every image held by the lab's site, in one gallery.")
        seen, hashes = set(), []
        for record in self.library:
            for m in record["media"]:
                if m["hash"] in self.media and m["hash"] not in seen:
                    seen.add(m["hash"])
                    hashes.append(m["hash"])

        body = f"""<main>
  <section class="page-head shell">
    <p class="kicker reveal">Archive</p>
    <h1 class="reveal">Image archive</h1>
    <p class="lede reveal">Every image held across the lab's pages, in one gallery. Select any frame to open it full size.</p>
  </section>
  <section class="shell band">
    {self.label('All images', f'{len(hashes)} frames')}
    {self.gallery(page, hashes, "archive")}
  </section>
</main>"""
        page.write(body)

    # ------------------------------------------------------------- pager

    def pager(self, page: Page, group: str, slug: str) -> str:
        if group == "projects":
            items = [(p["slug"], p["title"], "projects/" + p["slug"] + ".html") for p in self.site["projects"]]
        elif group == "works":
            items = [(w["slug"], w["title"], "works/" + w["slug"] + ".html") for w in self.site["works"]]
        else:
            items = [(s["slug"], s["title"], s["slug"] + ".html") for s in self.site["sections"]]

        i = next((n for n, item in enumerate(items) if item[0] == slug), 0)
        prev = items[i - 1]
        nxt = items[(i + 1) % len(items)]
        return f"""<nav class="pager">
  <a class="prev" href="{page.url(prev[2])}"><span class="tag">Previous</span><span data-scramble>{esc(prev[1])}</span></a>
  <a class="next" href="{page.url(nxt[2])}"><span class="tag">Next</span><span data-scramble>{esc(nxt[1])}</span></a>
</nav>"""


def esc(value: str) -> str:
    return html.escape(value or "", quote=True)


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<script>document.documentElement.className += " has-js";</script>
<link rel="stylesheet" href="{glightbox_css}">
<link rel="stylesheet" href="{css}">
</head>
<body>
<div class="curtain" aria-hidden="true"><span class="curtain-mark">&#9670;</span></div>
<div class="spotlight" aria-hidden="true"></div>
{header}
<div class="page">
{body}
{footer}
</div>
<div class="toast" role="status" aria-live="polite"></div>
<script src="{glightbox_js}"></script>
<script src="{js}"></script>
</body>
</html>
"""


if __name__ == "__main__":
    for stale in ("projects", "works", "research", "people", "events"):
        shutil.rmtree(ROOT / stale, ignore_errors=True)
    SiteBuilder().build()
    built = sorted(p.relative_to(ROOT) for p in ROOT.rglob("*.html") if "source" not in p.parts)
    print(f"built {len(built)} pages")
