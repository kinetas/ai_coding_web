(function () {
  function byId(id) {
    return document.getElementById(id);
  }

  function fmt(v) {
    if (v === null || v === undefined || v === "") return "—";
    if (typeof v === "number" && isFinite(v)) return String(v);
    return String(v);
  }

  function setText(id, text) {
    var el = byId(id);
    if (el) el.textContent = text;
  }

  function renderRegions(rows) {
    var tb = byId("tbl-regions");
    if (!tb) return;
    var body = tb.querySelector("tbody");
    if (!body) return;
    body.innerHTML = "";
    (rows || []).forEach(function (r) {
      var tr = document.createElement("tr");
      tr.innerHTML =
        "<td>" +
        fmt(r.region) +
        "</td><td>" +
        fmt(r.count) +
        "</td><td>" +
        fmt(r.min) +
        "</td><td>" +
        fmt(r.max) +
        "</td><td>" +
        fmt(r.avg) +
        "</td>";
      body.appendChild(tr);
    });
  }

  function renderBins(dist) {
    var tb = byId("tbl-distribution");
    if (!tb) return;
    var body = tb.querySelector("tbody");
    if (!body) return;
    body.innerHTML = "";
    var bins = dist && Array.isArray(dist.bins) ? dist.bins : [];
    bins.forEach(function (b) {
      var tr = document.createElement("tr");
      tr.innerHTML =
        "<td>" +
        fmt(b.label) +
        "</td><td>" +
        fmt(b.price_min) +
        "</td><td>" +
        fmt(b.price_max) +
        "</td><td>" +
        fmt(b.count) +
        "</td>";
      body.appendChild(tr);
    });
    setText("dist-unit", dist && dist.unit_hint ? dist.unit_hint : "");
  }

  function renderForecast(fc) {
    if (!fc) return;
    setText("fc-next", fmt(fc.next_step_estimate));
    setText("fc-wow", fc.week_over_week_pct !== undefined ? fmt(fc.week_over_week_pct) + "%" : "—");
    setText("fc-slope", fmt(fc.slope_per_week));
    setText("fc-method", fc.method ? fmt(fc.method) : "linear_extrapolation");
    setText("fc-note", fc.note || "");

    if (window.EtCharts && byId("chart-fc-series") && Array.isArray(fc.mean_series_weeks) && fc.mean_series_weeks.length > 1) {
      window.EtCharts.lineChart(byId("chart-fc-series"), fc.mean_series_weeks, { accent: "#9AF7D0" });
    }
  }

  function renderCharts(bundle) {
    if (!window.EtCharts) return;
    var b = bundle || {};
    var acc = b.accents || {};
    var cssA1 = getComputedStyle(document.documentElement).getPropertyValue("--accent").trim() || "#00D4FF";
    var cssA2 = getComputedStyle(document.documentElement).getPropertyValue("--accent2").trim() || "#A78BFF";
    if (byId("chart-line2")) window.EtCharts.lineChart(byId("chart-line2"), b.line || [], { accent: acc.line || cssA1 });
    if (byId("chart-bar2")) window.EtCharts.barChart(byId("chart-bar2"), b.bar || [], { accent: acc.bar || cssA2 });
    if (byId("chart-donut2")) window.EtCharts.donutChart(byId("chart-donut2"), b.donut || [], {});
  }

  document.addEventListener("DOMContentLoaded", function () {
    var err = byId("agri-error");
    window.EtApi.fetchJson("/api/agri-analytics", { method: "GET" })
      .then(function (data) {
        if (err) {
          err.hidden = true;
          err.textContent = "";
        }
        setText("agri-updated", data && data.updated_at ? data.updated_at : "—");
        setText("agri-source", data && data.source ? data.source : "—");
        var meta = data && data.meta ? data.meta : {};
        var metaEl = byId("agri-meta");
        if (metaEl) {
          var bits = [];
          if (meta.item_count != null) bits.push("표본 " + meta.item_count + "건");
          if (meta.generated_at) bits.push("생성 " + meta.generated_at);
          if (meta.api_path_hint) bits.push("API경로 " + meta.api_path_hint);
          metaEl.textContent = bits.length ? bits.join(" · ") : "";
        }

        var ov = (data && data.overall) || {};
        setText("ov-min", fmt(ov.min));
        setText("ov-max", fmt(ov.max));
        setText("ov-avg", fmt(ov.avg));
        setText("ov-spread", fmt(ov.spread));
        setText("ov-count", fmt(ov.count));

        renderRegions(data && data.region_stats);
        renderBins(data && data.distribution);
        renderForecast(data && data.forecast);
        renderCharts(data && data.chart_bundle);
      })
      .catch(function (reason) {
        if (!err) return;
        err.hidden = false;
        err.textContent = reason && reason.message ? reason.message : "분석 데이터를 불러오지 못했습니다.";
      });
  });
})();
