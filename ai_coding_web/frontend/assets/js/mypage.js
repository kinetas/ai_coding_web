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

      // Fill form from current user
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
            setAlert(err, "Enter a nickname.");
            return;
          }

          window.EtApi.fetchJson("/api/auth/profile", {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ nickname: nickname })
          })
            .then(function () {
              setAlert(ok, "Nickname saved.");
            })
            .catch(function (error) {
              setAlert(err, error && error.message ? error.message : "Save failed.");
            });
        });
      }

      if (delBtn) {
        delBtn.addEventListener("click", function () {
          setAlert(delErr, "");
          if (!delInput || String(delInput.value || "").trim().toUpperCase() !== "DELETE") {
            setAlert(delErr, "Type DELETE exactly to confirm.");
            return;
          }
          if (!window.confirm("Delete your account? This cannot be undone.")) {
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
              setAlert(delErr, error && error.message ? error.message : "Account deletion failed.");
            });
        });
      }
    });
  });
})();


const PRESET_TEMPLATES = [
  {
    id: 'agri_price',
    label: 'Agri price trend',
    icon: '🥬',
    desc: 'Spot major crop price moves at a glance',
    widget: { type: 'chart', endpoint: '/api/public/price', chart_type: 'line' }
  },
  {
    id: 'weekly_news',
    label: 'Weekly news keywords',
    icon: '📰',
    desc: 'Word cloud of this week’s top keywords',
    widget: { type: 'wordcloud', endpoint: '/api/public/news/wordcloud' }
  },
  {
    id: 'category_issue',
    label: 'Category issue trends',
    icon: '📊',
    desc: 'News frequency trends by category',
    widget: { type: 'chart', endpoint: '/api/public/category', chart_type: 'bar' }
  }
];

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
  if (!window.EtAuth || !window.EtAuth.isAuthed()) {
    alert('Please sign in to use this.');
    window.location.href = './login.html';
    return;
  }
  try {
    await window.EtApi.fetchJson('/api/builder/widget', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: preset.label, config: preset.widget })
    });
    alert(`Widget '${preset.label}' was added.`);
    location.reload();
  } catch (e) {
    alert(e && e.message ? e.message : 'Could not add widget. Try again.');
  }
}

document.addEventListener('DOMContentLoaded', renderPresetCards);
