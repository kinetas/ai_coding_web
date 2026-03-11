(function () {
  function setActiveNavLink() {
    var page = document.body && document.body.dataset ? document.body.dataset.page : "";
    if (!page) return;
    var links = document.querySelectorAll(".nav-link[data-nav]");
    links.forEach(function (a) {
      if (a.getAttribute("data-nav") === page) {
        a.setAttribute("aria-current", "page");
      } else {
        a.removeAttribute("aria-current");
      }
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
    myCreate.setAttribute("data-auth-mycreate", "true");

    var mySaved = document.createElement("a");
    mySaved.className = "nav-link nav-link--btn";
    mySaved.href = "./my-analyses.html";
    mySaved.textContent = "내 분석 보기";
    mySaved.setAttribute("data-auth-mysaved", "true");

    var userPill = document.createElement("span");
    userPill.className = "user-pill";
    userPill.setAttribute("data-auth-user", "true");

    var loginLink = document.createElement("a");
    loginLink.className = "nav-link nav-link--btn";
    loginLink.href = "./login.html";
    loginLink.textContent = "로그인";
    loginLink.setAttribute("data-auth-login", "true");

    var logoutBtn = document.createElement("button");
    logoutBtn.className = "nav-link nav-link--btn";
    logoutBtn.type = "button";
    logoutBtn.textContent = "로그아웃";
    logoutBtn.setAttribute("data-auth-logout", "true");

    slot.appendChild(myCreate);
    slot.appendChild(mySaved);
    slot.appendChild(userPill);
    slot.appendChild(loginLink);
    slot.appendChild(logoutBtn);
    nav.appendChild(slot);

    function render() {
      var authed = window.EtAuth && window.EtAuth.isAuthed && window.EtAuth.isAuthed();
      var user = authed && window.EtAuth.getUser ? window.EtAuth.getUser() : null;

      if (authed) {
        myCreate.style.display = "inline-flex";
        mySaved.style.display = "inline-flex";
        userPill.textContent = user && user.name ? user.name : "User";
        userPill.style.display = "inline-flex";
        loginLink.style.display = "none";
        logoutBtn.style.display = "inline-flex";
      } else {
        myCreate.style.display = "none";
        mySaved.style.display = "none";
        userPill.style.display = "none";
        loginLink.style.display = "inline-flex";
        logoutBtn.style.display = "none";
      }

      // 로그인 링크에 next 붙이기
      try {
        var current = window.location.pathname.split("/").pop() || "index.html";
        var query = window.location.search || "";
        var hash = window.location.hash || "";
        loginLink.href = window.EtAuth && window.EtAuth.buildLoginUrl ? window.EtAuth.buildLoginUrl(current + query + hash) : "./login.html";
      } catch (e) {
        // ignore
      }
    }

    logoutBtn.addEventListener("click", function () {
      if (window.EtAuth && window.EtAuth.logout) window.EtAuth.logout();
      render();
      window.location.href = "./index.html";
    });

    render();
  }

  document.addEventListener("DOMContentLoaded", function () {
    setActiveNavLink();
    setupMobileNav();
    ensureAuthNav();
  });
})();
