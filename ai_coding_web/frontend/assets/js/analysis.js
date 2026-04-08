(function () {
  function byId(id) {
    return document.getElementById(id);
  }

  function showChartError(message) {
    var line = byId("chart-line");
    var bar = byId("chart-bar");
    var donut = byId("chart-donut");
    [line, bar, donut].forEach(function (canvas) {
      if (!canvas || !canvas.parentElement) return;
      var note = canvas.parentElement.querySelector(".chart-error");
      if (!note) {
        note = document.createElement("p");
        note.className = "chart-error";
        canvas.parentElement.appendChild(note);
      }
      note.textContent = message;
    });
  }

  function renderForPage(page) {
    if (!window.EtCharts) return;
    if (!page) return;

    window.EtApi.fetchJson("/api/analysis?page=" + encodeURIComponent(page), { method: "GET" })
      .then(function (cfg) {
        var line = Array.isArray(cfg && cfg.line) ? cfg.line : [];
        var bar = Array.isArray(cfg && cfg.bar) ? cfg.bar : [];
        var donut = Array.isArray(cfg && cfg.donut) ? cfg.donut : [];
        var accents = cfg && cfg.accents ? cfg.accents : {};
        var cssA1 = getComputedStyle(document.documentElement).getPropertyValue("--accent").trim() || "#00D4FF";
        var cssA2 = getComputedStyle(document.documentElement).getPropertyValue("--accent2").trim() || "#A78BFF";
        window.EtCharts.lineChart(byId("chart-line"), line, { accent: accents.line || cssA1 });
        window.EtCharts.barChart(byId("chart-bar"), bar, { accent: accents.bar || cssA2 });
        window.EtCharts.donutChart(byId("chart-donut"), donut, {});
      })
      .catch(function (reason) {
        showChartError(reason && reason.message ? reason.message : "Could not load chart data.");
      });
  }

  function setupResize(page) {
    var t = null;
    window.addEventListener("resize", function () {
      if (t) window.clearTimeout(t);
      t = window.setTimeout(function () {
        renderForPage(page);
      }, 200);
    });
  }

  var PAGE_CATEGORY = {
    "analysis-1": "agri",
    "analysis-2": "health",
    "analysis-3": "traffic",
    "analysis-4": "tour",
    "analysis-5": "env"
  };

  function renderKpiCards(page) {
    var el = document.getElementById("analysis-kpi");
    if (!el) return;
    var cat = PAGE_CATEGORY[page];
    if (!cat) return;

    window.EtApi.fetchJson("/api/wordcloud?category=" + encodeURIComponent(cat) + "&region=kr", { method: "GET" })
      .then(function (json) {
        var words = Array.isArray(json && json.words) ? json.words : [];
        var top = words.slice(0, 3);
        if (!top.length) return;
        var maxW = top[0].weight || 1;
        el.innerHTML = top.map(function (w, i) {
          var pct = Math.round((w.weight / maxW) * 100);
          return '<div class="kpi-card">' +
            '<p class="kpi-card__label">TOP ' + (i + 1) + '</p>' +
            '<p class="kpi-card__value">' + w.text + '</p>' +
            '<p class="kpi-card__sub">Score ' + pct + '</p>' +
            '</div>';
        }).join("");
      })
      .catch(function () {});
  }

  document.addEventListener("DOMContentLoaded", function () {
    var page = document.body && document.body.dataset ? document.body.dataset.page : "";
    renderForPage(page);
    renderKpiCards(page);
    setupResize(page);
  });
})();
