/* Interaction layer: navigation, reveals, pointer effects, page transitions and the lightbox.
   Each behaviour is a small class; Site wires them up and drives the shared animation frame. */

(function () {
  "use strict";

  var CALM = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var FINE = window.matchMedia("(pointer: fine)").matches;

  function lerp(a, b, t) {
    return a + (b - a) * t;
  }

  /* ------------------------------------------------------------- chrome */

  /** The left rail: collapsible on wide screens, sliding over the page on narrow ones. */
  function Rail() {
    this.root = document.documentElement;
    this.toggle = document.querySelector(".rail-toggle");
    this.rail = document.querySelector(".rail");
    this.scrim = document.querySelector(".rail-scrim");
    if (!this.toggle || !this.rail) return;

    var self = this;
    this.narrow = window.matchMedia("(max-width: 900px)");
    this.apply(this.narrow.matches ? false : this.remembered());

    this.toggle.addEventListener("click", function () {
      self.apply(!self.isOpen());
    });

    if (this.scrim) {
      this.scrim.removeAttribute("hidden");
      this.scrim.addEventListener("click", function () {
        self.apply(false);
      });
    }

    this.rail.addEventListener("click", function (event) {
      if (event.target.closest("a") && self.narrow.matches) self.apply(false);
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && self.narrow.matches) self.apply(false);
    });

    this.narrow.addEventListener("change", function (event) {
      self.apply(event.matches ? false : self.remembered());
    });
  }

  Rail.prototype.isOpen = function () {
    return !this.root.classList.contains("nav-closed");
  };

  Rail.prototype.remembered = function () {
    try {
      return window.localStorage.getItem("rail") !== "closed";
    } catch (err) {
      return true;
    }
  };

  Rail.prototype.apply = function (open) {
    this.root.classList.toggle("nav-closed", !open);
    this.root.classList.toggle("nav-open", open && this.narrow.matches);
    this.toggle.setAttribute("aria-expanded", String(open));
    if (this.narrow.matches) return;
    try {
      window.localStorage.setItem("rail", open ? "open" : "closed");
    } catch (err) {
      /* Private browsing; the rail simply opens by default next time. */
    }
  };

  /** Sticky-header shadow, reading progress and the back-to-top button. */
  function ScrollChrome() {
    this.bar = document.querySelector(".rail-progress span");
    this.top = document.querySelector(".to-top");

    var self = this;
    window.addEventListener("scroll", function () {
      self.update();
    }, { passive: true });
    window.addEventListener("resize", function () {
      self.update();
    });
    if (this.top) {
      this.top.addEventListener("click", function () {
        window.scrollTo({ top: 0, behavior: CALM ? "auto" : "smooth" });
      });
    }
    this.update();
  }

  ScrollChrome.prototype.update = function () {
    var y = window.scrollY || 0;
    var span = document.documentElement.scrollHeight - window.innerHeight;

    if (this.bar) this.bar.style.height = (span > 0 ? (y / span) * 100 : 0) + "%";
    if (this.top) this.top.classList.toggle("is-on", y > window.innerHeight * 0.8);
  };

  /** Fade and wipe elements in as they enter the viewport, staggered within a group. */
  function Reveal() {
    var targets = document.querySelectorAll(".reveal");
    if (!targets.length) return;

    if (CALM || !("IntersectionObserver" in window)) {
      targets.forEach(function (el) {
        el.classList.add("is-visible");
      });
      return;
    }

    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry, i) {
          if (!entry.isIntersecting) return;
          setTimeout(function () {
            entry.target.classList.add("is-visible");
          }, Math.min(i, 8) * 65);
          observer.unobserve(entry.target);
        });
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.05 }
    );

    targets.forEach(function (el) {
      observer.observe(el);
    });
  }

  /* -------------------------------------------------------- pointer fx */

  /** Soft paper light that follows the pointer. */
  function Spotlight() {
    var light = document.querySelector(".spotlight");
    if (!light || !FINE || CALM) return;

    window.addEventListener("pointermove", function (event) {
      light.classList.add("is-on");
      light.style.setProperty("--mx", event.clientX + "px");
      light.style.setProperty("--my", event.clientY + "px");
    }, { passive: true });

    document.addEventListener("pointerleave", function () {
      light.classList.remove("is-on");
    });
  }

  /** Elements that drift toward the pointer when it comes close. */
  function Magnet() {
    this.items = Array.prototype.map.call(document.querySelectorAll("[data-magnet]"), function (el) {
      return { el: el, x: 0, y: 0, tx: 0, ty: 0 };
    });
    if (!this.items.length || CALM || !FINE) return;

    var self = this;
    window.addEventListener("pointermove", function (event) {
      self.items.forEach(function (item) {
        var box = item.el.getBoundingClientRect();
        var dx = event.clientX - (box.left + box.width / 2);
        var dy = event.clientY - (box.top + box.height / 2);
        var reach = Math.max(box.width, 140);
        var near = Math.hypot(dx, dy) < reach;
        item.tx = near ? dx * 0.22 : 0;
        item.ty = near ? dy * 0.3 : 0;
      });
    }, { passive: true });
  }

  Magnet.prototype.frame = function () {
    if (CALM || !FINE) return;
    this.items.forEach(function (item) {
      item.x = lerp(item.x, item.tx, 0.12);
      item.y = lerp(item.y, item.ty, 0.12);
      if (Math.abs(item.x) < 0.05 && Math.abs(item.y) < 0.05) {
        item.el.style.transform = "";
        return;
      }
      item.el.style.transform = "translate3d(" + item.x.toFixed(2) + "px," + item.y.toFixed(2) + "px,0)";
    });
  };

  /** Cards lean toward the pointer. */
  function Tilt() {
    if (CALM || !FINE) return;
    document.querySelectorAll("[data-tilt]").forEach(function (card) {
      card.addEventListener("pointermove", function (event) {
        var box = card.getBoundingClientRect();
        var dx = (event.clientX - box.left) / box.width - 0.5;
        var dy = (event.clientY - box.top) / box.height - 0.5;
        card.style.transform =
          "perspective(900px) rotateY(" + (dx * 7).toFixed(2) + "deg) rotateX(" +
          (-dy * 7).toFixed(2) + "deg) translateY(-6px)";
      });
      card.addEventListener("pointerleave", function () {
        card.style.transform = "";
      });
    });
  }

  /* -------------------------------------------------------------- text */

  /** Letters of a label churn briefly before settling back. */
  function Scramble() {
    if (CALM) return;
    /* A loose mix of caps and marks, so a label churns playfully before settling back. */
    var GLYPHS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ*+◆✦∴○△";

    document.querySelectorAll("[data-scramble]").forEach(function (el) {
      var target = el.textContent;
      var host = el.closest("a, button, .nav-item") || el;
      var timer = null;

      host.addEventListener("pointerenter", function () {
        var step = 0;
        clearInterval(timer);
        timer = setInterval(function () {
          step += 1;
          el.textContent = target
            .split("")
            .map(function (ch, i) {
              if (ch === " " || i < step * 1.6) return ch;
              return GLYPHS[Math.floor(Math.random() * GLYPHS.length)];
            })
            .join("");
          if (step * 1.6 > target.length) {
            clearInterval(timer);
            el.textContent = target;
          }
        }, 28);
      });

      host.addEventListener("pointerleave", function () {
        clearInterval(timer);
        el.textContent = target;
      });
    });
  }

  /** The hero headline lags slightly behind the scroll. */
  function Parallax() {
    this.items = document.querySelectorAll("[data-parallax]");
  }

  Parallax.prototype.frame = function () {
    if (CALM) return;
    var y = window.scrollY || 0;
    this.items.forEach(function (el) {
      var rate = parseFloat(el.getAttribute("data-parallax")) || 0.1;
      el.style.transform = "translate3d(0," + (-y * rate).toFixed(2) + "px,0)";
    });
  };

  /* --------------------------------------------- surprises and passage */

  function Toast() {
    this.el = document.querySelector(".toast");
    this.timer = null;
  }

  Toast.prototype.say = function (message) {
    if (!this.el) return;
    this.el.textContent = message;
    this.el.classList.add("is-on");
    clearTimeout(this.timer);
    var el = this.el;
    this.timer = setTimeout(function () {
      el.classList.remove("is-on");
    }, 2200);
  };

  /** The diamond in the header tips every framed thing off its axis, and back. */
  function Unsettle(toast) {
    var sigil = document.querySelector(".sigil");
    if (!sigil) return;
    var on = false;

    sigil.addEventListener("click", function () {
      on = !on;
      sigil.classList.toggle("is-on", on);
      document.querySelectorAll(".tile, .card-work").forEach(function (el, i) {
        el.style.setProperty("--chaos", on ? (((i * 7) % 13) - 6) * 0.9 + "deg" : "0deg");
      });
      toast.say(on ? "Unsettled" : "Settled");
    });
  }

  /** Typing the seminar's name warms the page. */
  function Ember(toast) {
    var word = "lava";
    var buffer = "";

    document.addEventListener("keydown", function (event) {
      if (event.key.length !== 1 || event.metaKey || event.ctrlKey) return;
      buffer = (buffer + event.key.toLowerCase()).slice(-word.length);
      if (buffer !== word || document.body.classList.contains("is-hot")) return;
      document.body.classList.add("is-hot");
      toast.say("The floor is lava");
      setTimeout(function () {
        document.body.classList.remove("is-hot");
      }, 2400);
    });
  }

  /** Ink wipe over the page between documents. */
  function Curtain() {
    var curtain = document.querySelector(".curtain");
    if (!curtain || CALM) return;

    curtain.classList.add("is-out");

    document.addEventListener("click", function (event) {
      var link = event.target.closest("a");
      if (!link || event.defaultPrevented || event.metaKey || event.ctrlKey || event.shiftKey) return;
      if (link.target === "_blank" || link.classList.contains("glightbox")) return;

      var url = link.getAttribute("href") || "";
      if (!url || url.charAt(0) === "#" || /^[a-z]+:/i.test(url)) return;

      event.preventDefault();
      curtain.classList.remove("is-out");
      curtain.classList.add("is-in");
      setTimeout(function () {
        window.location.href = link.href;
      }, 430);
    });

    /* Restore the page when the browser serves it from the back/forward cache. */
    window.addEventListener("pageshow", function (event) {
      if (!event.persisted) return;
      curtain.classList.remove("is-in");
      curtain.classList.add("is-out");
    });
  }

  /** Selected Works only: images can be dragged freely on the canvas. A real drag (past a small
      threshold) suppresses the click that would otherwise open the lightbox, so a plain click
      still opens it exactly as before; only motion beyond the threshold counts as a drag. */
  function FreeformCollage() {
    if (!("PointerEvent" in window)) return;
    var containers = document.querySelectorAll(".collage-freeform");
    if (!containers.length) return;

    containers.forEach(function (container) {
      var active = null;

      container.addEventListener("pointerdown", function (event) {
        if (event.button > 0) return;
        var tile = event.target.closest(".tile");
        if (!tile) return;
        var rect = tile.getBoundingClientRect();
        var hostRect = container.getBoundingClientRect();
        active = {
          tile: tile,
          pointerId: event.pointerId,
          startX: event.clientX,
          startY: event.clientY,
          originLeft: rect.left - hostRect.left,
          originTop: rect.top - hostRect.top,
          dragging: false
        };
        tile.setPointerCapture(event.pointerId);
      });

      container.addEventListener("pointermove", function (event) {
        if (!active || event.pointerId !== active.pointerId) return;
        var dx = event.clientX - active.startX;
        var dy = event.clientY - active.startY;
        if (!active.dragging && Math.hypot(dx, dy) > 6) {
          active.dragging = true;
          active.tile.classList.add("is-dragging");
        }
        if (active.dragging) {
          event.preventDefault();
          active.tile.style.left = active.originLeft + dx + "px";
          active.tile.style.top = active.originTop + dy + "px";
        }
      });

      function release(event) {
        if (!active || event.pointerId !== active.pointerId) return;
        active.tile.classList.remove("is-dragging");
        active.tile.dataset.justDragged = active.dragging ? "1" : "";
        active = null;
      }

      container.addEventListener("pointerup", release);
      container.addEventListener("pointercancel", release);

      /* Caught here, on the container, in the capture phase: this runs before GLightbox's own
         click listener on the tile itself, regardless of which one was registered first. */
      container.addEventListener(
        "click",
        function (event) {
          var tile = event.target.closest(".tile");
          if (tile && tile.dataset.justDragged === "1") {
            tile.dataset.justDragged = "";
            event.preventDefault();
            event.stopImmediatePropagation();
          }
        },
        true
      );
    });
  }

  /** Hero only: the kicker tag and the meta line can be nudged a short distance from their
      curated position. They stay in normal flow (position: relative), so dragging one never
      reflows the H1 or anything else around it. */
  function HeroTags() {
    if (!("PointerEvent" in window)) return;
    var tags = document.querySelectorAll(".hero-tag");
    if (!tags.length) return;

    tags.forEach(function (tag) {
      var active = null;

      tag.addEventListener("pointerdown", function (event) {
        if (event.button > 0) return;
        active = {
          pointerId: event.pointerId,
          startX: event.clientX,
          startY: event.clientY,
          originLeft: parseFloat(tag.dataset.dragLeft || "0"),
          originTop: parseFloat(tag.dataset.dragTop || "0"),
          dragging: false
        };
        tag.setPointerCapture(event.pointerId);
      });

      tag.addEventListener("pointermove", function (event) {
        if (!active || event.pointerId !== active.pointerId) return;
        var dx = event.clientX - active.startX;
        var dy = event.clientY - active.startY;
        if (!active.dragging && Math.hypot(dx, dy) > 6) {
          active.dragging = true;
          tag.classList.add("is-dragging");
        }
        if (active.dragging) {
          event.preventDefault();
          var left = active.originLeft + dx;
          var top = active.originTop + dy;
          tag.style.left = left + "px";
          tag.style.top = top + "px";
          tag.dataset.dragLeft = left;
          tag.dataset.dragTop = top;
        }
      });

      function release(event) {
        if (!active || event.pointerId !== active.pointerId) return;
        tag.classList.remove("is-dragging");
        tag.dataset.justDragged = active.dragging ? "1" : "";
        active = null;
      }

      tag.addEventListener("pointerup", release);
      tag.addEventListener("pointercancel", release);

      /* The kicker holds a real link (HfG Karlsruhe); a drag must not also follow it. Caught
         here, in the capture phase, ahead of the link's own default navigation. */
      tag.addEventListener(
        "click",
        function (event) {
          if (tag.dataset.justDragged === "1") {
            tag.dataset.justDragged = "";
            event.preventDefault();
            event.stopImmediatePropagation();
          }
        },
        true
      );
    });
  }

  function Lightbox() {
    if (typeof GLightbox !== "function") return;
    GLightbox({
      selector: ".glightbox",
      touchNavigation: true,
      loop: true,
      openEffect: "fade",
      closeEffect: "fade",
      slideEffect: "fade",
      zoomable: true,
      descPosition: "bottom"
    });
  }

  /* --------------------------------------------------------------- app */

  function Site() {
    var toast = new Toast();
    new ScrollChrome();

    new Rail();
    new Reveal();
    new Tilt();
    new Scramble();
    new Unsettle(toast);
    new Ember(toast);
    new Curtain();
    FreeformCollage();
    HeroTags();
    Lightbox();

    this.frames = [new Spotlight(), new Magnet(), new Parallax()];
    this.tick();
  }

  Site.prototype.tick = function () {
    var self = this;
    this.frames.forEach(function (part) {
      if (part.frame) part.frame();
    });
    requestAnimationFrame(function () {
      self.tick();
    });
  };

  if (document.readyState !== "loading") {
    new Site();
  } else {
    document.addEventListener("DOMContentLoaded", function () {
      new Site();
    });
  }
})();
