(function () {
  'use strict';

  var DONUT_COLORS = ['#00D4FF', '#A78BFF', '#FFD36A', '#9AF7D0', '#FF7AD9', '#FF9F56', '#56CFFF', '#B4F26E'];

  var state = {
    category: null,
    subcategory: null,
    year: new Date().getFullYear() - 1,
    method: null,
    loading: false,
  };

  function qs(sel) { return document.querySelector(sel); }

  function unlockStep(n) {
    var el = document.getElementById('ca-step-' + n);
    if (el) el.classList.remove('ca-step--locked');
  }
  function lockStep(n) {
    var el = document.getElementById('ca-step-' + n);
    if (el) el.classList.add('ca-step--locked');
  }

  function checkRunnable() {
    var btn = qs('#ca-run-btn');
    if (!btn) return;
    var ok = state.category && state.subcategory && state.year && state.method && !state.loading;
    btn.disabled = !ok;
  }

  function setActiveSingle(group, code) {
    if (!group) return;
    group.querySelectorAll('.ca-btn').forEach(function (b) {
      b.classList.toggle('active', b.dataset.code === code);
    });
  }

  // ── Step 1: 카테고리 ────────────────────────────────────────────────────

  function renderCategoryBtns(categories) {
    var group = qs('#ca-category-group');
    if (!group) return;
    group.innerHTML = categories.map(function (cat) {
      return '<button class="ca-btn" data-code="' + cat.code + '">' + cat.label + '</button>';
    }).join('');
    group.addEventListener('click', function (e) {
      var btn = e.target.closest('.ca-btn');
      if (!btn) return;
      var code = btn.dataset.code;
      if (state.category === code) return;
      state.category = code;
      state.subcategory = null;
      state.method = null;
      setActiveSingle(group, code);
      // Reset downstream
      lockStep(3); lockStep(4);
      resetMethodBtns();
      loadSubcategories(code);
      checkRunnable();
    });
  }

  // ── Step 2: 서브카테고리 ─────────────────────────────────────────────────

  function loadSubcategories(category) {
    var group = qs('#ca-subcategory-group');
    if (!group) return;
    group.innerHTML = '<span class="ca-placeholder">불러오는 중…</span>';
    unlockStep(2);

    window.EtApi.fetchJson('/api/custom-analysis/subcategories?category=' + encodeURIComponent(category))
      .then(function (data) {
        var subs = data.subcategories || [];
        var allBtn = '<button class="ca-btn" data-code="all">전체</button>';
        var subBtns = subs.map(function (s) {
          return '<button class="ca-btn" data-code="' + escAttr(s.code) + '">' + escHtml(s.label) + '</button>';
        }).join('');
        group.innerHTML = allBtn + subBtns;
        group.addEventListener('click', onSubcategoryClick);
      })
      .catch(function () {
        group.innerHTML = '<span class="ca-placeholder">불러오기 실패</span>';
      });
  }

  function onSubcategoryClick(e) {
    var btn = e.target.closest('.ca-btn');
    if (!btn) return;
    var group = qs('#ca-subcategory-group');
    state.subcategory = btn.dataset.code;
    setActiveSingle(group, state.subcategory);
    unlockStep(3);
    unlockStep(4);
    checkRunnable();
  }

  // ── Step 3: 연도 ─────────────────────────────────────────────────────────

  function initYearInput() {
    var input = qs('#ca-year');
    if (!input) return;
    input.value = state.year;
    input.addEventListener('change', function () {
      var v = parseInt(input.value, 10);
      if (!isNaN(v) && v >= 2018 && v <= 2030) {
        state.year = v;
      } else {
        input.value = state.year;
      }
      checkRunnable();
    });
  }

  // ── Step 4: 분석 방식 ────────────────────────────────────────────────────

  function renderMethodBtns(methods) {
    var group = qs('#ca-method-group');
    if (!group) return;
    group.innerHTML = methods.map(function (m) {
      return '<button class="ca-btn" data-code="' + m.code + '" title="' + escAttr(m.desc || '') + '">' + m.label + '</button>';
    }).join('');
    group.addEventListener('click', function (e) {
      var btn = e.target.closest('.ca-btn');
      if (!btn) return;
      state.method = btn.dataset.code;
      setActiveSingle(group, state.method);
      checkRunnable();
    });
  }

  function resetMethodBtns() {
    var group = qs('#ca-method-group');
    if (!group) return;
    group.querySelectorAll('.ca-btn').forEach(function (b) { b.classList.remove('active'); });
    state.method = null;
  }

  // ── 분석 실행 ────────────────────────────────────────────────────────────

  function runAnalysis() {
    if (!state.category || !state.subcategory || !state.year || !state.method) return;
    if (state.loading) return;

    state.loading = true;
    checkRunnable();

    var result = qs('#ca-result');
    var titleEl = qs('#ca-result-title');
    var noteEl = qs('#ca-result-note');
    var legend = qs('#ca-legend');
    var noDataEl = qs('#ca-no-data');
    var canvas = qs('#ca-canvas');

    if (result) result.hidden = false;
    if (titleEl) titleEl.textContent = '분석 중…';
    if (noteEl) noteEl.hidden = true;
    if (legend) legend.innerHTML = '';
    if (noDataEl) noDataEl.hidden = true;
    if (canvas) { var ctx2 = canvas.getContext('2d'); if (ctx2) ctx2.clearRect(0, 0, canvas.width, canvas.height); }

    var url = '/api/custom-analysis/data'
      + '?category=' + encodeURIComponent(state.category)
      + '&subcategory=' + encodeURIComponent(state.subcategory)
      + '&year=' + encodeURIComponent(state.year)
      + '&method=' + encodeURIComponent(state.method);

    window.EtApi.fetchJson(url)
      .then(function (data) {
        state.loading = false;
        checkRunnable();
        renderResult(data);
      })
      .catch(function (e) {
        state.loading = false;
        checkRunnable();
        if (titleEl) titleEl.textContent = '요청 실패';
        if (noteEl) { noteEl.textContent = e && e.message ? e.message : '오류가 발생했습니다.'; noteEl.hidden = false; }
      });
  }

  // ── 결과 렌더링 ──────────────────────────────────────────────────────────

  function renderResult(data) {
    var titleEl = qs('#ca-result-title');
    var noteEl = qs('#ca-result-note');
    var legend = qs('#ca-legend');
    var noDataEl = qs('#ca-no-data');
    var canvas = qs('#ca-canvas');

    if (titleEl) titleEl.textContent = data.title || '분석 결과';
    if (data.note && noteEl) { noteEl.textContent = data.note; noteEl.hidden = false; }

    var series = data.series || [];
    var labels = data.labels || [];

    if (!series.length) {
      if (noDataEl) noDataEl.hidden = false;
      if (canvas) { var ctx3 = canvas.getContext('2d'); if (ctx3) ctx3.clearRect(0, 0, canvas.width, canvas.height); }
      return;
    }

    var chartType = data.chart_type || 'line';
    var unit = data.unit || '';

    if (chartType === 'line') {
      if (canvas) window.EtCharts.lineChart(canvas, series, { labels: labels });
      renderTableLegend(legend, labels, series, unit, false);
    } else if (chartType === 'bar') {
      var isMovers = data.method === 'movers';
      if (isMovers) {
        renderMoversChart(canvas, series, labels);
      } else {
        if (canvas) window.EtCharts.barChart(canvas, series, {});
      }
      renderTableLegend(legend, labels, series, unit, isMovers);
    } else if (chartType === 'donut') {
      if (canvas) window.EtCharts.donutChart(canvas, series, { colors: DONUT_COLORS });
      renderDonutLegend(legend, labels, series);
    }
  }

  function renderTableLegend(legend, labels, series, unit, isMovers) {
    if (!legend) return;
    if (!labels.length) { legend.innerHTML = ''; return; }

    var unitHtml = unit ? '<div class="ca-legend-unit">' + escHtml(unit) + '</div>' : '';
    var rows = labels.map(function (lbl, i) {
      var val = series[i] != null ? series[i] : 0;
      var isPos = val >= 0;
      var color = isMovers ? (isPos ? '#9AF7D0' : '#FF7AD9') : 'var(--accent2)';
      var sign = (isMovers && isPos && val !== 0) ? '+' : '';
      var valStr = isMovers
        ? sign + Number(val).toFixed(1)
        : Number(val).toLocaleString('ko-KR');
      return '<div class="ca-legend-row">'
        + '<span class="ca-legend-dot" style="background:' + color + '"></span>'
        + '<span class="ca-legend-name">' + escHtml(lbl) + '</span>'
        + '<span class="ca-legend-val">' + valStr + '</span>'
        + '</div>';
    }).join('');

    legend.innerHTML = unitHtml + '<div class="ca-legend-grid">' + rows + '</div>';
  }

  function renderDonutLegend(legend, labels, series) {
    if (!legend) return;
    var total = series.reduce(function (a, b) { return a + (b || 0); }, 0);
    if (!labels.length) { legend.innerHTML = ''; return; }
    var rows = labels.map(function (lbl, i) {
      var pct = total > 0 ? Math.round((series[i] || 0) / total * 100) : 0;
      return '<div class="ca-legend-row">'
        + '<span class="ca-legend-dot" style="background:' + DONUT_COLORS[i % DONUT_COLORS.length] + '"></span>'
        + '<span class="ca-legend-name">' + escHtml(lbl) + '</span>'
        + '<span class="ca-legend-val">' + pct + '%</span>'
        + '</div>';
    }).join('');
    legend.innerHTML = '<div class="ca-legend-grid">' + rows + '</div>';
  }

  // ── 등락 전용 바 차트 ────────────────────────────────────────────────────

  function renderMoversChart(canvas, series, labels) {
    if (!canvas) return;
    var dpr = window.devicePixelRatio || 1;
    var rect = canvas.getBoundingClientRect();
    var W = Math.max(1, Math.floor(rect.width));
    var H = Math.max(1, Math.floor(rect.height));
    canvas.width = Math.floor(W * dpr);
    canvas.height = Math.floor(H * dpr);
    var ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);

    var maxAbs = 0;
    for (var i = 0; i < series.length; i++) maxAbs = Math.max(maxAbs, Math.abs(series[i] || 0));
    maxAbs = Math.max(maxAbs, 1);

    var ml = 10, mr = 10, mt = 14, mb = 14;
    var iW = W - ml - mr;
    var iH = H - mt - mb;
    var n = Math.max(1, series.length);
    var gap = 5;
    var bw = Math.max(6, (iW - gap * (n - 1)) / n);

    // 0 기준선
    var midY = mt + iH / 2;
    ctx.save();
    ctx.strokeStyle = 'rgba(234,240,255,.20)';
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    ctx.beginPath(); ctx.moveTo(ml, midY); ctx.lineTo(ml + iW, midY); ctx.stroke();
    ctx.restore();

    // 바
    ctx.save();
    for (var k = 0; k < series.length; k++) {
      var v = series[k] || 0;
      var hh = Math.max(2, (iH / 2) * (Math.abs(v) / maxAbs));
      var x = ml + k * (bw + gap);
      if (v >= 0) {
        ctx.fillStyle = 'rgba(154,247,208,.82)';
        ctx.fillRect(x, midY - hh, bw, hh);
      } else {
        ctx.fillStyle = 'rgba(255,122,217,.82)';
        ctx.fillRect(x, midY, bw, hh);
      }
    }
    ctx.restore();

    // 범위 표시 (최대 절댓값)
    ctx.save();
    ctx.fillStyle = 'rgba(234,240,255,.45)';
    ctx.font = '10px ui-sans-serif,system-ui,sans-serif';
    ctx.textAlign = 'right';
    ctx.textBaseline = 'top';
    ctx.fillText('+' + maxAbs.toFixed(1) + '%', ml + iW, mt);
    ctx.textBaseline = 'bottom';
    ctx.fillText('-' + maxAbs.toFixed(1) + '%', ml + iW, mt + iH);
    ctx.restore();
  }

  // ── 유틸 ─────────────────────────────────────────────────────────────────

  function escHtml(s) {
    return String(s || '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function escAttr(s) { return escHtml(s); }

  // ── 초기화 ───────────────────────────────────────────────────────────────

  function init() {
    if (!window.EtApi) return;

    window.EtApi.fetchJson('/api/custom-analysis/meta')
      .then(function (meta) {
        renderCategoryBtns(meta.categories || []);
        renderMethodBtns(meta.methods || []);
      })
      .catch(function () {/* meta 로드 실패는 무시 */});

    initYearInput();

    var runBtn = qs('#ca-run-btn');
    if (runBtn) runBtn.addEventListener('click', runAnalysis);
  }

  document.addEventListener('DOMContentLoaded', init);
})();
