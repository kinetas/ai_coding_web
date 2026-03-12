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
        window.EtCharts.lineChart(byId("chart-line"), line, { accent: accents.line || "#6AE4FF" });
        window.EtCharts.barChart(byId("chart-bar"), bar, { accent: accents.bar || "#B79BFF" });
        window.EtCharts.donutChart(byId("chart-donut"), donut, {});
      })
      .catch(function (reason) {
        showChartError(reason && reason.message ? reason.message : "그래프 데이터를 불러오지 못했습니다.");
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
