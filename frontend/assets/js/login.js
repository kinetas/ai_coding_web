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
    var registerForm = $("#register-form");
    var err = $("#login-error");
    var ok = $("#login-success");
    var regErr = $("#register-error");
    var regOk = $("#register-success");

    if (!window.EtAuth || !window.EtAuth.login || !window.EtAuth.register) {
      setAlert(err, "로그인 모듈을 불러오지 못했습니다. (auth.js 확인)");
      return;
    }

    var next = getNext();

    window.EtAuth.init().then(function (user) {
      if (user) {
        safeRedirect(next || "analysis-1.html");
        return;
      }

      if (form) {
        form.addEventListener("submit", function (e) {
          e.preventDefault();
          setAlert(err, "");
          setAlert(ok, "");

          var fd = new FormData(form);
          var email = String(fd.get("email") || "").trim();
          var password = String(fd.get("password") || "");

          window.EtAuth.login(email, password)
            .then(function () {
              setAlert(ok, "로그인 성공! 이동 중...");
              window.setTimeout(function () {
                safeRedirect(next || "analysis-1.html");
              }, 350);
            })
            .catch(function (error) {
              setAlert(err, error && error.message ? error.message : "로그인에 실패했습니다.");
            });
        });
      }

      if (registerForm) {
        registerForm.addEventListener("submit", function (e) {
          e.preventDefault();
          setAlert(regErr, "");
          setAlert(regOk, "");

          var fd = new FormData(registerForm);
          var name = String(fd.get("name") || "").trim();
          var email = String(fd.get("email") || "").trim();
          var password = String(fd.get("password") || "");

          window.EtAuth.register(name, email, password)
            .then(function (res) {
              if (res && res.needsEmailConfirmation) {
                setAlert(regOk, "가입 확인 메일을 발송했습니다. 메일의 링크로 인증한 뒤 로그인해 주세요.");
                return;
              }
              setAlert(regOk, "회원가입 성공! 이동 중...");
              window.setTimeout(function () {
                safeRedirect(next || "analysis-1.html");
              }, 350);
            })
            .catch(function (error) {
              setAlert(regErr, error && error.message ? error.message : "회원가입에 실패했습니다.");
            });
        });
      }
    });
  });
})();
