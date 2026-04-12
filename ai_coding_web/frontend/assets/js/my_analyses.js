(function () {
  'use strict';

  var CATEGORY_LABELS = { agri: '농산물', health: '보건', traffic: '교통', tour: '관광', env: '환경' };
  var METHOD_LABELS = { trend: '추이', compare: '비교', distribution: '비중', movers: '등락' };

  function byId(id) { return document.getElementById(id); }

  function escHtml(s) {
    return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function fmtDate(iso) {
    if (!iso) return '';
    return iso.replace('T', ' ').slice(0, 16);
  }

  // ── 커스텀 분석 목록 ──────────────────────────────────────────────────────

  function loadCustomAnalyses() {
    var empty = byId('ca-list-empty');
    var table = byId('ca-list-table');
    var tbody = byId('ca-saved-list-body');

    window.EtApi.fetchJson('/api/custom-analysis/saved')
      .then(function (json) {
        var items = json && Array.isArray(json.items) ? json.items : [];
        if (!items.length) {
          if (empty) empty.hidden = false;
          if (table) table.hidden = true;
          return;
        }
        if (empty) empty.hidden = true;
        if (table) table.hidden = false;
        if (tbody) tbody.innerHTML = '';

        items.forEach(function (it) {
          var tr = document.createElement('tr');

          // 이름 (클릭 → 분석 만들기 복원)
          var href = './my-analysis.html'
            + '?ca_category=' + encodeURIComponent(it.category)
            + '&ca_subcategory=' + encodeURIComponent(it.subcategory)
            + '&ca_item=' + encodeURIComponent(it.item || 'all')
            + '&ca_year_from=' + encodeURIComponent(it.year_from)
            + '&ca_year_to=' + encodeURIComponent(it.year_to)
            + '&ca_method=' + encodeURIComponent(it.method);

          var td1 = document.createElement('td');
          td1.innerHTML = '<a href="' + escHtml(href) + '">' + escHtml(it.title || '(제목 없음)') + '</a>';

          var tdCat = document.createElement('td');
          tdCat.textContent = CATEGORY_LABELS[it.category] || it.category;

          var tdSub = document.createElement('td');
          tdSub.textContent = (it.item && it.item !== 'all') ? it.item : (it.subcategory || '전체');

          var tdMethod = document.createElement('td');
          tdMethod.textContent = METHOD_LABELS[it.method] || it.method;

          var tdYear = document.createElement('td');
          tdYear.textContent = it.year_from === it.year_to ? String(it.year_from) : it.year_from + '~' + it.year_to;

          var tdLive = document.createElement('td');
          if (it.live) {
            var badge = document.createElement('span');
            badge.style.cssText = 'background:var(--accent,#00D4FF);color:#000;font-size:.75rem;padding:2px 7px;border-radius:20px;font-weight:700;white-space:nowrap';
            badge.textContent = '최신 4주';
            tdLive.appendChild(badge);
          }

          var tdDate = document.createElement('td');
          tdDate.textContent = fmtDate(it.saved_at);

          // 알림 설정 버튼 (농산물 + 특정 품목인 경우만)
          var tdAlert = document.createElement('td');
          if (it.category === 'agri' && it.item && it.item !== 'all') {
            var alertBtn = document.createElement('button');
            alertBtn.className = 'btn btn--ghost btn--sm';
            alertBtn.textContent = '알림 설정';
            alertBtn.dataset.alertItem = it.item;
            tdAlert.appendChild(alertBtn);
          }

          tr.appendChild(td1);
          tr.appendChild(tdCat);
          tr.appendChild(tdSub);
          tr.appendChild(tdMethod);
          tr.appendChild(tdYear);
          tr.appendChild(tdLive);
          tr.appendChild(tdDate);
          tr.appendChild(tdAlert);
          if (tbody) tbody.appendChild(tr);
        });

        // 알림 설정 버튼 이벤트 위임
        if (tbody) {
          tbody.addEventListener('click', function (e) {
            var btn = e.target.closest('[data-alert-item]');
            if (!btn) return;
            prefillAlert(btn.dataset.alertItem);
          });
        }
      })
      .catch(function (reason) {
        if (empty) {
          empty.hidden = false;
          empty.textContent = reason && reason.message ? reason.message : '목록을 불러오지 못했습니다.';
        }
        if (table) table.hidden = true;
      });
  }

  // ── 알림 폼 사전 입력 ─────────────────────────────────────────────────────

  function prefillAlert(itemName) {
    var itemInput = byId('alert-item');
    var nameInput = byId('alert-name');
    var formSection = byId('alerts-panel');

    if (itemInput) itemInput.value = itemName;
    if (nameInput && !nameInput.value) nameInput.value = itemName + ' 가격 알림';

    if (formSection) {
      formSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    if (itemInput) setTimeout(function () { itemInput.focus(); }, 400);
  }

  // ── 초기화 ────────────────────────────────────────────────────────────────

  document.addEventListener('DOMContentLoaded', function () {
    window.EtAuth.requireAuth({ redirect: true }).then(function (allowed) {
      if (!allowed) return;
      loadCustomAnalyses();
    });
  });
})();
