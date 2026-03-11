(function () {
  function $(sel) {
    return document.querySelector(sel);
  }

  function getNext() {
    try {
      var params = new URLSearchParams(window.location.search || "");
      var n = params.get("next");
      return n ? String(n) : "";
    } catch (e) {
      return "";
    }
  }

  function safeRedirect(target) {
    var t = String(target || "").trim();
    if (!t) {
      window.location.href = "./index.html";
      return;
    }
    // 같은 사이트 내 상대경로만 허용(오픈 리다이렉트 방지)
    if (/^https?:\/\//i.test(t) || t.indexOf("//") === 0) {
      window.location.href = "./index.html";
      return;
    }
    if (t[0] === "/") t = t.slice(1);
    window.location.href = "./" + t;
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
    var form = $("#login-form");
    var err = $("#login-error");
    var ok = $("#login-success");

    if (!window.EtAuth || !window.EtAuth.login) {
      setAlert(err, "로그인 모듈을 불러오지 못했습니다. (auth.js 확인)");
      return;
    }

    var next = getNext();

    // 이미 로그인 상태면 바로 이동
    if (window.EtAuth.isAuthed && window.EtAuth.isAuthed()) {
      safeRedirect(next || "analysis-1.html");
      return;
    }

    if (!form) return;

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      setAlert(err, "");
      setAlert(ok, "");

      var fd = new FormData(form);
      var email = String(fd.get("email") || "").trim();
      var password = String(fd.get("password") || "");

      var res = window.EtAuth.login(email, password);
      if (!res || !res.ok) {
        setAlert(err, (res && res.message) || "로그인에 실패했습니다.");
        return;
      }

      setAlert(ok, "로그인 성공! 이동 중...");
      window.setTimeout(function () {
        safeRedirect(next || "analysis-1.html");
      }, 350);
    });
  });
})();
