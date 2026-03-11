(function () {
  var STORAGE_KEY = "et_auth_v1";
  var DEFAULT_TTL_MS = 1000 * 60 * 60 * 24 * 7;

  function safeParse(json) {
    try {
      return JSON.parse(json);
    } catch (e) {
      return null;
    }
  }

  function now() {
    return Date.now();
  }

  function getSession() {
    var raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    var parsed = safeParse(raw);
    if (!parsed || !parsed.expiresAt) return null;
    if (Number(parsed.expiresAt) <= now()) {
      localStorage.removeItem(STORAGE_KEY);
      return null;
    }
    return parsed;
  }

  function setSession(user) {
    var session = {
      user: {
        email: String(user.email || ""),
        name: String(user.name || "")
      },
      createdAt: now(),
      expiresAt: now() + DEFAULT_TTL_MS
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
    return session;
  }

  function clearSession() {
    localStorage.removeItem(STORAGE_KEY);
  }

  function isAuthed() {
    return !!getSession();
  }

  function getUser() {
    var s = getSession();
    return s && s.user ? s.user : null;
  }

  function normalizeNameFromEmail(email) {
    var e = String(email || "").trim();
    if (!e) return "User";
    var at = e.indexOf("@");
    var base = at > 0 ? e.slice(0, at) : e;
    return base.slice(0, 18) || "User";
  }

  // 데모 로그인: 지금은 프론트에서만 검증합니다.
  // 이후 서버 연동 시, 이 함수를 API 호출로 교체하면 됩니다.
  function login(email, password) {
    var e = String(email || "").trim();
    var p = String(password || "");

    if (!e) return { ok: false, message: "이메일/아이디를 입력해 주세요." };
    if (p.length < 4) return { ok: false, message: "비밀번호는 4자 이상으로 입력해 주세요." };

    // 데모 계정(예시): demo@et.ai / etl1234
    if (e.toLowerCase() === "demo@et.ai" && p !== "etl1234") {
      return { ok: false, message: "데모 계정 비밀번호가 일치하지 않습니다." };
    }

    var session = setSession({ email: e, name: normalizeNameFromEmail(e) });
    return { ok: true, session: session };
  }

  function logout() {
    clearSession();
  }

  function buildLoginUrl(next) {
    var n = String(next || "").trim();
    if (!n) return "./login.html";
    return "./login.html?next=" + encodeURIComponent(n);
  }

  function requireAuth(opts) {
    var options = opts || {};
    if (isAuthed()) return true;
    if (options.redirect !== false) {
      var current = window.location.pathname.split("/").pop() || "index.html";
      var query = window.location.search || "";
      var hash = window.location.hash || "";
      window.location.href = buildLoginUrl(current + query + hash);
    }
    return false;
  }

  window.EtAuth = {
    isAuthed: isAuthed,
    getUser: getUser,
    login: login,
    logout: logout,
    requireAuth: requireAuth,
    buildLoginUrl: buildLoginUrl
  };
})();
