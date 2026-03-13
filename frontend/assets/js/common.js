(function () {
  function getApiBase() {
    if (window.ET_APP_CONFIG && window.ET_APP_CONFIG.apiBase) {
      return String(window.ET_APP_CONFIG.apiBase).replace(/\/+$/, "");
    }
    if (window.ET_API_BASE) {
      return String(window.ET_API_BASE).replace(/\/+$/, "");
    }
    return "http://127.0.0.1:8000";
  }

  function buildApiUrl(path) {
    var p = String(path || "");
    if (/^https?:\/\//i.test(p)) return p;
    if (p && p[0] !== "/") p = "/" + p;
    return getApiBase() + p;
  }

  function parseJsonResponse(res) {
    if (!res.ok) {
      return res.json()
        .catch(function () { return {}; })
        .then(function (json) {
          var err = new Error((json && (json.detail || json.message)) || "요청에 실패했습니다.");
          err.status = res.status;
          throw err;
        });
    }
    return res.json();
  }

  function fetchJson(path, options) {
    var opts = options || {};
    var headers = opts.headers || {};
    return fetch(buildApiUrl(path), {
      method: opts.method || "GET",
      headers: headers,
      body: opts.body,
      credentials: opts.credentials || "include"
    }).then(parseJsonResponse);
  }

  function setActiveNavLink() {
    var page = document.body && document.body.dataset ? document.body.dataset.page : "";
    if (!page) return;
    var links = document.querySelectorAll(".nav-link[data-nav]");
    links.forEach(function (a) {
      if (a.getAttribute("data-nav") === page) a.setAttribute("aria-current", "page");
      else a.removeAttribute("aria-current");
    });
  }

  function setupMobileNav() {
    var toggle = document.querySelector(".nav-toggle");
    var nav = document.querySelector(".site-nav");
    if (!toggle || !nav) return;

    function closeNav() {
      nav.classList.remove("is-open");
      toggle.setAttribute("aria-expanded", "false");
    }

    function openNav() {
      nav.classList.add("is-open");
      toggle.setAttribute("aria-expanded", "true");
    }

    toggle.addEventListener("click", function () {
      var isOpen = nav.classList.contains("is-open");
      if (isOpen) closeNav();
      else openNav();
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeNav();
    });

    nav.addEventListener("click", function (e) {
      var target = e.target;
      if (target && target.matches && target.matches("a[href]")) closeNav();
    });

    document.addEventListener("click", function (e) {
      var t = e.target;
      if (!t) return;
      if (nav.contains(t) || toggle.contains(t)) return;
      closeNav();
    });
  }

  function ensureAuthNav() {
    var nav = document.querySelector(".site-nav");
    if (!nav) return;
    if (nav.querySelector("[data-auth-slot]")) return;

    var slot = document.createElement("div");
    slot.className = "nav-auth";
    slot.setAttribute("data-auth-slot", "true");

    var myCreate = document.createElement("a");
    myCreate.className = "nav-link nav-link--btn";
    myCreate.href = "./my-analysis.html";
    myCreate.textContent = "내 분석 만들기";

    var mySaved = document.createElement("a");
    mySaved.className = "nav-link nav-link--btn";
    mySaved.href = "./my-analyses.html";
    mySaved.textContent = "내 분석 보기";

    var userPill = document.createElement("span");
    userPill.className = "user-pill";

    var loginLink = document.createElement("a");
    loginLink.className = "nav-link nav-link--btn";
    loginLink.href = "./login.html";
    loginLink.textContent = "로그인";

    var logoutBtn = document.createElement("button");
    logoutBtn.className = "nav-link nav-link--btn";
    logoutBtn.type = "button";
    logoutBtn.textContent = "로그아웃";

    slot.appendChild(myCreate);
    slot.appendChild(mySaved);
    slot.appendChild(userPill);
    slot.appendChild(loginLink);
    slot.appendChild(logoutBtn);
    nav.appendChild(slot);

    function render() {
      var user = window.EtAuth && window.EtAuth.getUser ? window.EtAuth.getUser() : null;
      var authed = !!user;

      myCreate.style.display = authed ? "inline-flex" : "none";
      mySaved.style.display = authed ? "inline-flex" : "none";
      userPill.style.display = authed ? "inline-flex" : "none";
      loginLink.style.display = authed ? "none" : "inline-flex";
      logoutBtn.style.display = authed ? "inline-flex" : "none";
      userPill.textContent = authed ? (user.nickname || user.email || "User") : "";

      try {
        var current = window.location.pathname.split("/").pop() || "index.html";
        var query = window.location.search || "";
        var hash = window.location.hash || "";
        loginLink.href = window.EtAuth && window.EtAuth.buildLoginUrl ? window.EtAuth.buildLoginUrl(current + query + hash) : "./login.html";
      } catch (e) {
        loginLink.href = "./login.html";
      }
    }

    logoutBtn.addEventListener("click", function () {
      if (!window.EtAuth || !window.EtAuth.logout) return;
      window.EtAuth.logout().finally(function () {
        render();
        window.location.href = "./index.html";
      });
    });

    window.addEventListener("et-auth-changed", render);
    if (window.EtAuth && window.EtAuth.init) {
      window.EtAuth.init().finally(render);
    } else {
      render();
    }
  }

  window.EtApi = {
    getBase: getApiBase,
    url: buildApiUrl,
    fetchJson: fetchJson
  };

  document.addEventListener("DOMContentLoaded", function () {
    setActiveNavLink();
    setupMobileNav();
    ensureAuthNav();
  });
})();
