(function () {
  var MAX_WORDS = 28;

  function isAllowedCategory(c) {
    return c === "all" || c === "agri" || c === "health" || c === "traffic" || c === "tour" || c === "env";
  }

  function isAllowedRegion(r) {
    return r === "kr" || r === "global";
  }

  function getCssVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  var state = {
    category: "all",
    region: "kr",
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
    var a1 = getCssVar("--accent") || "#00D4FF";
    var a2 = getCssVar("--accent2") || "#A78BFF";
    if (regionKey === "kr") return [a1, a2, "#9AF7D0", "#FFD36A", "#FF7AD9"];
    return [a2, a1, "#FFB86A", "#9AF7D0", "#FF7AD9"];
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
    var pad = 8;

    function intersects(a, b) {
      return !(a.right < b.left || a.left > b.right || a.bottom < b.top || a.top > b.bottom);
    }

    function tryPlace(ww, wh) {
      // 나선형 탐색: 중앙에서 바깥으로 확장하며 빈 자리 탐색
      var cx = cw / 2;
      var cy = ch / 2;
      var step = 6;
      var maxR = Math.max(cw, ch);

      for (var r = 0; r < maxR; r += step) {
        var steps = Math.max(1, Math.round(2 * Math.PI * Math.max(r, 1) / step));
        for (var s = 0; s < steps; s++) {
          var angle = (s / steps) * Math.PI * 2;
          var jitter = (Math.random() - 0.5) * step;
          var x = cx + (r + jitter) * Math.cos(angle) - ww / 2;
          var y = cy + (r + jitter) * Math.sin(angle) - wh / 2;
          x = clamp(x, pad, cw - ww - pad);
          y = clamp(y, pad, ch - wh - pad);
          var cand = { left: x, top: y, right: x + ww, bottom: y + wh };
          var hit = false;
          for (var i = 0; i < placed.length; i++) {
            if (intersects(cand, placed[i])) { hit = true; break; }
          }
          if (!hit) return cand;
        }
      }
      return null;
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
      var ww = Math.max(1, wRect.width);
      var wh = Math.max(1, wRect.height);

      var pos = tryPlace(ww, wh);

      if (!pos) {
        // 공간 없으면 컨테이너 밖으로 숨김 (겹침 방지)
        span.style.visibility = "hidden";
        return;
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
        renderSidebarKpi(results[0]);
      })
      .catch(function (reason) {
        var msg = reason && reason.message ? reason.message : "워드클라우드 데이터를 불러오지 못했습니다.";
        renderCloudError(kr, msg);
        renderCloudError(gl, msg);
      });
  }

  function renderSidebarKpi(words) {
    var kpiEl = document.getElementById("sidebar-kpi");
    if (!kpiEl) return;
    var top = (words || []).slice(0, 5);
    if (!top.length) {
      kpiEl.innerHTML = '<p class="kpi-error">데이터 없음</p>';
      return;
    }
    var maxW = top[0].weight || 1;
    kpiEl.innerHTML = top.map(function (w, i) {
      var pct = Math.round((w.weight / maxW) * 100);
      return '<div class="kpi-item">' +
        '<span class="kpi-rank">' + (i + 1) + '</span>' +
        '<span class="kpi-word">' + w.text + '</span>' +
        '<span class="kpi-score">' + pct + '</span>' +
        '</div>';
    }).join("");
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

  function setupRegionTabs() {
    var tabs = document.querySelectorAll(".wc-tab[data-region]");
    if (!tabs.length) return;

    tabs.forEach(function (tab) {
      tab.addEventListener("click", function () {
        var region = tab.getAttribute("data-region");
        if (!isAllowedRegion(region)) return;
        state.region = region;

        tabs.forEach(function (t) {
          var active = t.getAttribute("data-region") === region;
          t.classList.toggle("is-active", active);
          t.setAttribute("aria-selected", active ? "true" : "false");
        });

        var panels = document.querySelectorAll(".wc-panel");
        panels.forEach(function (p) {
          p.classList.toggle("is-active", p.id === "wc-panel-" + region);
        });
      });
    });
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
    setupRegionTabs();
    setupResizeRerender();
    renderAllClouds();
  });
})();


// ── Last Updated 갱신 시각 표시 ──────────────────────────────────────
async function fetchLastUpdated() {
  const el = document.getElementById('last-updated-bar');
  if (!el) return;
  try {
    const res = await fetch('/api/public/price?limit=1');
    const data = await res.json();
    const raw = data?.last_updated || data?.items?.[0]?.updated_at || null;
    if (!raw) { el.textContent = '갱신 시각: 알 수 없음'; return; }
    const dt = new Date(raw);
    el.textContent = '마지막 갱신: ' + dt.toLocaleString('ko-KR', {
      timeZone: 'Asia/Seoul',
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit'
    });
  } catch (e) {
    el.textContent = '갱신 시각: 알 수 없음';
  }
}
document.addEventListener('DOMContentLoaded', fetchLastUpdated);


// ── 데이터 수집 진행 상태 메시지 ────────────────────────────────────
async function fetchDataStatus() {
  const el = document.getElementById('data-status-msg');
  if (!el) return;
  try {
    const res = await fetch('/api/public/news/wordcloud');
    const data = await res.json();
    const count = data?.word_count ?? (data?.words?.length ?? 0);
    const MIN_WORDS = 5;
    if (count < MIN_WORDS) {
      el.style.display = 'block';
      el.textContent = `데이터를 수집하고 있습니다 (${count}/15 단어 확보됨). 잠시 후 다시 확인해 주세요.`;
      el.className = 'data-status-msg collecting';
    } else {
      el.style.display = 'none';
    }
  } catch (e) {
    // API 호출 실패 시 무시
  }
}
document.addEventListener('DOMContentLoaded', fetchDataStatus);
