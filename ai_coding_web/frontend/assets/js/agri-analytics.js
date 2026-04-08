(function () {
  function byId(id) {
    return document.getElementById(id);
  }

  function fmt(v) {
    if (v === null || v === undefined || v === "") return "—";
    if (typeof v === "number" && isFinite(v)) return String(v);
    return String(v);
  }

  function fmtPrice(v) {
    if (v === null || v === undefined || v === "") return "—";
    var n = Number(v);
    if (!isFinite(n)) return String(v);
    return n.toLocaleString("ko-KR") + "원";
  }

  function setText(id, text) {
    var el = byId(id);
    if (el) el.textContent = text;
  }

  // ── 카테고리별 통계 렌더링 ──────────────────────────────────────────────

  function renderCategoryStats(data) {
    var tabsEl = byId("cat-tabs");
    var panelsEl = byId("cat-panels");
    var errEl = byId("cat-error");
    if (!tabsEl || !panelsEl) return;

    var cats = (data && Array.isArray(data.categories)) ? data.categories : [];
    if (!cats.length) {
      if (errEl) { errEl.hidden = false; errEl.textContent = "카테고리 데이터가 없습니다."; }
      return;
    }
    if (errEl) errEl.hidden = true;

    tabsEl.innerHTML = "";
    panelsEl.innerHTML = "";

    cats.forEach(function (cat, idx) {
      // 탭 버튼
      var btn = document.createElement("button");
      btn.className = "cat-tab" + (idx === 0 ? " is-active" : "");
      btn.type = "button";
      btn.textContent = cat.ctgry_nm;
      btn.dataset.target = "cat-panel-" + idx;
      tabsEl.appendChild(btn);

      // 패널
      var panel = document.createElement("div");
      panel.id = "cat-panel-" + idx;
      panel.className = "cat-panel" + (idx === 0 ? " is-active" : "");

      var cheapestTxt = cat.cheapest ? cat.cheapest.item_nm + " " + fmtPrice(cat.cheapest.price) : "—";
      var expTxt = cat.most_expensive ? cat.most_expensive.item_nm + " " + fmtPrice(cat.most_expensive.price) : "—";

      panel.innerHTML =
        '<div class="cat-stat-grid">' +
        statCard("표본 수", fmt(cat.count) + "건", "") +
        statCard("평균가", fmtPrice(cat.avg_price), "") +
        statCard("최저가", fmtPrice(cat.min_price), cheapestTxt) +
        statCard("최고가", fmtPrice(cat.max_price), expTxt) +
        "</div>";
      panelsEl.appendChild(panel);
    });

    // 탭 클릭
    tabsEl.addEventListener("click", function (e) {
      var btn = e.target.closest(".cat-tab");
      if (!btn) return;
      tabsEl.querySelectorAll(".cat-tab").forEach(function (b) { b.classList.remove("is-active"); });
      panelsEl.querySelectorAll(".cat-panel").forEach(function (p) { p.classList.remove("is-active"); });
      btn.classList.add("is-active");
      var target = byId(btn.dataset.target);
      if (target) target.classList.add("is-active");
    });
  }

  function statCard(label, value, sub) {
    return (
      '<div class="cat-stat-card">' +
      '<p class="cat-stat-card__label">' + label + "</p>" +
      '<p class="cat-stat-card__value">' + value + "</p>" +
      (sub ? '<p class="cat-stat-card__sub">' + sub + "</p>" : "") +
      "</div>"
    );
  }

  // ── 쌀 주차별 시계열 렌더링 ───────────────────────────────────────────────

  function renderRiceSeries(data) {
    var errEl = byId("rice-error");
    if (!data) {
      if (errEl) { errEl.hidden = false; errEl.textContent = "쌀 가격 데이터를 불러오지 못했습니다."; }
      return;
    }
    if (errEl) errEl.hidden = true;

    setText("rice-item-nm", data.item_nm || "쌀");

    var fc = data.forecast || {};
    setText("rice-fc-note", fc.note || "");
    setText("rice-fc-next", fc.next_step_estimate != null ? fmtPrice(fc.next_step_estimate) : "—");
    setText("rice-fc-wow", fc.week_over_week_pct != null ? fmt(fc.week_over_week_pct) + "%" : "—");
    setText("rice-fc-slope", fc.slope_per_week != null ? fmt(fc.slope_per_week) + "원/주" : "—");

    var series = Array.isArray(data.weekly_series) ? data.weekly_series : [];
    setText("rice-week-count", series.length ? series.length + "구간" : "—");

    if (window.EtCharts && byId("chart-rice-series") && series.length > 1) {
      var chartData = series.map(function (pt) { return pt.avg_price; });
      window.EtCharts.lineChart(byId("chart-rice-series"), chartData, { accent: "#9AF7D0" });
    }
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

    // 1) 전체 분석 데이터
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

    // 2) 카테고리별 통계
    window.EtApi.fetchJson("/api/agri-analytics/category-stats", { method: "GET" })
      .then(function (data) {
        renderCategoryStats(data);
      })
      .catch(function (reason) {
        var errEl = byId("cat-error");
        if (!errEl) return;
        errEl.hidden = false;
        errEl.textContent = reason && reason.message ? reason.message : "카테고리 통계를 불러오지 못했습니다.";
      });

    // 3) 쌀 주차별 시계열
    window.EtApi.fetchJson("/api/agri-analytics/rice-series", { method: "GET" })
      .then(function (data) {
        renderRiceSeries(data);
      })
      .catch(function (reason) {
        var errEl = byId("rice-error");
        if (!errEl) return;
        errEl.hidden = false;
        errEl.textContent = reason && reason.message ? reason.message : "쌀 가격 시계열을 불러오지 못했습니다.";
      });
  });
})();
