# Mixed Realities and Digitalities Lab

A static site rebuilt from the Cargo site at <https://1019911-copy4.cargo.site>. All text and
images are archived locally, so the site runs with no network access. No CSS framework: layout,
type and motion are hand-written, and the only third-party file is the lightbox.

## Viewing

Open `index.html` directly, or serve the directory:

    python3 -m http.server 8811
    open -a Safari http://127.0.0.1:8811/index.html

## Layout

    index.html                  Home: hero, collage, contributions, project index
    gallery.html                Full image archive, 33 frames, lightbox
    projects/index.html         Project index
    projects/*.html             One page per seminar or collaboration
    works/*.html                Student contributions to The Floor is Lava
    research/, people/, events/ Remaining sections of the source navigation

    assets/css/site.css         Everything visual
    assets/js/site.js           Interaction layer
    assets/img/full/            Images at 1800 px for the lightbox
    assets/img/thumb/           Images at 700 px for galleries
    assets/vendor/glightbox/    GLightbox 3.3.1, vendored

    content/site.json           Site structure, navigation, curated image captions
    content/text.json           Prose, gallery ordering and collage coordinates
    content/text.md             The same text as a plain reading archive
    content/media_index.json    Media hash to local file mapping
    content/source/             Raw payloads pulled from the source site

    tools/fetch_media.py        Download the image library
    tools/extract_content.py    Convert the source page payloads into the content model
    tools/build.py              Render the HTML

## Rebuilding

    python3 tools/extract_content.py
    python3 tools/build.py

`tools/fetch_media.py` only needs rerunning if the images are missing or the source adds new ones.

## The collage

Galleries on the home and project pages are laid out by `Collage` in `tools/build.py`, not by the
browser. Images are placed tallest first into whichever lane currently reaches least far down, so
the lanes finish level and no holes open up; width, indent and a small rotation vary per image so
the result still reads as hand-placed, and every fifth image runs across two lanes to break the
rhythm. Coordinates are percentages of the gallery's width, the same unit the source site used, so
the whole arrangement scales with its column. Below 900 px it stacks into ordinary columns.

## Motion

Hover: images lift and warm up while their neighbours recede, captions slide in, nav labels
scramble and resolve, index rows shift with a preview thumbnail that tracks the pointer, cards lean
toward the cursor. Scrolling drives a progress hairline, clip-path reveals, a hero parallax, and a
marquee whose speed and direction follow the scroll. A soft light follows the pointer across the
page. Collage images can be dragged around and stay where they are put; the pointer stays the
system cursor throughout, and native cursors carry the affordance (grab over a collage, zoom over a
gallery frame).

Two things are hidden: the diamond beside the wordmark tips every framed image off its axis and
back, and typing `lava` warms the page.

All of it is suppressed under `prefers-reduced-motion`, the custom cursor and pointer effects only
run for a fine pointer, and the page is fully readable with scripting off.

## Notes on fidelity

- Pages that are empty on the source site (Publications, Cooperations, Students, Alumni, Teaching
  Bodies, Exhibitions, Rundgang, Festivals) are kept in the structure and carry a short note saying
  so, rather than being filled with invented content.
- Project pages have cover images only where the source site actually associates images with that
  project. The other projects hold no media on the source.
- Image captions come from the source where a `figcaption` exists, otherwise from the uploaded file
  names; files whose names carry no title are captioned "Untitled".
- The one external link on the source site, HfG Karlsruhe, is carried through in the header of the
  home page and in the footer of every page.
