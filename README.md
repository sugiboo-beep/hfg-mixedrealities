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

    content/                    Site structure, prose, captions, source payloads
    tools/                      Scripts that fetch media and build the HTML from content/

## Rebuilding

    python3 tools/extract_content.py
    python3 tools/build.py

`tools/fetch_media.py` only needs rerunning if the images are missing or the source adds new ones.
