(function () {
  var SEOUL_LAT = 37.5665;
  var SEOUL_LON = 126.9780;
  var API_URL = "https://api.open-meteo.com/v1/forecast"
    + "?latitude=" + SEOUL_LAT
    + "&longitude=" + SEOUL_LON
    + "&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max"
    + "&timezone=Asia%2FSeoul"
    + "&forecast_days=7";

  var WMO_ICON = {
    0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️",
    45: "🌫️", 48: "🌫️",
    51: "🌦️", 53: "🌦️", 55: "🌧️",
    61: "🌧️", 63: "🌧️", 65: "🌧️",
    71: "❄️", 73: "❄️", 75: "❄️",
    80: "🌦️", 81: "🌧️", 82: "⛈️",
    95: "⛈️", 96: "⛈️", 99: "⛈️"
  };

  var WMO_DESC = {
    0: "맑음", 1: "대체로 맑음", 2: "구름 조금", 3: "흐림",
    45: "안개", 48: "안개",
    51: "이슬비", 53: "이슬비", 55: "이슬비",
    61: "비", 63: "비", 65: "강한 비",
    71: "눈", 73: "눈", 75: "강한 눈",
    80: "소나기", 81: "소나기", 82: "강한 소나기",
    95: "뇌우", 96: "뇌우", 99: "뇌우"
  };

  function wmoIcon(code) {
    return WMO_ICON[code] || "🌡️";
  }

  function wmoDesc(code) {
    return WMO_DESC[code] || "기상 정보 없음";
  }

  function formatDay(dateStr, idx) {
    var d = new Date(dateStr + "T00:00:00");
    var days = ["일", "월", "화", "수", "목", "금", "토"];
    var month = d.getMonth() + 1;
    var day = d.getDate();
    var dow = days[d.getDay()];
    if (idx === 0) return "오늘 (" + dow + ")";
    if (idx === 1) return "내일 (" + dow + ")";
    return month + "/" + day + " (" + dow + ")";
  }

  function renderForecast(daily) {
    var grid = document.getElementById("forecast-grid");
    if (!grid) return;

    var html = daily.time.map(function (dateStr, i) {
      var code = daily.weathercode[i];
      var tmax = Math.round(daily.temperature_2m_max[i]);
      var tmin = Math.round(daily.temperature_2m_min[i]);
      var rain = daily.precipitation_sum[i];
      var wind = daily.wind_speed_10m_max[i];
      var isToday = i === 0;
      return [
        '<div class="weather-card' + (isToday ? " weather-card--today" : "") + '">',
        '  <p class="weather-card__date">' + formatDay(dateStr, i) + "</p>",
        '  <p class="weather-card__icon">' + wmoIcon(code) + "</p>",
        '  <p class="weather-card__temp">' + tmax + "° <span>/ " + tmin + "°</span></p>",
        '  <p class="weather-card__rain">💧 ' + rain.toFixed(1) + " mm</p>",
        '  <p class="weather-card__wind">💨 ' + wind.toFixed(1) + " km/h</p>",
        "</div>"
      ].join("\n");
    }).join("\n");

    grid.innerHTML = html;
  }

  function buildAdvisory(daily) {
    var items = [];

    for (var i = 0; i < daily.time.length; i++) {
      var dateStr = formatDay(daily.time[i], i);
      var rain = daily.precipitation_sum[i];
      var tmax = daily.temperature_2m_max[i];
      var tmin = daily.temperature_2m_min[i];
      var wind = daily.wind_speed_10m_max[i];

      if (rain >= 30) {
        items.push({ level: "danger", icon: "⛈️", title: dateStr + " — 강수 주의 (" + rain.toFixed(0) + "mm)", text: "강수량이 많습니다. 수확·출하 작업을 피하고 침수 피해에 대비하세요." });
      } else if (rain >= 10) {
        items.push({ level: "warn", icon: "🌧️", title: dateStr + " — 비 예보 (" + rain.toFixed(0) + "mm)", text: "엽채류 수확 후 건조 보관에 유의하세요." });
      }

      if (tmax >= 35) {
        items.push({ level: "danger", icon: "🌡️", title: dateStr + " — 폭염 주의 (" + tmax + "°C)", text: "엽채류 시들음 위험. 오전 일찍 작업하고 관수를 늘리세요." });
      } else if (tmax >= 30) {
        items.push({ level: "warn", icon: "☀️", title: dateStr + " — 더위 예보 (" + tmax + "°C)", text: "고온 피해에 취약한 상추·시금치 등 엽채류 관리에 유의하세요." });
      }

      if (tmin <= 2) {
        items.push({ level: "danger", icon: "🧊", title: dateStr + " — 냉해 위험 (" + tmin + "°C)", text: "서리·결빙 가능성. 무·배추 등 월동 작물 피복재 점검이 필요합니다." });
      } else if (tmin <= 5) {
        items.push({ level: "warn", icon: "❄️", title: dateStr + " — 저온 주의 (" + tmin + "°C)", text: "온도에 민감한 모종 및 고추·토마토 야간 보온에 신경 쓰세요." });
      }

      if (wind >= 50) {
        items.push({ level: "danger", icon: "🌬️", title: dateStr + " — 강풍 주의 (" + wind.toFixed(0) + " km/h)", text: "시설하우스 고정 상태를 점검하고 지지대를 보강하세요." });
      } else if (wind >= 30) {
        items.push({ level: "warn", icon: "💨", title: dateStr + " — 바람 예보 (" + wind.toFixed(0) + " km/h)", text: "방풍망 점검 및 키 큰 작물의 쓰러짐에 주의하세요." });
      }
    }

    if (items.length === 0) {
      items.push({ level: "info", icon: "✅", title: "특이 기상 없음", text: "향후 7일간 농작업에 큰 지장을 주는 기상 특보가 없습니다." });
    }

    return items;
  }

  function renderAdvisory(daily) {
    var list = document.getElementById("advisory-list");
    if (!list) return;
    var advisories = buildAdvisory(daily);
    var html = advisories.map(function (a) {
      return [
        '<div class="advisory-item advisory-item--' + a.level + '">',
        '  <span class="advisory-item__icon">' + a.icon + "</span>",
        '  <p class="advisory-item__text"><strong>' + a.title + "</strong>" + a.text + "</p>",
        "</div>"
      ].join("\n");
    }).join("\n");
    list.innerHTML = html;
  }

  function loadWeather() {
    fetch(API_URL)
      .then(function (res) {
        if (!res.ok) throw new Error("날씨 API 오류: " + res.status);
        return res.json();
      })
      .then(function (data) {
        if (!data || !data.daily) throw new Error("날씨 데이터 형식이 올바르지 않습니다.");
        renderForecast(data.daily);
        renderAdvisory(data.daily);

        var updated = document.getElementById("weather-updated");
        if (updated) {
          var now = new Date();
          updated.textContent = "기준: 서울(37.57°N, 126.98°E) · " + now.toLocaleDateString("ko-KR") + " " + now.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" }) + " 조회 · Open-Meteo";
        }
      })
      .catch(function (err) {
        var grid = document.getElementById("forecast-grid");
        var adv = document.getElementById("advisory-list");
        var msg = '<p class="weather-error">날씨 정보를 불러오지 못했습니다.<br>' + String(err.message || err) + "</p>";
        if (grid) grid.innerHTML = msg;
        if (adv) adv.innerHTML = "";
      });
  }

  document.addEventListener("DOMContentLoaded", loadWeather);
})();
