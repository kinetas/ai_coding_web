(function () {
  'use strict';

  var DONUT_COLORS = ['#00D4FF', '#A78BFF', '#FFD36A', '#9AF7D0', '#FF7AD9', '#FF9F56', '#56CFFF', '#B4F26E'];

  var DEFAULT_YEAR = new Date().getFullYear() - 1;

  var state = {
    category: null,
    subcategory: null,
    item: 'all',
    yearFrom: DEFAULT_YEAR,
    yearTo: DEFAULT_YEAR,
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
    var ok = state.category && state.subcategory && state.yearFrom && state.yearTo
      && state.yearFrom <= state.yearTo && state.method && !state.loading;
    btn.disabled = !ok;
  }

  function setActiveSingle(groupId, code) {
    var group = document.getElementById(groupId);
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
      return '<button class="ca-btn" data-code="' + escAttr(cat.code) + '">' + escHtml(cat.label) + '</button>';
    }).join('');
  }

  function onCategoryBtn(btn) {
    var code = btn.dataset.code;
    if (state.category === code) return;
    state.category = code;
    state.subcategory = null;
    state.item = 'all';
    state.method = null;
    setActiveSingle('ca-category-group', code);
    lockStep(2); lockStep(3); lockStep(4); lockStep(5);
    resetSubcategoryBtns();
    resetItemBtns();
    resetMethodBtns();
    loadSubcategories(code);
    checkRunnable();
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
      })
      .catch(function () {
        group.innerHTML = '<span class="ca-placeholder">불러오기 실패</span>';
      });
  }

  function onSubcategoryBtn(btn) {
    var code = btn.dataset.code;
    // 같은 세부카테고리라도 품목이 아직 로드되지 않았으면 다시 시도
    if (state.subcategory === code && document.getElementById('ca-step-4').classList.contains('ca-step--locked') === false) return;
    state.subcategory = code;
    state.item = 'all';
    setActiveSingle('ca-subcategory-group', code);
    lockStep(3); lockStep(4); lockStep(5);
    resetItemBtns();
    resetMethodBtns();
    loadItems(state.category, code);
    checkRunnable();
  }

  function resetSubcategoryBtns() {
    var group = qs('#ca-subcategory-group');
    if (!group) return;
    group.innerHTML = '<span class="ca-placeholder">카테고리를 먼저 선택하세요</span>';
    state.subcategory = null;
  }

  // ── Step 3: 품목 ─────────────────────────────────────────────────────────

  function loadItems(category, subcategory) {
    var group = qs('#ca-item-group');
    if (!group) return;
    group.innerHTML = '<span class="ca-placeholder">불러오는 중…</span>';
    unlockStep(3);

    var url = '/api/custom-analysis/items'
      + '?category=' + encodeURIComponent(category)
      + '&subcategory=' + encodeURIComponent(subcategory);

    window.EtApi.fetchJson(url)
      .then(function (data) {
        var items = data.items || [];
        var allBtn = '<button class="ca-btn active" data-code="all">전체</button>';
        if (!items.length) {
          group.innerHTML = allBtn;
        } else {
          var itemBtns = items.map(function (it) {
            return '<button class="ca-btn" data-code="' + escAttr(it.code) + '">' + escHtml(it.label) + '</button>';
          }).join('');
          group.innerHTML = allBtn + itemBtns;
        }
        state.item = 'all';
        unlockStep(4);
        unlockStep(5);
        checkRunnable();
      })
      .catch(function () {
        // 오류 시에도 '전체'로 진행 가능하도록 unlock
        var group2 = qs('#ca-item-group');
        if (group2) group2.innerHTML = '<button class="ca-btn active" data-code="all">전체</button>';
        state.item = 'all';
        unlockStep(4);
        unlockStep(5);
        checkRunnable();
      });
  }

  function onItemBtn(btn) {
    state.item = btn.dataset.code;
    setActiveSingle('ca-item-group', state.item);
    checkRunnable();
  }

  function resetItemBtns() {
    var group = qs('#ca-item-group');
    if (!group) return;
    group.innerHTML = '<span class="ca-placeholder">세부 카테고리를 먼저 선택하세요</span>';
    state.item = 'all';
  }

  // ── Step 4: 기간 ─────────────────────────────────────────────────────────

  function initYearInputs() {
    var fromInput = qs('#ca-year-from');
    var toInput = qs('#ca-year-to');
    if (!fromInput || !toInput) return;

    fromInput.value = state.yearFrom;
    toInput.value = state.yearTo;

    function validateAndSync() {
      var from = parseInt(fromInput.value, 10);
      var to = parseInt(toInput.value, 10);
      if (!isNaN(from) && from >= 2018 && from <= 2030) {
        state.yearFrom = from;
      } else {
        fromInput.value = state.yearFrom;
      }
      if (!isNaN(to) && to >= 2018 && to <= 2030) {
        state.yearTo = to;
      } else {
        toInput.value = state.yearTo;
      }
      fromInput.style.borderColor = state.yearFrom > state.yearTo ? 'var(--danger, #e85d6f)' : '';
      toInput.style.borderColor = state.yearFrom > state.yearTo ? 'var(--danger, #e85d6f)' : '';
      checkRunnable();
    }

    fromInput.addEventListener('change', validateAndSync);
    toInput.addEventListener('change', validateAndSync);
  }

  // ── Step 5: 분석 방식 ────────────────────────────────────────────────────

  function renderMethodBtns(methods) {
    var group = qs('#ca-method-group');
    if (!group) return;
    group.innerHTML = methods.map(function (m) {
      return '<button class="ca-btn" data-code="' + escAttr(m.code) + '" title="' + escAttr(m.desc || '') + '">' + escHtml(m.label) + '</button>';
    }).join('');
  }

  function onMethodBtn(btn) {
    state.method = btn.dataset.code;
    setActiveSingle('ca-method-group', state.method);
    checkRunnable();
  }

  function resetMethodBtns() {
    var group = qs('#ca-method-group');
    if (!group) return;
    group.querySelectorAll('.ca-btn').forEach(function (b) { b.classList.remove('active'); });
    state.method = null;
  }

  // ── 저장 ─────────────────────────────────────────────────────────────────

  function showSaveRow() {
    var row = qs('#ca-save-row');
    var msg = qs('#ca-save-msg');
    var titleInput = qs('#ca-save-title');
    if (!row) return;
    row.hidden = false;
    if (msg) { msg.hidden = true; msg.textContent = ''; }
    if (titleInput && !titleInput.value) {
      // 기본 제목 자동 생성
      var cat = state.category || '';
      var sub = state.subcategory || '';
      var method = state.method || '';
      var methodLabel = { trend: '추이', compare: '비교', distribution: '비중', movers: '등락' }[method] || method;
      titleInput.value = (sub || cat) + ' ' + state.yearFrom
        + (state.yearFrom !== state.yearTo ? '~' + state.yearTo : '')
        + ' ' + methodLabel;
    }
  }

  function hideSaveRow() {
    var row = qs('#ca-save-row');
    if (row) row.hidden = true;
  }

  function saveAnalysis() {
    if (!window.EtApi) return;
    var titleInput = qs('#ca-save-title');
    var msgEl = qs('#ca-save-msg');
    var saveBtn = qs('#ca-save-btn');

    var title = (titleInput ? titleInput.value : '').trim();
    if (!title) {
      if (msgEl) { msgEl.textContent = '분석 이름을 입력하세요.'; msgEl.hidden = false; }
      if (titleInput) titleInput.focus();
      return;
    }

    if (saveBtn) saveBtn.disabled = true;
    if (msgEl) { msgEl.textContent = '저장 중…'; msgEl.hidden = false; }

    window.EtApi.fetchJson('/api/custom-analysis/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: title,
        category: state.category,
        subcategory: state.subcategory,
        item: state.item,
        year_from: state.yearFrom,
        year_to: state.yearTo,
        method: state.method,
      }),
    })
      .then(function () {
        if (msgEl) { msgEl.textContent = '저장되었습니다. 저장된 분석에서 확인하세요.'; msgEl.hidden = false; }
        if (saveBtn) { saveBtn.disabled = false; saveBtn.textContent = '다시 저장'; }
      })
      .catch(function (e) {
        var msg = (e && e.message) ? e.message : '저장에 실패했습니다. 로그인 후 이용하세요.';
        if (msgEl) { msgEl.textContent = msg; msgEl.hidden = false; }
        if (saveBtn) saveBtn.disabled = false;
      });
  }

  // ── 분석 실행 ────────────────────────────────────────────────────────────

  function runAnalysis() {
    if (!state.category || !state.subcategory || !state.yearFrom || !state.yearTo || !state.method) return;
    if (state.yearFrom > state.yearTo) return;
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
      + '&item=' + encodeURIComponent(state.item)
      + '&year_from=' + encodeURIComponent(state.yearFrom)
      + '&year_to=' + encodeURIComponent(state.yearTo)
      + '&method=' + encodeURIComponent(state.method);

    window.EtApi.fetchJson(url)
      .then(function (data) {
        state.loading = false;
        checkRunnable();
        renderResult(data);
        showSaveRow();
      })
      .catch(function (e) {
        state.loading = false;
        checkRunnable();
        hideSaveRow();
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

    var midY = mt + iH / 2;
    ctx.save();
    ctx.strokeStyle = 'rgba(234,240,255,.20)';
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    ctx.beginPath(); ctx.moveTo(ml, midY); ctx.lineTo(ml + iW, midY); ctx.stroke();
    ctx.restore();

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

  // ── 초기화 ── 이벤트 리스너는 여기서 한 번만 등록 ─────────────────────────

  function init() {
    if (!window.EtApi) return;

    // 메타 로드 (카테고리·분석방식) → 완료 후 URL 파라미터 복원
    window.EtApi.fetchJson('/api/custom-analysis/meta')
      .then(function (meta) {
        renderCategoryBtns(meta.categories || []);
        renderMethodBtns(meta.methods || []);
        _restoreFromParams();
      })
      .catch(function () {});

    initYearInputs();

    // 단일 위임: ca-step--locked의 pointer-events:none 영향을 받지 않는
    // 패널 루트에 등록. 버튼 소속 그룹을 closest()로 판별한다.
    var panel = document.getElementById('custom-analysis-panel');
    if (panel) {
      panel.addEventListener('click', function (e) {
        var btn = e.target.closest('.ca-btn');
        if (!btn) return;

        if (btn.closest('#ca-category-group'))    { onCategoryBtn(btn);    return; }
        if (btn.closest('#ca-subcategory-group')) { onSubcategoryBtn(btn); return; }
        if (btn.closest('#ca-item-group'))        { onItemBtn(btn);        return; }
        if (btn.closest('#ca-method-group'))      { onMethodBtn(btn);      return; }
      });
    }

    var runBtn = qs('#ca-run-btn');
    if (runBtn) runBtn.addEventListener('click', runAnalysis);

    var saveBtn = qs('#ca-save-btn');
    if (saveBtn) saveBtn.addEventListener('click', saveAnalysis);
  }

  // ── URL 파라미터 복원 (meta 로드 완료 후 호출) ───────────────────────────

  function _restoreFromParams() {
    var sp = new URLSearchParams(window.location.search);
    var cat = sp.get('ca_category');
    if (!cat) return;

    var sub = sp.get('ca_subcategory') || '';
    var item = sp.get('ca_item') || 'all';
    var yFrom = parseInt(sp.get('ca_year_from'), 10) || DEFAULT_YEAR;
    var yTo = parseInt(sp.get('ca_year_to'), 10) || DEFAULT_YEAR;
    var method = sp.get('ca_method') || 'trend';

    // 카테고리 선택
    var catBtn = document.querySelector('#ca-category-group [data-code="' + cat + '"]');
    if (!catBtn) return;
    onCategoryBtn(catBtn);

    // 서브카테고리 버튼이 생길 때까지 대기
    var attempts = 0;
    function waitAndSelect() {
      if (attempts++ > 20) return;
      var subBtn = document.querySelector('#ca-subcategory-group [data-code="' + sub + '"]');
      if (!subBtn) { return setTimeout(waitAndSelect, 150); }
      onSubcategoryBtn(subBtn);

      // step-4(기간)가 unlock될 때까지 대기
      var attempts2 = 0;
      function waitItem() {
        if (attempts2++ > 20) return;
        var step4 = document.getElementById('ca-step-4');
        if (!step4 || step4.classList.contains('ca-step--locked')) { return setTimeout(waitItem, 150); }
        // 품목
        if (item !== 'all') {
          var itemBtn = document.querySelector('#ca-item-group [data-code="' + item + '"]');
          if (itemBtn) onItemBtn(itemBtn);
        }
        // 기간
        var fromIn = qs('#ca-year-from');
        var toIn = qs('#ca-year-to');
        if (fromIn) { fromIn.value = yFrom; fromIn.dispatchEvent(new Event('change')); }
        if (toIn) { toIn.value = yTo; toIn.dispatchEvent(new Event('change')); }
        // 분석방식
        var mBtn = document.querySelector('#ca-method-group [data-code="' + method + '"]');
        if (mBtn) onMethodBtn(mBtn);
        // 자동 실행
        setTimeout(runAnalysis, 50);
      }
      setTimeout(waitItem, 150);
    }
    setTimeout(waitAndSelect, 150);
  }

  document.addEventListener('DOMContentLoaded', init);
})();
