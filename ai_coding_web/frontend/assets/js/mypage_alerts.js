(function () {
  'use strict';

  function qs(sel) { return document.querySelector(sel); }
  function byId(id) { return document.getElementById(id); }

  function escHtml(s) {
    return String(s || '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function conditionLabel(c) {
    return c === 'above' ? '초과' : '미만';
  }

  // ── 알림 체크 (현재 가격 vs 임계값) ─────────────────────────────────────

  function loadAndCheck() {
    window.EtApi.fetchJson('/api/alerts/check')
      .then(function (data) {
        renderTriggered(data.items || [], data.survey_date || '');
        renderList(data.items || []);
      })
      .catch(function () {
        var empty = byId('alerts-empty');
        if (empty) { empty.hidden = false; empty.textContent = '알림 정보를 불러오지 못했습니다.'; }
      });
  }

  // ── 발동된 알림 표시 ──────────────────────────────────────────────────────

  function renderTriggered(items, surveyDate) {
    var triggered = items.filter(function (it) { return it.triggered === true; });
    var panel = byId('alerts-triggered');
    var list = byId('alerts-triggered-list');
    var none = byId('alerts-none');
    var dateEl = byId('alerts-survey-date');

    if (!triggered.length) {
      if (panel) panel.hidden = true;
      if (none) none.hidden = false;
      return;
    }

    if (none) none.hidden = true;
    if (panel) panel.hidden = false;
    if (dateEl && surveyDate) dateEl.textContent = '최신 조사일: ' + surveyDate;

    if (!list) return;
    list.innerHTML = triggered.map(function (it) {
      var cur = it.current_price != null ? Number(it.current_price).toLocaleString('ko-KR') + '원' : '—';
      var thr = Number(it.threshold).toLocaleString('ko-KR') + '원';
      return '<li class="builder-saved-item alert--error" style="border-radius:8px;padding:10px 14px;margin-bottom:6px;list-style:none">'
        + '<strong>' + escHtml(it.name) + '</strong>'
        + ' — <span>' + escHtml(it.item_name) + ' 현재 ' + cur + ' / 기준 ' + thr + ' ' + conditionLabel(it.condition) + '</span>'
        + '</li>';
    }).join('');
  }

  // ── 전체 알림 목록 ────────────────────────────────────────────────────────

  function renderList(items) {
    var listEl = byId('alerts-list');
    var emptyEl = byId('alerts-empty');

    if (!items.length) {
      if (emptyEl) emptyEl.hidden = false;
      if (listEl) listEl.hidden = true;
      return;
    }

    if (emptyEl) emptyEl.hidden = true;
    if (!listEl) return;
    listEl.hidden = false;

    listEl.innerHTML = items.map(function (it) {
      var cur = it.current_price != null ? Number(it.current_price).toLocaleString('ko-KR') + '원' : '데이터 없음';
      var thr = Number(it.threshold).toLocaleString('ko-KR') + '원';
      var statusDot = it.triggered === true
        ? '<span style="color:#e85d6f;font-weight:700">● </span>'
        : it.triggered === false
          ? '<span style="color:#9AF7D0;font-weight:700">● </span>'
          : '<span style="color:#888;font-weight:700">● </span>';
      return '<li style="display:flex;align-items:center;justify-content:space-between;padding:10px 14px;margin-bottom:6px;background:var(--surface2,#1a1d2e);border-radius:8px;list-style:none">'
        + '<span>' + statusDot + escHtml(it.name)
        + ' <span class="muted">(' + escHtml(it.item_name) + ' ' + thr + ' ' + conditionLabel(it.condition) + ' / 현재 ' + cur + ')</span>'
        + '</span>'
        + '<button class="btn btn--ghost btn--sm" data-delete-id="' + it.id + '" style="flex-shrink:0;margin-left:12px">삭제</button>'
        + '</li>';
    }).join('');

    listEl.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-delete-id]');
      if (!btn) return;
      deleteAlert(parseInt(btn.dataset.deleteId, 10));
    });
  }

  // ── 알림 삭제 ────────────────────────────────────────────────────────────

  function deleteAlert(id) {
    window.EtApi.fetchJson('/api/alerts/' + id, { method: 'DELETE' })
      .then(function () { loadAndCheck(); })
      .catch(function () {});
  }

  // ── 알림 추가 폼 ─────────────────────────────────────────────────────────

  function initForm() {
    var form = byId('alert-form');
    if (!form) return;

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var itemInput = byId('alert-item');
      var condInput = byId('alert-condition');
      var thrInput = byId('alert-threshold');
      var nameInput = byId('alert-name');
      var errEl = byId('alert-form-err');
      var okEl = byId('alert-form-ok');

      if (errEl) errEl.hidden = true;
      if (okEl) okEl.hidden = true;

      var itemName = (itemInput ? itemInput.value : '').trim();
      var condition = condInput ? condInput.value : 'above';
      var threshold = parseFloat(thrInput ? thrInput.value : '');
      var nameVal = (nameInput ? nameInput.value : '').trim()
        || itemName + ' ' + (threshold || '') + '원 ' + conditionLabel(condition);

      if (!itemName) {
        if (errEl) { errEl.textContent = '품목명을 입력하세요.'; errEl.hidden = false; }
        return;
      }
      if (isNaN(threshold) || threshold <= 0) {
        if (errEl) { errEl.textContent = '기준 가격을 올바르게 입력하세요.'; errEl.hidden = false; }
        return;
      }

      var btn = form.querySelector('button[type=submit]');
      if (btn) btn.disabled = true;

      window.EtApi.fetchJson('/api/alerts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: nameVal, item_name: itemName, condition: condition, threshold: threshold }),
      })
        .then(function () {
          if (okEl) { okEl.textContent = '알림이 추가되었습니다.'; okEl.hidden = false; }
          form.reset();
          loadAndCheck();
        })
        .catch(function (err) {
          if (errEl) { errEl.textContent = err && err.message ? err.message : '추가에 실패했습니다.'; errEl.hidden = false; }
        })
        .finally(function () {
          if (btn) btn.disabled = false;
        });
    });
  }

  // ── 초기화 ────────────────────────────────────────────────────────────────

  document.addEventListener('DOMContentLoaded', function () {
    if (!window.EtAuth || !window.EtApi) return;
    window.EtAuth.requireAuth({ redirect: false }).then(function (allowed) {
      if (!allowed) {
        var panel = byId('alerts-panel');
        if (panel) panel.hidden = true;
        return;
      }
      loadAndCheck();
      initForm();
    });
  });
})();
