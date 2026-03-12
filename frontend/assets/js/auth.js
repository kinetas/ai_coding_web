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

  function getApi() {
    if (window.EtApi && window.EtApi.fetchJson) return window.EtApi;
    throw new Error("EtApi 모듈을 먼저 로드해야 합니다.");
  }

  function init() {
    if (state.initPromise) return state.initPromise;
    state.initPromise = getApi().fetchJson("/api/auth/me")
      .then(function (user) {
        setUser(user);
        return user;
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

  function login(email, password) {
    return getApi().fetchJson("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: String(email || "").trim(), password: String(password || "") })
    }).then(function (json) {
      setUser(json && json.user ? json.user : null);
      return json;
    });
  }

  function register(name, email, password) {
    return getApi().fetchJson("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: String(name || "").trim(),
        email: String(email || "").trim(),
        password: String(password || "")
      })
    }).then(function (json) {
      setUser(json && json.user ? json.user : null);
      return json;
    });
  }

  function logout() {
    return getApi().fetchJson("/api/auth/logout", { method: "POST" })
      .catch(function () { return { ok: true }; })
      .then(function (json) {
        setUser(null);
        return json;
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
    login: login,
    register: register,
    logout: logout,
    requireAuth: requireAuth,
    buildLoginUrl: buildLoginUrl
  };
})();
