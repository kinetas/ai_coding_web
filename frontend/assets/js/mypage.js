(function () {
  function $(sel) {
    return document.querySelector(sel);
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
    if (!window.EtAuth || !window.EtAuth.init) {
      return;
    }

    var form = $("#profile-form");
    var nick = $("#field-nickname");
    var email = $("#field-email");
    var err = $("#profile-error");
    var ok = $("#profile-success");
    var delErr = $("#delete-error");
    var delBtn = $("#delete-account-btn");
    var delInput = $("#delete-confirm");

    window.EtAuth.requireAuth({ redirect: true }).then(function (allowed) {
      if (!allowed) return;

      window.EtAuth.init().then(function () {
        return window.EtAuth.getSupabaseClient().auth.getUser();
      }).then(function (res) {
        var u = res.data && res.data.user;
        if (!u) return;
        if (nick) nick.value = (u.user_metadata && (u.user_metadata.nickname || u.user_metadata.full_name)) || "";
        if (email) email.value = u.email || "";
      });

      if (form) {
        form.addEventListener("submit", function (e) {
          e.preventDefault();
          setAlert(err, "");
          setAlert(ok, "");

          var fd = new FormData(form);
          var nickname = String(fd.get("nickname") || "").trim();
          var em = String(fd.get("email") || "").trim();

          if (!em) {
            setAlert(err, "이메일을 입력해 주세요.");
            return;
          }

          window.EtAuth
            .updateUserProfile({ email: em, nickname: nickname || undefined })
            .then(function () {
              setAlert(ok, "저장했습니다. 이메일을 바꾼 경우 확인 메일을 확인해 주세요.");
            })
            .catch(function (error) {
              setAlert(err, error && error.message ? error.message : "저장에 실패했습니다.");
            });
        });
      }

      if (delBtn) {
        delBtn.addEventListener("click", function () {
          setAlert(delErr, "");
          if (!delInput || String(delInput.value || "").trim() !== "탈퇴") {
            setAlert(delErr, "확인 문구를 정확히 입력해 주세요.");
            return;
          }
          if (!window.confirm("정말 탈퇴하시겠습니까? 이 작업은 되돌릴 수 없습니다.")) {
            return;
          }

          Promise.resolve()
            .then(function () {
              if (window.EtAuth.refreshSession) {
                return window.EtAuth.refreshSession();
              }
            })
            .catch(function () {
              throw new Error("세션을 갱신하지 못했습니다. 다시 로그인한 뒤 시도해 주세요.");
            })
            .then(function () {
              return window.EtAuth.getAccessToken();
            })
            .then(function (token) {
              if (!token) {
                throw new Error("로그인 세션이 없습니다. 다시 로그인해 주세요.");
              }
              return window.EtApi.fetchJson("/api/auth/account", { method: "DELETE" });
            })
            .then(function () {
              return window.EtAuth.logout();
            })
            .then(function () {
              window.location.href = "./login.html";
            })
            .catch(function (error) {
              setAlert(delErr, error && error.message ? error.message : "탈퇴 처리에 실패했습니다.");
            });
        });
      }
    });
  });
})();
