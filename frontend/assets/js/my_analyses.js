(function () {
  function byId(id) {
    return document.getElementById(id);
  }

  function getApiBase() {
    if (window.ET_API_BASE) return String(window.ET_API_BASE).replace(/\/+$/, "");
    return "http://127.0.0.1:8000";
  }

  function getUserEmail() {
    var user = window.EtAuth && window.EtAuth.getUser ? window.EtAuth.getUser() : null;
    return user && user.email ? String(user.email) : "";
  }

  function fetchJson(url) {
    return fetch(url, { method: "GET" }).then(function (res) {
      if (!res.ok) throw new Error("bad response");
      return res.json();
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    // 이 페이지는 로그인 필요
    if (window.EtAuth) {
      var ok = window.EtAuth.requireAuth({ redirect: true });
      if (!ok) return;
    }

    var empty = byId("list-empty");
    var table = byId("list-table");
    var user = getUserEmail();
    var url = getApiBase() + "/api/builder/saved?user=" + encodeURIComponent(user);

    fetchJson(url)
      .then(function (json) {
        var items = json && Array.isArray(json.items) ? json.items : [];
        if (!items.length) {
          if (empty) empty.hidden = false;
          if (table) table.hidden = true;
          return;
        }
        if (empty) empty.hidden = true;
        if (table) table.hidden = false;

        items.forEach(function (it) {
          var tr = document.createElement("tr");
          var a = document.createElement("a");
          a.href = "./my-analysis.html?keyword=" + encodeURIComponent(it.keyword) + "&metric=" + encodeURIComponent(it.metric) + "&label=" + encodeURIComponent(it.metric_label || "");
          a.textContent = it.title || "(제목 없음)";

          var td1 = document.createElement("td");
          td1.appendChild(a);
          var td2 = document.createElement("td");
          td2.textContent = it.keyword || "";
          var td3 = document.createElement("td");
          td3.textContent = it.metric_label || it.metric || "";
          var td4 = document.createElement("td");
          td4.textContent = it.saved_at || "";

          tr.appendChild(td1);
          tr.appendChild(td2);
          tr.appendChild(td3);
          tr.appendChild(td4);
          table.appendChild(tr);
        });
      })
      .catch(function () {
        if (empty) {
          empty.hidden = false;
          empty.textContent = "목록을 불러오지 못했습니다. (백엔드 실행/주소 확인)";
        }
        if (table) table.hidden = true;
      });
  });
})();
