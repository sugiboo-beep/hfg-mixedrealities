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

## Colour

Neon green `#c8ff2e` is the signature, but it measures 1.03:1 against the paper and 16.1:1 against
the ink, so it is only ever a fill or a mark on a dark ground, never text on the page. Text accents
come from five section hues, each measured at 4.2:1 or better against the paper: green `#0a7d45`
for projects, blue `#1f3ae0` for research, violet `#7526bb` for people, pink `#d40f68` for events,
amber `#b4560a` for the archive. Every project cycles through the five, so browsing changes colour.
`tools/make_thumbnail.py` reads these values back out of the stylesheet, so the social card and
favicon never drift from the site.

## Korean

The lab's contributors write in Korean and one of the essays turns on Korean words, so the site's
own furniture carries a Korean gloss: the rail's groups, the section labels and the page heads. The
glossary is `korean` in `content/site.json`. The archived prose itself is never touched. The
hover-scramble effect churns through hangul syllables before settling into the label's own script.

## Navigation and type

Navigation is a fixed rail down the left edge, grouped by section, with a toggle at the top that
collapses it to a spine and gives the width back to the page. The choice is remembered in
`localStorage` across pages. Below 900 px the rail slides over the page instead, with a scrim.
Reading progress runs down the rail's right edge.

Two sans faces carry the whole site: Futura sets every headline, the rail's group heads and the
index, while Helvetica Neue Light handles running text and answers Futura word by word inside the
headline itself. Display type is uppercase and tracked rather than relying on thick-thin contrast.

## Motion

Hover: an image lifts off the paper on a soft cast shadow and drifts, each frame in its own way
(a slow sway, a shiver, a pendulum, a bob), while its neighbours recede and its caption slides in.
Nav labels scramble and resolve, index rows shift and colour, cards lean toward the cursor. Scrolling drives the rail's progress line, clip-path reveals and a
hero parallax. A soft light follows the pointer across the page.

Rotation, lift and wiggle are driven through the separate `rotate`, `translate` and `scale`
properties rather than one `transform`, so a resting tilt, a hover lift and a looping animation
can coexist without overwriting each other.

Two things are hidden: the diamond beside the wordmark tips every framed image off its axis and
back, and typing `lava` warms the page.

All of it is suppressed under `prefers-reduced-motion`, pointer effects only run for a fine
pointer, and the page is fully readable with scripting off.

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
