(function () {
  function $(sel) {
    return document.querySelector(sel);
  }

  function byId(id) {
    return document.getElementById(id);
  }

  function getApiBase() {
    if (window.ET_API_BASE) return String(window.ET_API_BASE).replace(/\/+$/, "");
    return "http://127.0.0.1:8000";
  }

  function renderForPage(page) {
    if (!window.EtCharts) return;

    // page별 샘플 데이터(백엔드 연결 실패 시 fallback)
    var preset = {
      "analysis-1": {
        line: [38, 41, 45, 44, 52, 58, 55, 61, 66, 64, 70, 76],
        bar: [12, 18, 10, 22, 16],
        donut: [44, 26, 18, 12],
        accents: { line: "#6AE4FF", bar: "#B79BFF" }
      },
      "analysis-2": {
        line: [22, 26, 30, 28, 34, 40, 48, 52, 46, 50, 58, 62],
        bar: [8, 14, 20, 16, 12],
        donut: [36, 24, 20, 20],
        accents: { line: "#9AF7D0", bar: "#6AE4FF" }
      },
      "analysis-3": {
        line: [18, 24, 29, 33, 38, 44, 40, 48, 56, 52, 60, 66],
        bar: [10, 16, 26, 18, 14],
        donut: [40, 28, 20, 12],
        accents: { line: "#FFD36A", bar: "#FF7AD9" }
      },
      "analysis-4": {
        line: [14, 16, 20, 18, 24, 28, 34, 30, 36, 40, 44, 48],
        bar: [6, 12, 14, 10, 8],
        donut: [34, 22, 24, 20],
        accents: { line: "#B79BFF", bar: "#9AF7D0" }
      }
    };

    var fallback = preset[page];
    if (!fallback) return;

    var url = getApiBase() + "/api/analysis?page=" + encodeURIComponent(page);
    fetch(url, { method: "GET" })
      .then(function (res) {
        if (!res.ok) throw new Error("bad response");
        return res.json();
      })
      .then(function (cfg) {
        var line = Array.isArray(cfg && cfg.line) ? cfg.line : fallback.line;
        var bar = Array.isArray(cfg && cfg.bar) ? cfg.bar : fallback.bar;
        var donut = Array.isArray(cfg && cfg.donut) ? cfg.donut : fallback.donut;
        var accents = cfg && cfg.accents ? cfg.accents : fallback.accents;
        window.EtCharts.lineChart(byId("chart-line"), line, { accent: accents.line || fallback.accents.line });
        window.EtCharts.barChart(byId("chart-bar"), bar, { accent: accents.bar || fallback.accents.bar });
        window.EtCharts.donutChart(byId("chart-donut"), donut, {});
      })
      .catch(function () {
        window.EtCharts.lineChart(byId("chart-line"), fallback.line, { accent: fallback.accents.line });
        window.EtCharts.barChart(byId("chart-bar"), fallback.bar, { accent: fallback.accents.bar });
        window.EtCharts.donutChart(byId("chart-donut"), fallback.donut, {});
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

  document.addEventListener("DOMContentLoaded", function () {
    var page = document.body && document.body.dataset ? document.body.dataset.page : "";
    renderForPage(page);
    setupResize(page);
  });
})();
