(function () {
  function byId(id) {
    return document.getElementById(id);
  }

  function fetchJson(path) {
    return window.EtApi.fetchJson(path, { method: "GET" });
  }

  document.addEventListener("DOMContentLoaded", function () {
    window.EtAuth.requireAuth({ redirect: true }).then(function (allowed) {
      if (!allowed) return;

      var empty = byId("list-empty");
      var table = byId("list-table");
      var tbody = byId("saved-list-body");

      fetchJson("/api/builder/saved")
        .then(function (json) {
          var items = json && Array.isArray(json.items) ? json.items : [];
          if (!items.length) {
            if (empty) empty.hidden = false;
            if (table) table.hidden = true;
            return;
          }
          if (empty) empty.hidden = true;
          if (table) table.hidden = false;
          if (tbody) tbody.innerHTML = "";

          items.forEach(function (it) {
            var tr = document.createElement("tr");
            var a = document.createElement("a");
            var cat = it.category_label || "";
            a.href =
              "./my-analysis.html?category=" +
              encodeURIComponent(cat) +
              "&keyword=" +
              encodeURIComponent(it.keyword) +
              "&metric=" +
              encodeURIComponent(it.metric) +
              "&label=" +
              encodeURIComponent(it.metric_label || "");
            a.textContent = it.title || "(Untitled)";

            var td1 = document.createElement("td");
            td1.appendChild(a);
            var tdCat = document.createElement("td");
            tdCat.textContent = cat || "—";
            var td2 = document.createElement("td");
            td2.textContent = it.keyword || "";
            var td3 = document.createElement("td");
            td3.textContent = it.metric_label || it.metric || "";
            var td4 = document.createElement("td");
            td4.textContent = it.saved_at || "";

            tr.appendChild(td1);
            tr.appendChild(tdCat);
            tr.appendChild(td2);
            tr.appendChild(td3);
            tr.appendChild(td4);
            if (tbody) tbody.appendChild(tr);
          });
        })
        .catch(function (reason) {
          if (empty) {
            empty.hidden = false;
            empty.textContent = reason && reason.message ? reason.message : "Could not load the list.";
          }
          if (table) table.hidden = true;
        });
    });
  });
})();
