(function () {
  if (!window.ET_APP_CONFIG) {
    // Dev on port 5500: point API to :8000; otherwise same-origin relative path.
    // Keep host aligned with the page: localhost vs 127.0.0.1 affects SameSite=Lax cookies on fetch.
    var isDev = window.location.port === "5500";
    var apiBase = "";
    if (isDev) {
      apiBase = "http://" + window.location.hostname + ":8000";
    }
    window.ET_APP_CONFIG = {
      apiBase: apiBase
    };
  }
})();
