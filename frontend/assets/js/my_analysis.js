(function () {
  function $(sel) {
    return document.querySelector(sel);
  }

  function byId(id) {
    return document.getElementById(id);
  }

  function getApiBase() {
    if (window.ET_API_BASE) return String(window.ET_API_BASE).replace(/\/+$/, "");
    return "http://127.0.0.1:8000";
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

  function getUserEmail() {
    var user = window.EtAuth && window.EtAuth.getUser ? window.EtAuth.getUser() : null;
    return user && user.email ? String(user.email) : "";
  }

  function fetchJson(url, opts) {
    return fetch(url, opts || {}).then(function (res) {
      if (!res.ok) throw new Error("bad response");
      return res.json();
    });
  }

  function renderSuggestions(list) {
    var root = byId("suggestions");
    if (!root) return;
    root.innerHTML = "";
    (list || []).forEach(function (sug) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "chip";
      btn.textContent = sug.label;
      btn.setAttribute("data-metric", sug.id);
      btn.setAttribute("data-desc", sug.description || "");
      root.appendChild(btn);
    });
  }

  var state = {
    keyword: "",
    metric: "",
    metricLabel: "",
    metricDesc: "",
    lastMetricData: null
  };

  document.addEventListener("DOMContentLoaded", function () {
    // 이 페이지는 로그인 필요
    if (window.EtAuth) {
      var ok = window.EtAuth.requireAuth({ redirect: true });
      if (!ok) return;
    }

    var form = byId("builder-form");
    var keywordInput = byId("keyword");
    var error = byId("builder-error");
    var sugPanel = byId("suggestions-panel");
    var noSug = byId("no-suggestions");
    var chatForm = byId("chat-form");
    var chatAnswer = byId("chat-answer");
    var resultPanel = byId("result-panel");
    var metricDesc = byId("metric-desc");
    var resultTitle = byId("result-title");

    var saveForm = byId("save-form");
    var saveTitle = byId("save-title");
    var saveOk = byId("save-ok");
    var saveErr = byId("save-err");

    function applyMetric(metricId, label, desc) {
      state.metric = metricId;
      state.metricLabel = label || metricId;
      state.metricDesc = desc || "";

      if (resultTitle) resultTitle.textContent = state.keyword + " · " + state.metricLabel;
      if (metricDesc) metricDesc.textContent = state.metricDesc || "선택한 지표 추세(예시)";

      var url = getApiBase() + "/api/builder/metric?keyword=" + encodeURIComponent(state.keyword) + "&metric=" + encodeURIComponent(state.metric);
      fetchJson(url, { method: "GET" })
        .then(function (data) {
          state.lastMetricData = data;
          if (resultPanel) resultPanel.hidden = false;

          var line = data && Array.isArray(data.line) ? data.line : [];
          var bar = data && Array.isArray(data.bar) ? data.bar : [];
          var accents = data && data.accents ? data.accents : {};

          if (window.EtCharts) {
            window.EtCharts.lineChart(byId("builder-line"), line, { accent: accents.line || "#6AE4FF" });
            window.EtCharts.barChart(byId("builder-bar"), bar, { accent: accents.bar || "#B79BFF" });
          }

          if (saveTitle && !saveTitle.value) {
            saveTitle.value = state.keyword + " " + state.metricLabel;
          }
        })
        .catch(function () {
          setAlert(error, "지표 데이터를 불러오지 못했습니다. (백엔드 실행/주소 확인)");
        });
    }

    if (form) {
      form.addEventListener("submit", function (e) {
        e.preventDefault();
        setAlert(error, "");
        setAlert(chatAnswer, "");
        if (saveOk) saveOk.hidden = true;
        if (saveErr) saveErr.hidden = true;

        state.keyword = String(keywordInput && keywordInput.value ? keywordInput.value : "").trim();
        state.metric = "";
        state.lastMetricData = null;
        if (!state.keyword) {
          setAlert(error, "키워드를 입력해 주세요.");
          return;
        }

        var url = getApiBase() + "/api/builder/suggestions?keyword=" + encodeURIComponent(state.keyword);
        fetchJson(url, { method: "GET" })
          .then(function (json) {
            var list = json && Array.isArray(json.suggestions) ? json.suggestions : [];
            renderSuggestions(list);
            if (sugPanel) sugPanel.hidden = false;
            if (resultPanel) resultPanel.hidden = true;

            var has = list.length > 0;
            if (noSug) noSug.hidden = has;
            if (chatForm) chatForm.hidden = has;
          })
          .catch(function () {
            setAlert(error, "추천 카테고리를 불러오지 못했습니다. (백엔드 실행/주소 확인)");
          });
      });
    }

    var sugRoot = byId("suggestions");
    if (sugRoot) {
      sugRoot.addEventListener("click", function (e) {
        var t = e.target;
        if (!t || !t.matches || !t.matches("button[data-metric]")) return;
        var metricId = t.getAttribute("data-metric") || "";
        var label = t.textContent || metricId;
        var desc = t.getAttribute("data-desc") || "";
        applyMetric(metricId, label, desc);
      });
    }

    if (chatForm) {
      chatForm.addEventListener("submit", function (e) {
        e.preventDefault();
        setAlert(chatAnswer, "");
        var q = String(byId("question") && byId("question").value ? byId("question").value : "").trim();
        if (!q) {
          setAlert(chatAnswer, "질문을 입력해 주세요.");
          return;
        }
        var payload = { user: getUserEmail(), keyword: state.keyword, question: q };
        fetchJson(getApiBase() + "/api/builder/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        })
          .then(function (json) {
            setAlert(chatAnswer, (json && json.answer) || "응답을 받지 못했습니다.");
          })
          .catch(function () {
            setAlert(chatAnswer, "챗봇 요청에 실패했습니다.");
          });
      });
    }

    if (saveForm) {
      saveForm.addEventListener("submit", function (e) {
        e.preventDefault();
        if (saveOk) saveOk.hidden = true;
        if (saveErr) saveErr.hidden = true;

        if (!state.keyword || !state.metric) {
          setAlert(saveErr, "먼저 추천 카테고리에서 지표를 선택해 주세요.");
          return;
        }
        var title = String(saveTitle && saveTitle.value ? saveTitle.value : "").trim();
        if (!title) {
          setAlert(saveErr, "저장 이름을 입력해 주세요.");
          return;
        }

        var payload = {
          user: getUserEmail(),
          title: title,
          keyword: state.keyword,
          metric: state.metric,
          metric_label: state.metricLabel
        };
        fetchJson(getApiBase() + "/api/builder/save", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        })
          .then(function () {
            setAlert(saveOk, "저장 완료! ‘내 분석 보기’에서 확인할 수 있어요.");
          })
          .catch(function () {
            setAlert(saveErr, "저장에 실패했습니다.");
          });
      });
    }

    // saved page에서 넘어온 파라미터로 자동 조회
    try {
      var params = new URLSearchParams(window.location.search || "");
      var kw = params.get("keyword");
      var metric = params.get("metric");
      var label = params.get("label");
      if (kw) {
        if (keywordInput) keywordInput.value = kw;
        state.keyword = kw;
        // 자동 추천/선택
        fetchJson(getApiBase() + "/api/builder/suggestions?keyword=" + encodeURIComponent(kw))
          .then(function (json) {
            var list = json && Array.isArray(json.suggestions) ? json.suggestions : [];
            renderSuggestions(list);
            if (sugPanel) sugPanel.hidden = false;

            if (metric) {
              // metric match
              var found = null;
              for (var i = 0; i < list.length; i++) {
                if (list[i].id === metric) { found = list[i]; break; }
              }
              applyMetric(metric, (found && found.label) || label || metric, (found && found.description) || "");
            }
          })
          .catch(function () {
            // ignore
          });
      }
    } catch (e) {
      // ignore
    }
  });
})();
