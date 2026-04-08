/**
 * Playwright MCP — Supabase dashboard helper (wait for login, then resume)
 *
 * Flow:
 * 1) Open dashboard URL → may redirect to sign-in
 * 2) On login page, show a top banner: automation continues after login
 * 3) Wait until /sign-in and /login disappear from URL (up to 10 min)
 * 4) Navigate back to project list or API settings
 * 5) Show the task overlay bottom-right as before
 *
 * Copy only [SUPABASE_TOUR_START] ~ [SUPABASE_TOUR_END] into MCP browser_run_code `code`.
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
        "Et · After you finish Supabase sign-in, this tab will continue automatically (key copy steps). During social login you may leave and return.";
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
    h.textContent = "Et · Next steps in Supabase";
    var ol = document.createElement("ol");
    ol.style.cssText = "margin:0;padding-left:20px";
    [
      "Pick a project (if you see the list).",
      "Go to Project Settings → API.",
      "Copy Project URL and anon public key.",
      "Paste into local frontend/assets/js/config.js as supabaseUrl and supabaseAnonKey, then save.",
      "Under Authentication → Providers, ensure Email is enabled."
    ].forEach(function (t) {
      var li = document.createElement("li");
      li.textContent = t;
      ol.appendChild(li);
    });
    var p = document.createElement("p");
    p.style.cssText = "margin:12px 0 0;font-size:12px;color:rgba(234,240,255,.65)";
    p.textContent = "This box is injected by Playwright MCP over the dashboard.";
    var btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = "Dismiss";
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
