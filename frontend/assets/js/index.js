(function () {
  var MAX_WORDS = 28;

  function isAllowedCategory(c) {
    return c === "all" || c === "agri" || c === "health" || c === "traffic" || c === "tour" || c === "env";
  }

  function isAllowedRegion(r) {
    return r === "kr" || r === "global";
  }

  var state = {
    category: "all",
    slide: 0,
    timer: null,
    resizeTimer: null
  };

  function clamp(n, min, max) {
    return Math.max(min, Math.min(max, n));
  }

  function sortByWeightDesc(a, b) {
    return b.weight - a.weight;
  }

  function normalizeWords(words) {
    var arr = Array.isArray(words) ? words : [];
    return arr
      .map(function (w) {
        return { text: String(w && w.text ? w.text : ""), weight: Number(w && w.weight ? w.weight : 0) };
      })
      .filter(function (w) { return w.text && isFinite(w.weight) && w.weight >= 0; })
      .sort(sortByWeightDesc)
      .slice(0, MAX_WORDS);
  }

  function fetchWords(regionKey, category) {
    var cat = isAllowedCategory(category) ? category : "all";
    var reg = isAllowedRegion(regionKey) ? regionKey : "kr";
    return window.EtApi.fetchJson("/api/wordcloud?category=" + encodeURIComponent(cat) + "&region=" + encodeURIComponent(reg), { method: "GET" })
      .then(function (json) {
        return normalizeWords(json && json.words ? json.words : []);
      });
  }

  function createPalette(regionKey) {
    if (regionKey === "kr") return ["#6AE4FF", "#B79BFF", "#9AF7D0", "#FFD36A", "#FF7AD9"];
    return ["#B79BFF", "#6AE4FF", "#FFB86A", "#9AF7D0", "#FF7AD9"];
  }

  function renderWordCloud(container, words, regionKey) {
    if (!container) return;
    container.innerHTML = "";

    var rect = container.getBoundingClientRect();
    var cw = Math.max(1, rect.width);
    var ch = Math.max(1, rect.height);

    var weights = words.map(function (w) { return w.weight; });
    var maxW = Math.max.apply(null, weights.concat([1]));
    var minW = Math.min.apply(null, weights.concat([1]));

    var palette = createPalette(regionKey);
    var placed = [];

    function intersects(a, b) {
      return !(a.right < b.left || a.left > b.right || a.bottom < b.top || a.top > b.bottom);
    }

    words.forEach(function (w, idx) {
      var span = document.createElement("span");
      span.className = "wc-word";
      span.textContent = w.text;

      var norm = (w.weight - minW) / Math.max(1, (maxW - minW));
      var size = Math.round(14 + norm * 34);
      span.style.fontSize = size + "px";
      span.style.opacity = String(0.92 - norm * 0.18);
      span.style.color = palette[idx % palette.length];
      span.style.transform = "translateZ(0)";

      container.appendChild(span);

      var wRect = span.getBoundingClientRect();
      var ww = wRect.width;
      var wh = wRect.height;

      var pad = 10;
      var tries = 30;
      var pos = { left: pad, top: pad, right: pad + ww, bottom: pad + wh };

      for (var t = 0; t < tries; t++) {
        var x = Math.random() * clamp(cw - ww - pad * 2, 0, cw) + pad;
        var y = Math.random() * clamp(ch - wh - pad * 2, 0, ch) + pad;
        var cand = { left: x, top: y, right: x + ww, bottom: y + wh };

        var hasHit = false;
        for (var i = 0; i < placed.length; i++) {
          if (intersects(cand, placed[i])) {
            hasHit = true;
            break;
          }
        }
        if (!hasHit) {
          pos = cand;
          break;
        }
      }

      span.style.left = Math.round(pos.left) + "px";
      span.style.top = Math.round(pos.top) + "px";
      placed.push(pos);
    });
  }

  function renderCloudError(container, message) {
    if (!container) return;
    container.innerHTML = "";
    var note = document.createElement("p");
    note.className = "chart-error";
    note.textContent = message;
    container.appendChild(note);
  }

  function setActiveChip(category) {
    var chips = document.querySelectorAll(".chip[data-category]");
    chips.forEach(function (btn) {
      if (btn.getAttribute("data-category") === category) btn.classList.add("is-active");
      else btn.classList.remove("is-active");
    });
  }

  function renderAllClouds() {
    var kr = document.getElementById("cloud-kr");
    var gl = document.getElementById("cloud-global");

    return Promise.all([fetchWords("kr", state.category), fetchWords("global", state.category)])
      .then(function (results) {
        renderWordCloud(kr, results[0], "kr");
        renderWordCloud(gl, results[1], "global");
      })
      .catch(function (reason) {
        var msg = reason && reason.message ? reason.message : "워드클라우드 데이터를 불러오지 못했습니다.";
        renderCloudError(kr, msg);
        renderCloudError(gl, msg);
      });
  }

  function setupFilters() {
    var root = document.querySelector(".filters");
    if (!root) return;

    root.addEventListener("click", function (e) {
      var t = e.target;
      if (!t || !t.matches || !t.matches(".chip[data-category]")) return;

      state.category = t.getAttribute("data-category") || "all";
      setActiveChip(state.category);
      renderAllClouds();
    });
  }

  function setSlide(index) {
    var track = document.querySelector("[data-carousel-track]");
    var dots = document.querySelectorAll("[data-carousel-dot]");
    if (!track) return;

    var count = 2;
    var next = ((index % count) + count) % count;
    state.slide = next;
    track.style.transform = "translateX(" + (-next * 50) + "%)";

    dots.forEach(function (d) {
      var i = Number(d.getAttribute("data-carousel-dot"));
      var active = i === next;
      if (active) d.classList.add("is-active");
      else d.classList.remove("is-active");
      d.setAttribute("aria-selected", active ? "true" : "false");
    });
  }

  function setupCarousel() {
    var prev = document.querySelector("[data-carousel-prev]");
    var next = document.querySelector("[data-carousel-next]");
    var dots = document.querySelectorAll("[data-carousel-dot]");
    var viewport = document.querySelector(".carousel__viewport");

    if (prev) prev.addEventListener("click", function () { setSlide(state.slide - 1); });
    if (next) next.addEventListener("click", function () { setSlide(state.slide + 1); });

    dots.forEach(function (d) {
      d.addEventListener("click", function () {
        var i = Number(d.getAttribute("data-carousel-dot"));
        setSlide(i);
      });
    });

    function start() {
      stop();
      state.timer = window.setInterval(function () {
        setSlide(state.slide + 1);
      }, 6500);
    }

    function stop() {
      if (state.timer) window.clearInterval(state.timer);
      state.timer = null;
    }

    if (viewport) {
      viewport.addEventListener("mouseenter", stop);
      viewport.addEventListener("mouseleave", start);
      viewport.addEventListener("focusin", stop);
      viewport.addEventListener("focusout", start);
    }

    start();
  }

  function setupResizeRerender() {
    window.addEventListener("resize", function () {
      if (state.resizeTimer) window.clearTimeout(state.resizeTimer);
      state.resizeTimer = window.setTimeout(function () {
        renderAllClouds();
      }, 250);
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    try {
      var params = new URLSearchParams(window.location.search || "");
      var requested = params.get("category");
      if (requested && isAllowedCategory(requested)) {
        state.category = requested;
      }
    } catch (e) {
      // ignore
    }
    setActiveChip(state.category);
    setupFilters();
    setupCarousel();
    setupResizeRerender();
    renderAllClouds();
    setSlide(0);
  });
})();
