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

  function fmtPct(v) {
    if (v === null || v === undefined) return null;
    var n = Number(v);
    if (!isFinite(n)) return null;
    var sign = n >= 0 ? "+" : "";
    return sign + n.toFixed(2) + "%";
  }

  function setText(id, text) {
    var el = byId(id);
    if (el) el.textContent = text;
  }

  var _FAMILY_LABEL = {
    weight: "중량(kg·g)",
    count: "개수(개·마리·포기 등)",
    pack: "묶음(장·묶음·손 등)",
    volume: "용량(L)",
    special: "특수단위"
  };

  // Category stats tabs

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
      // Tab button
      var btn = document.createElement("button");
      btn.className = "cat-tab" + (idx === 0 ? " is-active" : "");
      btn.type = "button";
      btn.textContent = cat.ctgry_nm + " (" + (cat.count || 0) + ")";
      btn.dataset.target = "cat-panel-" + idx;
      tabsEl.appendChild(btn);

      // Panel
      var panel = document.createElement("div");
      panel.id = "cat-panel-" + idx;
      panel.className = "cat-panel" + (idx === 0 ? " is-active" : "");

      // 대표 통계 (weight 계열 우선)
      var cheapestTxt = cat.cheapest
        ? cat.cheapest.item_nm + " " + fmtPrice(cat.cheapest.price) + (cat.cheapest.unit_label ? " (" + cat.cheapest.unit_label + ")" : "")
        : "—";
      var expTxt = cat.most_expensive
        ? cat.most_expensive.item_nm + " " + fmtPrice(cat.most_expensive.price) + (cat.most_expensive.unit_label ? " (" + cat.most_expensive.unit_label + ")" : "")
        : "—";

      var html =
        '<p class="panel-desc" style="margin-bottom:0.5rem">대표 통계 (' + (cat.price_label || "원") + ')</p>' +
        '<div class="cat-stat-grid">' +
        statCard("표본 수", fmt(cat.count) + "건", "") +
        statCard("평균", fmtPrice(cat.avg_price), cat.price_label || "") +
        statCard("최저가 품목", fmtPrice(cat.min_price), cheapestTxt) +
        statCard("최고가 품목", fmtPrice(cat.max_price), expTxt) +
        "</div>";

      // 단위군별 세부 통계
      var breakdown = Array.isArray(cat.unit_breakdown) ? cat.unit_breakdown : [];
      if (breakdown.length > 1) {
        html += '<details style="margin-top:1rem"><summary style="cursor:pointer;font-size:0.85rem;opacity:0.8">단위군별 세부 통계 보기</summary>';
        html += '<div style="margin-top:0.75rem">';
        breakdown.forEach(function (fam) {
          var famLabel = _FAMILY_LABEL[fam.unit_family] || fam.unit_family;
          var famCheapest = fam.cheapest
            ? fam.cheapest.item_nm + " " + fmtPrice(fam.cheapest.price)
            : "—";
          var famExp = fam.most_expensive
            ? fam.most_expensive.item_nm + " " + fmtPrice(fam.most_expensive.price)
            : "—";
          html +=
            '<p style="font-size:0.8rem;opacity:0.7;margin:0.5rem 0 0.25rem">' + famLabel + ' — ' + (fam.price_label || "") + '</p>' +
            '<div class="cat-stat-grid" style="--col:3">' +
            statCard("건수", fmt(fam.count) + "건", "") +
            statCard("평균", fmtPrice(fam.avg_price), "") +
            statCard("최저↑최고", fmtPrice(fam.min_price) + " / " + fmtPrice(fam.max_price), famCheapest + " / " + famExp) +
            "</div>";
        });
        html += "</div></details>";
      }

      panel.innerHTML = html;
      panelsEl.appendChild(panel);
    });

    // Tab click
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

  // Price movers — 2행×4열 카드 그리드 (반응형 4행×2열)

  function renderPriceMovers(data) {
    var errEl = byId("movers-error");
    if (!data) {
      if (errEl) { errEl.hidden = false; errEl.textContent = "가격 등락 데이터를 불러오지 못했습니다."; }
      return;
    }
    if (errEl) errEl.hidden = true;

    var risersEl = byId("movers-risers");
    var fallersEl = byId("movers-fallers");

    function buildMoverCard(m, isRise) {
      var pct = fmtPct(m.wow_pct);
      var w4str = fmtPct(m.w4_pct);
      var pctClass = isRise ? "mover-card__pct--rise" : "mover-card__pct--fall";

      var nameParts = [m.item_nm];
      if (m.vrty_nm) nameParts.push(m.vrty_nm);
      if (m.grd_nm) nameParts.push(m.grd_nm);
      var nameStr = nameParts.join(" ");

      var subParts = [];
      if (m.se_nm) subParts.push(m.se_nm);
      if (m.unit_label) subParts.push(m.unit_label);
      var subStr = subParts.join(" · ");

      return (
        '<div class="mover-card">' +
        '<div>' +
        '<p class="mover-card__name">' + nameStr + '</p>' +
        (subStr ? '<p class="mover-card__sub">' + subStr + '</p>' : '') +
        '</div>' +
        '<div>' +
        '<p class="mover-card__pct ' + pctClass + '">' + (pct || "—") + '</p>' +
        (w4str ? '<p class="mover-card__w4">4주 ' + w4str + '</p>' : '') +
        '</div>' +
        '</div>'
      );
    }

    function buildMoverGrid(items, isRise) {
      if (!items || !items.length) {
        return '<p style="opacity:0.6;font-size:0.85rem">데이터 없음</p>';
      }
      return items.slice(0, 8).map(function (m) {
        return buildMoverCard(m, isRise);
      }).join("");
    }

    if (risersEl) risersEl.innerHTML = buildMoverGrid(data.top_risers, true);
    if (fallersEl) fallersEl.innerHTML = buildMoverGrid(data.top_fallers, false);
  }

  // Rice weekly series

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
    setText("rice-fc-slope", fc.slope_per_week != null ? fmt(fc.slope_per_week) + " 원/주" : "—");

    var series = Array.isArray(data.weekly_series) ? data.weekly_series : [];
    setText("rice-week-count", series.length ? series.length + "개 기간" : "—");

    if (window.EtCharts && byId("chart-rice-series") && series.length > 1) {
      var chartData = series.map(function (pt) { return pt.avg_price; });
      window.EtCharts.lineChart(byId("chart-rice-series"), chartData, { accent: "#9AF7D0" });
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

    // 1) Full analytics payload (차트 번들 + 메타 표시용)
    window.EtApi.fetchJson("/api/agri-analytics", { method: "GET" })
      .then(function (data) {
        if (err) { err.hidden = true; err.textContent = ""; }
        var meta = data && data.meta ? data.meta : {};
        var metaEl = byId("agri-meta");
        if (metaEl) {
          var bits = [];
          if (meta.item_count != null) bits.push("표본 " + meta.item_count + "건");
          if (meta.generated_at) bits.push("생성 " + meta.generated_at);
          metaEl.textContent = bits.length ? bits.join(" · ") : "";
        }
        renderCharts(data && data.chart_bundle);
      })
      .catch(function () {
        // 차트 번들 실패는 조용히 처리 (주요 섹션에 영향 없음)
      });

    // 2) Category stats
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

    // 3) Rice weekly series
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

    // 4) Price movers (전주 대비 등락 품목, 8개씩)
    window.EtApi.fetchJson("/api/agri-analytics/price-movers?top_n=8", { method: "GET" })
      .then(function (data) {
        renderPriceMovers(data);
      })
      .catch(function (reason) {
        var errEl = byId("movers-error");
        if (!errEl) return;
        errEl.hidden = false;
        errEl.textContent = reason && reason.message ? reason.message : "가격 등락 데이터를 불러오지 못했습니다.";
      });
  });
})();
