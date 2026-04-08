(function () {
  function $(sel) {
    return document.querySelector(sel);
  }

  function setAlert(el, msg) {
    if (!el) return;
    var m = String(msg || "").trim();
    if (!m) {
      el.hidden = true;
      el.textContent = "";
      return;
    }
    el.hidden = false;
    el.textContent = m;
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (!window.EtAuth || !window.EtAuth.init) {
      return;
    }

    var form = $("#profile-form");
    var nick = $("#field-nickname");
    var email = $("#field-email");
    var err = $("#profile-error");
    var ok = $("#profile-success");
    var delErr = $("#delete-error");
    var delBtn = $("#delete-account-btn");
    var delInput = $("#delete-confirm");

    window.EtAuth.requireAuth({ redirect: true }).then(function (allowed) {
      if (!allowed) return;

      // 현재 로그인 사용자 정보로 폼 채우기
      var user = window.EtAuth.getUser();
      if (user) {
        if (nick) nick.value = user.nickname || "";
        if (email) email.value = user.email || "";
      }

      if (form) {
        form.addEventListener("submit", function (e) {
          e.preventDefault();
          setAlert(err, "");
          setAlert(ok, "");

          var fd = new FormData(form);
          var nickname = String(fd.get("nickname") || "").trim();

          if (!nickname) {
            setAlert(err, "닉네임을 입력해 주세요.");
            return;
          }

          window.EtApi.fetchJson("/api/auth/profile", {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ nickname: nickname })
          })
            .then(function () {
              setAlert(ok, "닉네임이 저장되었습니다.");
            })
            .catch(function (error) {
              setAlert(err, error && error.message ? error.message : "저장에 실패했습니다.");
            });
        });
      }

      if (delBtn) {
        delBtn.addEventListener("click", function () {
          setAlert(delErr, "");
          if (!delInput || String(delInput.value || "").trim() !== "탈퇴") {
            setAlert(delErr, "확인 문구를 정확히 입력해 주세요.");
            return;
          }
          if (!window.confirm("정말 탈퇴하시겠습니까? 이 작업은 되돌릴 수 없습니다.")) {
            return;
          }

          window.EtApi.fetchJson("/api/auth/account", { method: "DELETE" })
            .then(function () {
              return window.EtAuth.logout();
            })
            .then(function () {
              window.location.href = "./login.html";
            })
            .catch(function (error) {
              setAlert(delErr, error && error.message ? error.message : "탈퇴 처리에 실패했습니다.");
            });
        });
      }
    });
  });
})();


// ── 기본 템플릿 프리셋 상수 ──────────────────────────────────────────
const PRESET_TEMPLATES = [
  {
    id: 'agri_price',
    label: '농산물 가격 추이',
    icon: '🥬',
    desc: '주요 농산물 가격 변동을 한눈에',
    widget: { type: 'chart', endpoint: '/api/public/price', chart_type: 'line' }
  },
  {
    id: 'weekly_news',
    label: '주간 뉴스 키워드',
    icon: '📰',
    desc: '이번 주 주목받은 키워드 워드클라우드',
    widget: { type: 'wordcloud', endpoint: '/api/public/news/wordcloud' }
  },
  {
    id: 'category_issue',
    label: '카테고리별 이슈 변화',
    icon: '📊',
    desc: '카테고리별 뉴스 빈도 추이',
    widget: { type: 'chart', endpoint: '/api/public/category', chart_type: 'bar' }
  }
];


// ── 프리셋 카드 렌더링 ────────────────────────────────────────────────
function renderPresetCards() {
  const grid = document.getElementById('preset-card-grid');
  if (!grid || typeof PRESET_TEMPLATES === 'undefined') return;
  grid.innerHTML = PRESET_TEMPLATES.map(t => `
    <div class="preset-card" onclick="applyPreset('${t.id}')">
      <span class="preset-card__icon">${t.icon}</span>
      <strong class="preset-card__label">${t.label}</strong>
      <p class="preset-card__desc">${t.desc}</p>
    </div>
  `).join('');
}

async function applyPreset(presetId) {
  const preset = (PRESET_TEMPLATES || []).find(t => t.id === presetId);
  if (!preset) return;
  // 비로그인 체크
  if (!window.EtAuth || !window.EtAuth.isAuthed()) {
    alert('로그인 후 이용할 수 있습니다.');
    window.location.href = './login.html';
    return;
  }
  try {
    await window.EtApi.fetchJson('/api/builder/widget', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: preset.label, config: preset.widget })
    });
    alert(`'${preset.label}' 위젯이 추가됐습니다.`);
    location.reload();
  } catch (e) {
    alert(e && e.message ? e.message : '위젯 추가에 실패했습니다. 다시 시도해 주세요.');
  }
}

document.addEventListener('DOMContentLoaded', renderPresetCards);
