(function () {
  function byId(id) {
    return document.getElementById(id);
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

  function fetchJson(path, opts) {
    return window.EtApi.fetchJson(path, opts);
  }

  function escapeHtml(s) {
    var d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
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

  function renderCategoryButtons(categories) {
    var root = byId("category-pick");
    if (!root) return;
    root.innerHTML = "";
    (categories || []).forEach(function (label) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "chip chip--category";
      btn.textContent = label;
      btn.setAttribute("data-category", label);
      btn.setAttribute("aria-pressed", "false");
      root.appendChild(btn);
    });
  }

  function setCategorySelected(label) {
    var root = byId("category-pick");
    if (!root) return;
    root.querySelectorAll("[data-category]").forEach(function (btn) {
      var l = btn.getAttribute("data-category") || "";
      var on = l === label;
      btn.classList.toggle("is-active", on);
      btn.setAttribute("aria-pressed", on ? "true" : "false");
    });
  }

  function renderSavedList(items) {
    var panel = byId("saved-in-category-panel");
    var empty = byId("saved-in-category-empty");
    var ul = byId("saved-in-category-list");
    if (!panel || !empty || !ul) return;
    panel.hidden = false;
    ul.innerHTML = "";
    var arr = items || [];
    if (!arr.length) {
      empty.hidden = false;
      ul.hidden = true;
      return;
    }
    empty.hidden = true;
    ul.hidden = false;
    arr.forEach(function (it) {
      var li = document.createElement("li");
      var a = document.createElement("a");
      var cat = it.category_label || state.categoryLabel || "";
      a.href =
        "./my-analysis.html?category=" +
        encodeURIComponent(cat) +
        "&keyword=" +
        encodeURIComponent(it.keyword || "") +
        "&metric=" +
        encodeURIComponent(it.metric || "") +
        "&label=" +
        encodeURIComponent(it.metric_label || "");
      a.innerHTML =
        "<strong>" +
        escapeHtml(it.title || "(제목 없음)") +
        "</strong>" +
        '<span class="saved-meta">' +
        escapeHtml(it.keyword || "") +
        " · " +
        escapeHtml(it.metric_label || it.metric || "") +
        "</span>";
      li.appendChild(a);
      ul.appendChild(li);
    });
  }

  function loadSavedInCategory() {
    if (!state.categoryLabel) return;
    fetchJson("/api/builder/saved?category=" + encodeURIComponent(state.categoryLabel), { method: "GET" })
      .then(function (json) {
        var items = json && Array.isArray(json.items) ? json.items : [];
        renderSavedList(items);
      })
      .catch(function () {
        renderSavedList([]);
      });
  }

  var state = {
    keyword: "",
    categoryLabel: "",
    metric: "",
    metricLabel: "",
    metricDesc: "",
    lastMetricData: null,
    classifications: []
  };

  function suggestionsUrl(keyword) {
    var q = "/api/builder/suggestions?keyword=" + encodeURIComponent(keyword || "");
    if (state.categoryLabel) {
      q += "&category=" + encodeURIComponent(state.categoryLabel);
    }
    return q;
  }

  document.addEventListener("DOMContentLoaded", function () {
    window.EtAuth.requireAuth({ redirect: true }).then(function (allowed) {
      if (!allowed) return;

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

      function loadSuggestionsFromServer() {
        if (!state.categoryLabel) return;
        setAlert(error, "");
        fetchJson(suggestionsUrl(""), { method: "GET" })
          .then(function (json) {
            var list = json && Array.isArray(json.suggestions) ? json.suggestions : [];
            renderSuggestions(list);
            if (sugPanel) sugPanel.hidden = false;
            if (resultPanel) resultPanel.hidden = true;
            var has = list.length > 0;
            if (noSug) noSug.hidden = has;
            if (chatForm) chatForm.hidden = has;
          })
          .catch(function (reason) {
            setAlert(error, reason && reason.message ? reason.message : "추천 목록을 불러오지 못했습니다.");
          });
      }

      function selectCategory(label) {
        state.categoryLabel = String(label || "").trim();
        if (!state.categoryLabel) return;
        setCategorySelected(state.categoryLabel);
        var ks = byId("keyword-step");
        if (ks) ks.hidden = false;
        if (sugPanel) sugPanel.hidden = true;
        if (resultPanel) resultPanel.hidden = true;
        if (noSug) noSug.hidden = true;
        state.metric = "";
        state.lastMetricData = null;
        loadSavedInCategory();
        loadSuggestionsFromServer();
      }

      function applyMetric(metricId, label, desc) {
        state.metric = metricId;
        state.metricLabel = label || metricId;
        state.metricDesc = desc || "";

        var kwTrim = String(state.keyword || "").trim();
        if (!kwTrim) {
          state.keyword = state.metricLabel;
          if (keywordInput) keywordInput.value = state.keyword;
        }

        if (resultTitle) resultTitle.textContent = state.keyword + " · " + state.metricLabel;
        if (metricDesc) metricDesc.textContent = state.metricDesc || "선택한 지표 추세";

        fetchJson(
          "/api/builder/metric?keyword=" +
            encodeURIComponent(state.keyword) +
            "&metric=" +
            encodeURIComponent(state.metric),
          { method: "GET" }
        )
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
          .catch(function (reason) {
            setAlert(error, reason && reason.message ? reason.message : "지표 데이터를 불러오지 못했습니다.");
          });
      }

      fetchJson("/api/builder/classifications", { method: "GET" })
        .then(function (json) {
          var cats = (json && Array.isArray(json.classifications)) ? json.classifications : [];
          state.classifications = cats;
          renderCategoryButtons(cats);
          if (!cats.length) {
            setAlert(error, "등록된 분류가 없습니다. DB의 builder_keyword_catalog에 행을 추가하세요.");
          }

          var categoryRoot = byId("category-pick");
          if (categoryRoot) {
            categoryRoot.addEventListener("click", function (e) {
              var t = e.target;
              if (!t || !t.matches || !t.matches("button[data-category]")) return;
              var cat = t.getAttribute("data-category") || "";
              selectCategory(cat);
            });
          }

          try {
            var params = new URLSearchParams(window.location.search || "");
            var catParam = params.get("category");
            var kw = params.get("keyword");
            var metric = params.get("metric");
            var label = params.get("label");

            if (catParam && cats.indexOf(catParam) >= 0) {
              selectCategory(catParam);
              if (kw && keywordInput) keywordInput.value = kw;
              state.keyword = kw || "";

              if (kw) {
                fetchJson(suggestionsUrl(kw))
                  .then(function (j) {
                    var list = j && Array.isArray(j.suggestions) ? j.suggestions : [];
                    renderSuggestions(list);
                    if (sugPanel) sugPanel.hidden = false;

                    if (metric) {
                      var found = null;
                      for (var i = 0; i < list.length; i++) {
                        if (list[i].id === metric) {
                          found = list[i];
                          break;
                        }
                      }
                      applyMetric(metric, (found && found.label) || label || metric, (found && found.description) || "");
                    }
                  })
                  .catch(function () {});
              } else if (metric) {
                applyMetric(metric, label || metric, "");
              }
            }
          } catch (e) {
            // ignore
          }
        })
        .catch(function (reason) {
          setAlert(error, reason && reason.message ? reason.message : "분류 목록을 불러오지 못했습니다.");
        });

      if (form) {
        form.addEventListener("submit", function (e) {
          e.preventDefault();
          setAlert(error, "");
          setAlert(chatAnswer, "");
          if (saveOk) saveOk.hidden = true;
          if (saveErr) saveErr.hidden = true;

          if (!state.categoryLabel) {
            setAlert(error, "먼저 위에서 분류를 선택해 주세요.");
            return;
          }

          state.keyword = String(keywordInput && keywordInput.value ? keywordInput.value : "").trim();
          state.metric = "";
          state.lastMetricData = null;

          fetchJson(suggestionsUrl(state.keyword), { method: "GET" })
            .then(function (json) {
              var list = json && Array.isArray(json.suggestions) ? json.suggestions : [];
              renderSuggestions(list);
              if (sugPanel) sugPanel.hidden = false;
              if (resultPanel) resultPanel.hidden = true;

              var has = list.length > 0;
              if (noSug) noSug.hidden = has;
              if (chatForm) chatForm.hidden = has;
            })
            .catch(function (reason) {
              setAlert(error, reason && reason.message ? reason.message : "추천 카테고리를 불러오지 못했습니다.");
            });
        });
      }

      var sugRoot = byId("suggestions");
      if (sugRoot) {
        sugRoot.addEventListener("click", function (e) {
          var t = e.target;
          if (!t || !t.matches || !t.matches("button[data-metric]")) return;
          var metricId = t.getAttribute("data-metric") || "";
          var lbl = t.textContent || metricId;
          var desc = t.getAttribute("data-desc") || "";
          applyMetric(metricId, lbl, desc);
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
          var payload = { keyword: state.keyword, question: q };
          fetchJson("/api/builder/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
          })
            .then(function (json) {
              setAlert(chatAnswer, (json && json.answer) || "응답을 받지 못했습니다.");
            })
            .catch(function (reason) {
              setAlert(chatAnswer, reason && reason.message ? reason.message : "챗봇 요청에 실패했습니다.");
            });
        });
      }

      if (saveForm) {
        saveForm.addEventListener("submit", function (e) {
          e.preventDefault();
          if (saveOk) saveOk.hidden = true;
          if (saveErr) saveErr.hidden = true;

          if (!state.categoryLabel) {
            setAlert(saveErr, "분류가 선택되지 않았습니다.");
            return;
          }
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
            title: title,
            keyword: state.keyword,
            metric: state.metric,
            metric_label: state.metricLabel,
            category_label: state.categoryLabel
          };
          fetchJson("/api/builder/save", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
          })
            .then(function () {
              setAlert(saveOk, "저장 완료! ‘내 분석 보기’에서 확인할 수 있어요.");
              loadSavedInCategory();
            })
            .catch(function (reason) {
              setAlert(saveErr, reason && reason.message ? reason.message : "저장에 실패했습니다.");
            });
        });
      }
    });
  });
})();
