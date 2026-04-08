(function () {
  var state = {
    user: null,
    initPromise: null
  };

  function emitChange() {
    window.dispatchEvent(new CustomEvent("et-auth-changed", { detail: { user: state.user } }));
  }

  function setUser(user) {
    state.user = user || null;
    emitChange();
    return state.user;
  }

  function init() {
    if (state.initPromise) return state.initPromise;
    state.initPromise = window.EtApi.fetchJson("/api/auth/me", { credentials: "include" })
      .then(function (data) {
        setUser(data && data.id ? data : null);
        return state.user;
      })
      .catch(function () {
        setUser(null);
        return null;
      })
      .finally(function () {
        state.initPromise = null;
      });
    return state.initPromise;
  }

  function getUser() {
    return state.user;
  }

  function isAuthed() {
    return !!state.user;
  }

  // Cookie session: no bearer token; credentials: "include" sends cookies
  function getAccessToken() {
    return Promise.resolve(null);
  }

  function login(email, password) {
    return window.EtApi.fetchJson("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: String(email || "").trim(), password: String(password || "") }),
      credentials: "include"
    }).then(function (data) {
      setUser(data && data.user ? data.user : null);
      return { user: state.user };
    });
  }

  function register(name, email, password) {
    return window.EtApi.fetchJson("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: String(email || "").trim(),
        password: String(password || ""),
        nickname: String(name || "").trim()
      }),
      credentials: "include"
    }).then(function (data) {
      setUser(data && data.user ? data.user : null);
      return { user: state.user, needsEmailConfirmation: false };
    });
  }

  function logout() {
    return window.EtApi.fetchJson("/api/auth/logout", {
      method: "POST",
      credentials: "include"
    })
      .catch(function () {})
      .then(function () {
        setUser(null);
        return { ok: true };
      });
  }

  function buildLoginUrl(next) {
    var n = String(next || "").trim();
    if (!n) return "./login.html";
    return "./login.html?next=" + encodeURIComponent(n);
  }

  function requireAuth(opts) {
    var options = opts || {};
    return init().then(function (user) {
      if (user) return true;
      if (options.redirect !== false) {
        var current = window.location.pathname.split("/").pop() || "index.html";
        var query = window.location.search || "";
        var hash = window.location.hash || "";
        window.location.href = buildLoginUrl(current + query + hash);
      }
      return false;
    });
  }

  window.EtAuth = {
    init: init,
    isAuthed: isAuthed,
    getUser: getUser,
    getAccessToken: getAccessToken,
    login: login,
    register: register,
    logout: logout,
    requireAuth: requireAuth,
    buildLoginUrl: buildLoginUrl
  };
})();
