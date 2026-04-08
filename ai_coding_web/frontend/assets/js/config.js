(function () {
  if (!window.ET_APP_CONFIG) {
    // 로컬 개발(포트 5500)이면 백엔드 직접, 그 외(nginx 동일 출처)는 상대 경로
    // 호스트는 페이지와 맞춤: localhost ↔ 127.0.0.1 혼용 시 SameSite=Lax 쿠키가 cross-site fetch에 안 실림
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
