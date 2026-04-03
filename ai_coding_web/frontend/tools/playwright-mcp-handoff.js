/**
 * Playwright MCP — Supabase 대시보드 안내 (로그인 대기 후 자동 재개)
 *
 * 동작:
 * 1) 대시보드 URL로 이동 → 로그인이 필요하면 sign-in 으로 리다이렉트될 수 있음
 * 2) 로그인 페이지면 상단에 “로그인 완료 시 자동 진행” 배너 표시
 * 3) URL 에서 /sign-in, /login 이 사라질 때까지 대기 (최대 10분) — 직접 로그인하면 이어짐
 * 4) 로그인 후 프로젝트 목록 또는 API 설정으로 다시 이동
 * 5) 기존처럼 우측 하단에 할 일 안내 패널 표시
 *
 * 사용: MCP `browser_run_code` 의 `code` 에 [SUPABASE_TOUR_START] ~ [SUPABASE_TOUR_END] 만 복사
 */

/*
[SUPABASE_TOUR_START]

async (page) => {
  var projectRef = "";
  var targetUrl = projectRef
    ? "https://supabase.com/dashboard/project/" + projectRef + "/settings/api"
    : "https://supabase.com/dashboard/projects";

  await page.goto(targetUrl, { waitUntil: "domcontentloaded", timeout: 120000 });

  var u0 = page.url();
  if (u0.indexOf("/sign-in") >= 0 || u0.toLowerCase().indexOf("/login") >= 0) {
    await page.evaluate(function () {
      var id = "et-supabase-wait-login";
      if (document.getElementById(id)) return;
      var el = document.createElement("div");
      el.id = id;
      el.setAttribute("role", "status");
      el.style.cssText =
        "position:fixed;z-index:2147483646;left:0;right:0;top:0;padding:14px 20px;background:#152238;border-bottom:2px solid #6ae4ff;color:#eaf0ff;font:14px/1.45 system-ui,Segoe UI,sans-serif;text-align:center;box-shadow:0 8px 24px rgba(0,0,0,.4)";
      el.textContent =
        "Et · Supabase 로그인을 마치면 이 탭에서 자동으로 다음 단계(키 복사 안내)가 이어집니다. 소셜 로그인 중에는 잠시 다른 화면으로 갔다가 돌아올 수 있습니다.";
      if (document.body) document.body.insertBefore(el, document.body.firstChild);
    });
  }

  await page.waitForFunction(
    function () {
      var h = window.location.href;
      if (h.indexOf("supabase.com") === -1) return false;
      var low = h.toLowerCase();
      if (low.indexOf("/sign-in") >= 0) return false;
      if (low.indexOf("/login") >= 0 && low.indexOf("supabase.com") >= 0) return false;
      return true;
    },
    { timeout: 600000 }
  );

  await page.evaluate(function () {
    var w = document.getElementById("et-supabase-wait-login");
    if (w) w.remove();
  });

  if (projectRef) {
    await page.goto(
      "https://supabase.com/dashboard/project/" + projectRef + "/settings/api",
      { waitUntil: "domcontentloaded", timeout: 120000 }
    );
  } else {
    await page.goto("https://supabase.com/dashboard/projects", {
      waitUntil: "domcontentloaded",
      timeout: 120000
    });
  }

  await page.evaluate(function () {
    var id = "et-supabase-tour-overlay";
    if (document.getElementById(id)) return;
    var wrap = document.createElement("div");
    wrap.id = id;
    wrap.style.cssText =
      "position:fixed;z-index:2147483647;right:16px;bottom:16px;max-width:400px;max-height:85vh;overflow:auto;padding:18px;background:#0c1224;border:2px solid #6ae4ff;border-radius:14px;color:#eaf0ff;font:14px/1.55 system-ui,Segoe UI,sans-serif;box-shadow:0 16px 48px rgba(0,0,0,.55)";
    var h = document.createElement("h2");
    h.style.cssText = "margin:0 0 10px;font-size:17px;color:#6ae4ff";
    h.textContent = "Et · Supabase에서 할 일";
    var ol = document.createElement("ol");
    ol.style.cssText = "margin:0;padding-left:20px";
    [
      "프로젝트를 선택합니다 (목록 화면인 경우).",
      "Project Settings → API 로 이동합니다.",
      "Project URL 과 anon public 키를 복사합니다.",
      "로컬의 frontend/assets/js/config.js 에 supabaseUrl, supabaseAnonKey 로 붙여 넣고 저장합니다.",
      "Authentication → Providers 에서 Email 이 켜져 있는지 확인합니다."
    ].forEach(function (t) {
      var li = document.createElement("li");
      li.textContent = t;
      ol.appendChild(li);
    });
    var p = document.createElement("p");
    p.style.cssText = "margin:12px 0 0;font-size:12px;color:rgba(234,240,255,.65)";
    p.textContent = "이 박스는 Playwright MCP가 대시보드 위에 덧씌운 안내입니다.";
    var btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = "안내 닫기";
    btn.style.cssText =
      "margin-top:14px;width:100%;padding:11px;border-radius:10px;border:1px solid #6ae4ff;background:#152238;color:#eaf0ff;cursor:pointer;font-weight:600";
    btn.addEventListener("click", function () {
      wrap.remove();
    });
    wrap.appendChild(h);
    wrap.appendChild(ol);
    wrap.appendChild(p);
    wrap.appendChild(btn);
    document.body.appendChild(wrap);
  });

  return { ok: true, url: page.url() };
}

[SUPABASE_TOUR_END]
*/
