(function () {
  var MAX_WORDS = 28;

  var DATA = {
    agri: {
      label: "농산물",
      kr: [
        { text: "사과", weight: 86 },
        { text: "배추", weight: 72 },
        { text: "양파", weight: 66 },
        { text: "쌀값", weight: 64 },
        { text: "기상", weight: 52 },
        { text: "도매가격", weight: 58 },
        { text: "산지", weight: 50 },
        { text: "수급", weight: 46 },
        { text: "물가", weight: 44 }
      ],
      global: [
        { text: "food prices", weight: 80 },
        { text: "drought", weight: 62 },
        { text: "fertilizer", weight: 58 },
        { text: "supply chain", weight: 56 },
        { text: "coffee", weight: 54 },
        { text: "wheat", weight: 52 },
        { text: "crop yield", weight: 50 }
      ]
    },
    health: {
      label: "의료",
      kr: [
        { text: "독감", weight: 82 },
        { text: "응급실", weight: 60 },
        { text: "진료예약", weight: 58 },
        { text: "비대면", weight: 54 },
        { text: "건강검진", weight: 52 },
        { text: "약국", weight: 48 },
        { text: "감염", weight: 46 }
      ],
      global: [
        { text: "flu", weight: 70 },
        { text: "telehealth", weight: 62 },
        { text: "vaccination", weight: 56 },
        { text: "mental health", weight: 54 },
        { text: "AI in healthcare", weight: 52 },
        { text: "outbreak", weight: 50 }
      ]
    },
    traffic: {
      label: "교통",
      kr: [
        { text: "지하철 지연", weight: 74 },
        { text: "버스", weight: 58 },
        { text: "출근길", weight: 56 },
        { text: "택시", weight: 50 },
        { text: "전기차 충전", weight: 48 },
        { text: "사고", weight: 44 },
        { text: "혼잡", weight: 46 }
      ],
      global: [
        { text: "EV charging", weight: 66 },
        { text: "public transit", weight: 58 },
        { text: "traffic congestion", weight: 56 },
        { text: "autonomous", weight: 52 },
        { text: "micro-mobility", weight: 50 }
      ]
    },
    tour: {
      label: "관광",
      kr: [
        { text: "벚꽃", weight: 78 },
        { text: "축제", weight: 62 },
        { text: "맛집", weight: 60 },
        { text: "여행코스", weight: 54 },
        { text: "숙박", weight: 50 },
        { text: "항공권", weight: 48 }
      ],
      global: [
        { text: "cherry blossom", weight: 64 },
        { text: "budget travel", weight: 58 },
        { text: "visa", weight: 54 },
        { text: "travel deals", weight: 52 },
        { text: "city break", weight: 50 }
      ]
    },
    env: {
      label: "환경",
      kr: [
        { text: "미세먼지", weight: 84 },
        { text: "폭염", weight: 60 },
        { text: "탄소중립", weight: 56 },
        { text: "재활용", weight: 52 },
        { text: "기후", weight: 48 },
        { text: "홍수", weight: 44 }
      ],
      global: [
        { text: "climate", weight: 70 },
        { text: "heatwave", weight: 62 },
        { text: "wildfire", weight: 58 },
        { text: "renewables", weight: 54 },
        { text: "carbon", weight: 52 }
      ]
    }
  };

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

  function mergeAll(regionKey) {
    var map = {};
    Object.keys(DATA).forEach(function (cat) {
      (DATA[cat][regionKey] || []).forEach(function (w) {
        var k = String(w.text);
        map[k] = (map[k] || 0) + Number(w.weight || 0);
      });
    });

    var merged = Object.keys(map).map(function (k) {
      return { text: k, weight: map[k] };
    });
    merged.sort(sortByWeightDesc);
    return merged.slice(0, MAX_WORDS);
  }

  function getWords(regionKey, category) {
    if (category === "all") return mergeAll(regionKey);
    var bucket = DATA[category] && DATA[category][regionKey] ? DATA[category][regionKey].slice() : [];
    bucket.sort(sortByWeightDesc);
    return bucket.slice(0, MAX_WORDS);
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
    renderWordCloud(kr, getWords("kr", state.category), "kr");
    renderWordCloud(gl, getWords("global", state.category), "global");
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
      if (requested && (requested === "all" || Object.prototype.hasOwnProperty.call(DATA, requested))) {
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
