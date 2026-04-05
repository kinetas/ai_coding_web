(function () {
  if (!window.ET_APP_CONFIG) {
    // 로컬 개발(포트 5500)이면 백엔드 직접, 그 외(nginx)는 상대 경로
    var isDev = window.location.port === "5500";
    window.ET_APP_CONFIG = {
      apiBase: isDev ? "http://127.0.0.1:8000" : ""
    };
  }
})();
