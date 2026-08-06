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

  function Nav() {
    this.toggle = document.querySelector(".nav-toggle");
    this.nav = document.querySelector(".nav-main");
    if (!this.toggle || !this.nav) return;

    var self = this;
    this.toggle.addEventListener("click", function () {
      var open = self.nav.classList.toggle("is-open");
      self.toggle.setAttribute("aria-expanded", String(open));
      self.toggle.textContent = open ? "Close" : "Menu";
    });
    this.nav.addEventListener("click", function (event) {
      if (event.target.closest("a")) self.close();
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") self.close();
    });
  }

  Nav.prototype.close = function () {
    if (!this.nav) return;
    this.nav.classList.remove("is-open");
    this.toggle.setAttribute("aria-expanded", "false");
    this.toggle.textContent = "Menu";
  };

  /** Sticky-header shadow, reading progress and the back-to-top button. */
  function ScrollChrome() {
    this.head = document.querySelector(".site-head");
    this.bar = document.querySelector(".progress-rail span");
    this.top = document.querySelector(".to-top");
    this.last = window.scrollY;
    this.velocity = 0;
    this.direction = 1;

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
    var delta = y - this.last;
    this.last = y;
    this.velocity = Math.min(Math.abs(delta), 90);
    if (delta !== 0) this.direction = delta > 0 ? 1 : -1;

    if (this.head) this.head.classList.toggle("is-stuck", y > 12);
    if (this.bar) this.bar.style.width = (span > 0 ? (y / span) * 100 : 0) + "%";
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

  /** Ring cursor whose label names whatever is under it, plus the paper spotlight. */
  function Cursor() {
    this.el = document.querySelector(".cursor");
    this.label = document.querySelector(".cursor-label");
    this.light = document.querySelector(".spotlight");
    this.x = window.innerWidth / 2;
    this.y = window.innerHeight / 2;
    this.tx = this.x;
    this.ty = this.y;
    if (!this.el || !FINE || CALM) return;

    var self = this;
    window.addEventListener("pointermove", function (event) {
      self.tx = event.clientX;
      self.ty = event.clientY;
      self.read(event.target);
      if (self.light) {
        self.light.classList.add("is-on");
        self.light.style.setProperty("--mx", event.clientX + "px");
        self.light.style.setProperty("--my", event.clientY + "px");
      }
    }, { passive: true });

    document.addEventListener("pointerleave", function () {
      self.el.style.opacity = "0";
      if (self.light) self.light.classList.remove("is-on");
    });
    document.addEventListener("pointerenter", function () {
      self.el.style.opacity = "1";
    });
  }

  Cursor.prototype.read = function (target) {
    var text = "";
    if (target.closest) {
      if (target.closest("[data-drag]")) text = "drag";
      else if (target.closest(".tile")) text = "open";
      else if (target.closest(".index-row, .card-work")) text = "view";
      else if (target.closest('a[target="_blank"]')) text = "↗";
      else if (target.closest("a, button")) text = "→";
    }
    this.el.classList.toggle("is-active", Boolean(text));
    if (this.label && this.label.textContent !== text) this.label.textContent = text;
  };

  Cursor.prototype.frame = function () {
    if (!this.el || !FINE || CALM) return;
    this.x = lerp(this.x, this.tx, 0.22);
    this.y = lerp(this.y, this.ty, 0.22);
    this.el.style.transform = "translate3d(" + this.x + "px," + this.y + "px,0)";
  };

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

  /** Preview thumbnail that follows the pointer across an index list. */
  function Peek() {
    var peek = document.querySelector(".peek");
    var rows = document.querySelectorAll(".index-row[data-peek]");
    if (!peek || !rows.length || CALM || !FINE) return;

    var img = peek.querySelector("img");
    var pending = null;

    function move(event) {
      if (pending) return;
      pending = requestAnimationFrame(function () {
        peek.style.left = event.clientX + "px";
        peek.style.top = event.clientY + "px";
        pending = null;
      });
    }

    rows.forEach(function (row) {
      var src = row.getAttribute("data-peek");
      if (!src) return;
      row.addEventListener("pointerenter", function (event) {
        img.src = src;
        peek.classList.add("is-on");
        move(event);
      });
      row.addEventListener("pointermove", move);
      row.addEventListener("pointerleave", function () {
        peek.classList.remove("is-on");
      });
    });
  }

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
    var GLYPHS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ/\\*+<>#";

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

  /** Marquee whose speed and direction follow the scroll. */
  function Marquee(chrome) {
    this.track = document.querySelector(".marquee-track");
    this.chrome = chrome;
    this.offset = 0;
    if (!this.track) return;
    this.track.innerHTML += this.track.innerHTML;
    this.half = this.track.scrollWidth / 2;
  }

  Marquee.prototype.frame = function () {
    if (!this.track || CALM) return;
    var speed = 0.35 + this.chrome.velocity * 0.06;
    this.offset -= speed * this.chrome.direction;
    if (this.offset <= -this.half) this.offset += this.half;
    if (this.offset > 0) this.offset -= this.half;
    this.track.style.transform = "translate3d(" + this.offset.toFixed(2) + "px,0,0)";
  };

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

  /* ---------------------------------------------------------- collages */

  /** Collage tiles can be pushed around; a real drag suppresses the lightbox. */
  function Drag() {
    if (CALM) return;
    var top = 80;

    document.querySelectorAll("[data-drag]").forEach(function (tile) {
      var start = null;
      var base = { x: 0, y: 0 };
      var moved = false;

      tile.addEventListener("pointerdown", function (event) {
        if (event.button !== 0) return;
        start = { x: event.clientX, y: event.clientY };
        base = {
          x: parseFloat(tile.style.getPropertyValue("--dx")) || 0,
          y: parseFloat(tile.style.getPropertyValue("--dy")) || 0
        };
        moved = false;
        tile.setPointerCapture(event.pointerId);
      });

      tile.addEventListener("pointermove", function (event) {
        if (!start) return;
        var dx = event.clientX - start.x;
        var dy = event.clientY - start.y;
        if (!moved && Math.hypot(dx, dy) > 4) {
          moved = true;
          tile.classList.add("is-dragging");
          tile.style.zIndex = String(++top);
        }
        if (!moved) return;
        event.preventDefault();
        tile.style.setProperty("--dx", (base.x + dx).toFixed(1) + "px");
        tile.style.setProperty("--dy", (base.y + dy).toFixed(1) + "px");
      });

      function end(event) {
        if (!start) return;
        start = null;
        tile.classList.remove("is-dragging");
        if (tile.hasPointerCapture && tile.hasPointerCapture(event.pointerId)) {
          tile.releasePointerCapture(event.pointerId);
        }
      }

      tile.addEventListener("pointerup", end);
      tile.addEventListener("pointercancel", end);

      tile.addEventListener("click", function (event) {
        if (!moved) return;
        event.preventDefault();
        event.stopPropagation();
        moved = false;
      }, true);
    });
  }

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
    var chrome = new ScrollChrome();

    new Nav();
    new Reveal();
    new Peek();
    new Tilt();
    new Scramble();
    new Drag();
    new Unsettle(toast);
    new Ember(toast);
    new Curtain();
    Lightbox();

    this.frames = [new Cursor(), new Magnet(), new Marquee(chrome), new Parallax()];
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
