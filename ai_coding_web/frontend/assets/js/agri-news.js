(function () {
  var currentCrop = "";

  function formatDate(isoStr) {
    if (!isoStr) return "";
    try {
      var d = new Date(isoStr);
      var pad = function (n) { return n < 10 ? "0" + n : String(n); };
      return d.getFullYear() + "." + pad(d.getMonth() + 1) + "." + pad(d.getDate())
        + " " + pad(d.getHours()) + ":" + pad(d.getMinutes());
    } catch (e) { return ""; }
  }

  function renderNews(items) {
    var list = document.getElementById("news-list");
    var count = document.getElementById("news-count");
    if (!list) return;

    if (!items || items.length === 0) {
      list.innerHTML = '<p class="news-empty">뉴스를 찾을 수 없습니다.<br>잠시 후 다시 시도하거나 다른 품목을 선택하세요.</p>';
      if (count) count.textContent = "0건";
      return;
    }

    if (count) count.textContent = items.length + "건";

    var html = items.map(function (item) {
      var date = formatDate(item.published_at);
      var summary = (item.summary || "").replace(/<[^>]+>/g, "").trim();
      var summaryHtml = summary ? '<p class="news-item__summary">' + escapeHtml(summary.slice(0, 120)) + (summary.length > 120 ? "…" : "") + "</p>" : "";
      return [
        '<article class="news-item">',
        '  <p class="news-item__title"><a href="' + escapeHtml(item.url) + '" target="_blank" rel="noopener noreferrer">' + escapeHtml(item.title) + "</a></p>",
        summaryHtml,
        '  <p class="news-item__meta">' + (date ? date : "") + "</p>",
        "</article>"
      ].join("\n");
    }).join("\n");

    list.innerHTML = html;
  }

  function escapeHtml(str) {
    return String(str || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function loadNews(crop) {
    var list = document.getElementById("news-list");
    var count = document.getElementById("news-count");
    if (list) list.innerHTML = '<p class="news-empty">뉴스를 불러오는 중…</p>';
    if (count) count.textContent = "불러오는 중…";

    var path = "/api/agri/news?limit=40" + (crop ? "&crop=" + encodeURIComponent(crop) : "");
    window.EtApi.fetchJson(path)
      .then(function (data) {
        renderNews(Array.isArray(data) ? data : []);
      })
      .catch(function (err) {
        if (list) list.innerHTML = '<p class="news-empty">뉴스를 불러오지 못했습니다.<br>' + escapeHtml(String(err.message || err)) + "</p>";
        if (count) count.textContent = "오류";
      });
  }

  function initFilters() {
    var filters = document.getElementById("crop-filters");
    if (!filters) return;
    filters.addEventListener("click", function (e) {
      var btn = e.target;
      if (!btn || !btn.matches || !btn.matches("[data-crop]")) return;
      filters.querySelectorAll(".chip").forEach(function (c) { c.classList.remove("is-active"); });
      btn.classList.add("is-active");
      currentCrop = btn.getAttribute("data-crop") || "";
      loadNews(currentCrop);
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initFilters();
    loadNews("");
  });
})();
