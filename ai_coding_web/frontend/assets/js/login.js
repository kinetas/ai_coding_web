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
    // Only same-site relative paths (open redirect guard)
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
      setAlert(err, "Could not load auth module (check auth.js).");
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
              setAlert(ok, "Signed in. Redirecting...");
              window.setTimeout(function () {
                safeRedirect(next || "analysis-1.html");
              }, 350);
            })
            .catch(function (error) {
              setAlert(err, error && error.message ? error.message : "Sign-in failed.");
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
                setAlert(regOk, "Confirmation email sent. Verify via the link, then sign in.");
                return;
              }
              setAlert(regOk, "Account created. Redirecting...");
              window.setTimeout(function () {
                safeRedirect(next || "analysis-1.html");
              }, 350);
            })
            .catch(function (error) {
              setAlert(regErr, error && error.message ? error.message : "Registration failed.");
            });
        });
      }
    });
  });
})();
