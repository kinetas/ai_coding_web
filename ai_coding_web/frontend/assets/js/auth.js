(function () {
  var state = {
    user: null,
    initPromise: null,
    client: null,
    listenerAttached: false,
    refreshTimer: null
  };

  function emitChange() {
    window.dispatchEvent(new CustomEvent("et-auth-changed", { detail: { user: state.user } }));
  }

  function setUser(user) {
    state.user = user || null;
    emitChange();
    return state.user;
  }

  function getConfig() {
    var c = window.ET_APP_CONFIG || {};
    return {
      url: String(c.supabaseUrl || "").trim(),
      key: String(c.supabaseAnonKey || "").trim()
    };
  }

  function getSupabase() {
    if (state.client) return state.client;
    var cfg = getConfig();
    if (!cfg.url || !cfg.key) {
      throw new Error("Supabase가 설정되지 않았습니다. frontend/assets/js/config.js에 supabaseUrl과 supabaseAnonKey를 입력하세요.");
    }
    if (!window.supabase || typeof window.supabase.createClient !== "function") {
      throw new Error("Supabase 클라이언트를 불러오지 못했습니다. supabase-js 스크립트가 auth.js보다 먼저 로드되는지 확인하세요.");
    }
    state.client = window.supabase.createClient(cfg.url, cfg.key, {
      auth: {
        persistSession: true,
        autoRefreshToken: false,
        detectSessionInUrl: true
      }
    });
    return state.client;
  }

  function mapUser(u) {
    if (!u) return null;
    var meta = u.user_metadata || {};
    var nick = meta.full_name || meta.name || meta.nickname || "";
    if (!nick && u.email) nick = u.email.split("@")[0];
    return {
      id: u.id,
      email: u.email,
      nickname: nick
    };
  }

  function mapSessionUser(session) {
    if (!session || !session.user) return null;
    return mapUser(session.user);
  }

  function normalizeSessionPayload(data) {
    if (!data) return null;
    if (data.access_token && data.refresh_token) return data;
    if (data.session && data.session.access_token && data.session.refresh_token) {
      var s = data.session;
      return {
        access_token: s.access_token,
        refresh_token: s.refresh_token,
        expires_in: s.expires_in,
        expires_at: s.expires_at,
        token_type: s.token_type,
        user: data.user || s.user
      };
    }
    return null;
  }

  function applySession(raw) {
    var payload = normalizeSessionPayload(raw);
    if (!payload) {
      return Promise.resolve(null);
    }
    return getSupabase()
      .auth.setSession({
        access_token: payload.access_token,
        refresh_token: payload.refresh_token
      })
      .then(function (result) {
        if (result.error) throw toError(result.error);
        var u = result.data && result.data.session && result.data.session.user;
        setUser(mapUser(u));
        scheduleRefresh();
        return state.user;
      });
  }

  function scheduleRefresh() {
    if (state.refreshTimer) {
      clearInterval(state.refreshTimer);
      state.refreshTimer = null;
    }
    state.refreshTimer = window.setInterval(function () {
      refreshSession().catch(function () {});
    }, 45 * 60 * 1000);
  }

  function refreshSession() {
    return getSupabase()
      .auth.getSession()
      .then(function (r) {
        var s = r.data && r.data.session;
        if (!s || !s.refresh_token) return null;
        return window.EtApi.fetchJson("/api/auth/supabase/refresh", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: s.refresh_token })
        }).then(function (data) {
          return applySession(data);
        });
      });
  }

  function attachAuthListener() {
    if (state.listenerAttached) return;
    var client = getSupabase();
    state.listenerAttached = true;
    client.auth.onAuthStateChange(function (_event, session) {
      setUser(mapSessionUser(session));
    });
  }

  function toError(err) {
    if (!err) return new Error("요청에 실패했습니다.");
    var msg = err.message || String(err);
    var lower = msg.toLowerCase();
    if (lower.indexOf("invalid login credentials") !== -1 || lower.indexOf("invalid email or password") !== -1) {
      return new Error("이메일 또는 비밀번호가 올바르지 않습니다.");
    }
    if (msg.indexOf("User already registered") !== -1 || lower.indexOf("already been registered") !== -1) {
      return new Error("이미 가입된 이메일입니다.");
    }
    if (lower.indexOf("email not confirmed") !== -1) {
      return new Error("이메일 인증을 완료한 뒤 다시 로그인해 주세요.");
    }
    return new Error(msg);
  }

  function init() {
    if (state.initPromise) return state.initPromise;
    try {
      attachAuthListener();
    } catch (e) {
      return Promise.reject(e);
    }
    state.initPromise = getSupabase()
      .auth.getSession()
      .then(function (result) {
        var session = result.data && result.data.session;
        setUser(mapSessionUser(session));
        if (session && session.refresh_token) {
          scheduleRefresh();
        }
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

  function login(email, password) {
    return window.EtApi.fetchJson("/api/auth/supabase/sign-in", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: String(email || "").trim(),
        password: String(password || "")
      })
    }).then(function (data) {
      return applySession(data).then(function () {
        return { user: state.user };
      });
    });
  }

  function register(name, email, password) {
    return window.EtApi.fetchJson("/api/auth/supabase/sign-up", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: String(email || "").trim(),
        password: String(password || ""),
        nickname: String(name || "").trim()
      })
    }).then(function (data) {
      var norm = normalizeSessionPayload(data);
      if (norm) {
        return applySession(data).then(function () {
          return { user: state.user, needsEmailConfirmation: false };
        });
      }
      setUser(null);
      return {
        user: null,
        needsEmailConfirmation: true
      };
    });
  }

  function getSupabaseClient() {
    return getSupabase();
  }

  function getAccessToken() {
    return getSupabase()
      .auth.getSession()
      .then(function (result) {
        var s = result.data && result.data.session;
        return s && s.access_token ? s.access_token : null;
      });
  }

  function updateUserProfile(opts) {
    var o = opts || {};
    var body = {};
    if (o.email != null && String(o.email).trim() !== "") {
      body.email = String(o.email).trim();
    }
    if (o.nickname != null && String(o.nickname).trim() !== "") {
      body.nickname = String(o.nickname).trim();
    }
    if (!body.email && !body.nickname) {
      return Promise.resolve({ data: { user: state.user } });
    }
    return window.EtApi.fetchJson("/api/auth/supabase/user", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    }).then(function (data) {
      var u = (data && data.user) || data;
      if (u && u.id) setUser(mapUser(u));
      return { data: { user: state.user } };
    });
  }

  function logout() {
    return getAccessToken().then(function (token) {
      if (!token) {
        setUser(null);
        return getSupabase().auth.signOut({ scope: "local" }).then(function () {
          return { ok: true };
        });
      }
      return window.EtApi.fetchJson("/api/auth/supabase/sign-out", { method: "POST" })
        .catch(function () {
          return { ok: false };
        })
        .then(function () {
          return getSupabase().auth.signOut({ scope: "local" });
        })
        .then(function () {
          if (state.refreshTimer) {
            clearInterval(state.refreshTimer);
            state.refreshTimer = null;
          }
          setUser(null);
          return { ok: true };
        });
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
    getSupabaseClient: getSupabaseClient,
    getAccessToken: getAccessToken,
    /** 액세스 토큰 만료 시 탈퇴·보호 API용으로 refresh 후 세션 갱신 */
    refreshSession: refreshSession,
    updateUserProfile: updateUserProfile,
    login: login,
    register: register,
    logout: logout,
    requireAuth: requireAuth,
    buildLoginUrl: buildLoginUrl
  };
})();
