(function () {
  function getCssVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  function dprScale(canvas) {
    var ctx = canvas.getContext("2d");
    var dpr = window.devicePixelRatio || 1;
    var rect = canvas.getBoundingClientRect();
    var w = Math.max(1, Math.floor(rect.width));
    var h = Math.max(1, Math.floor(rect.height));

    if (canvas.width !== Math.floor(w * dpr) || canvas.height !== Math.floor(h * dpr)) {
      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    } else {
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    return { ctx: ctx, w: w, h: h };
  }

  function clear(ctx, w, h) {
    ctx.clearRect(0, 0, w, h);
  }

  function hexToRgba(hex, a) {
    var h = String(hex || "").replace("#", "");
    if (h.length === 3) h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
    var r = parseInt(h.slice(0, 2), 16);
    var g = parseInt(h.slice(2, 4), 16);
    var b = parseInt(h.slice(4, 6), 16);
    return "rgba(" + r + "," + g + "," + b + "," + a + ")";
  }

  function drawGrid(ctx, x, y, w, h, step, color) {
    ctx.save();
    ctx.strokeStyle = color;
    ctx.lineWidth = 1;
    ctx.globalAlpha = 1;
    for (var i = 0; i <= w; i += step) {
      ctx.beginPath();
      ctx.moveTo(x + i, y);
      ctx.lineTo(x + i, y + h);
      ctx.stroke();
    }
    for (var j = 0; j <= h; j += step) {
      ctx.beginPath();
      ctx.moveTo(x, y + j);
      ctx.lineTo(x + w, y + j);
      ctx.stroke();
    }
    ctx.restore();
  }

  function niceMax(v) {
    if (v <= 0) return 1;
    var pow = Math.pow(10, Math.floor(Math.log10(v)));
    var n = v / pow;
    var nice = n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10;
    return nice * pow;
  }

  function fmtShort(v) {
    // 차트 값 축약: 10,000 이상 → K
    var n = Math.round(v);
    if (n >= 10000) return (n / 1000).toFixed(1).replace(/\.0$/, "") + "K";
    return n.toLocaleString ? n.toLocaleString() : String(n);
  }

  function lineChart(canvas, series, opts) {
    if (!canvas) return;
    var o = opts || {};
    var accent  = o.accent  || getCssVar("--accent") || "#00D4FF";
    var grid    = o.grid    || "rgba(234,240,255,.08)";
    var textCol = o.text    || "rgba(234,240,255,.70)";
    var labels      = Array.isArray(o.labels) ? o.labels : null;      // x축 레이블
    var showValues  = o.showValues !== false;                          // 점 위 값 표시(기본 true)

    // 레이블 밀도 제어: 픽셀당 최소 간격
    var MIN_LABEL_PX = 42;

    // 마진: 값 표시 → 위 여백↑, 레이블 → 아래 여백↑
    var m = {
      t: showValues ? 30 : 18,
      r: 18,
      b: labels     ? 46 : 26,
      l: 50
    };

    var scaled = dprScale(canvas);
    var ctx = scaled.ctx, W = scaled.w, H = scaled.h;
    clear(ctx, W, H);

    var innerW = Math.max(1, W - m.l - m.r);
    var innerH = Math.max(1, H - m.t - m.b);
    var x0 = m.l, y0 = m.t;

    var maxV = 0;
    for (var i = 0; i < series.length; i++) maxV = Math.max(maxV, Number(series[i] || 0));
    var yMax = niceMax(maxV);

    // background grid
    drawGrid(ctx, x0, y0, innerW, innerH, 28, grid);

    // Y축 레이블
    ctx.save();
    ctx.fillStyle = textCol;
    ctx.font = "11px ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial";
    ctx.textAlign = "right";
    ctx.textBaseline = "middle";
    var ticks = 4;
    for (var t = 0; t <= ticks; t++) {
      var v = (yMax * (ticks - t)) / ticks;
      var yy = y0 + (innerH * t) / ticks;
      ctx.fillText(fmtShort(v), x0 - 6, yy);
    }
    ctx.restore();

    var n = Math.max(2, series.length);

    // 선
    ctx.save();
    ctx.lineWidth = 2.25;
    ctx.strokeStyle = accent;
    ctx.shadowColor = hexToRgba(accent, 0.25);
    ctx.shadowBlur = 18;
    ctx.beginPath();
    for (var k = 0; k < series.length; k++) {
      var x = x0 + (innerW * k) / (n - 1);
      var v2 = Number(series[k] || 0);
      var y = y0 + innerH - (innerH * v2) / Math.max(1, yMax);
      if (k === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
    ctx.restore();

    // 포인트 + 값 표시
    var stepPx = innerW / Math.max(1, n - 1);
    var showEvery = Math.max(1, Math.ceil(MIN_LABEL_PX / Math.max(1, stepPx)));

    ctx.save();
    for (var p = 0; p < series.length; p++) {
      var xp = x0 + (innerW * p) / (n - 1);
      var vp = Number(series[p] || 0);
      var yp = y0 + innerH - (innerH * vp) / Math.max(1, yMax);

      // 점
      ctx.beginPath();
      ctx.fillStyle = hexToRgba(accent, 0.92);
      ctx.arc(xp, yp, 3.5, 0, Math.PI * 2);
      ctx.fill();

      // 점 위 값
      if (showValues && p % showEvery === 0) {
        ctx.fillStyle = textCol;
        ctx.font = "10px ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial";
        ctx.textAlign = "center";
        ctx.textBaseline = "bottom";
        ctx.fillText(fmtShort(vp), xp, yp - 5);
      }
    }
    ctx.restore();

    // X축 레이블 (회전 -30°)
    if (labels) {
      ctx.save();
      ctx.fillStyle = textCol;
      ctx.font = "10px ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial";
      ctx.textAlign = "right";
      ctx.textBaseline = "top";
      for (var lx = 0; lx < labels.length && lx < series.length; lx++) {
        if (lx % showEvery !== 0) continue;
        var xl = x0 + (innerW * lx) / (n - 1);
        var yl = y0 + innerH + 6;
        ctx.save();
        ctx.translate(xl, yl);
        ctx.rotate(-Math.PI / 6);   // -30°
        ctx.fillText(labels[lx], 0, 0);
        ctx.restore();
      }
      ctx.restore();
    }
  }

  // ── 쌀 주간 시계열 전용 (날짜 x축 + 호버 툴팁) ───────────────────────────
  function riceLineChart(canvas, series, dateLabels, opts) {
    if (!canvas || !series || series.length < 2) return;

    // 이전 이벤트 정리
    if (canvas._riceCleanup) { canvas._riceCleanup(); canvas._riceCleanup = null; }

    var o = opts || {};
    var accent  = o.accent || "#9AF7D0";
    var GRID    = "rgba(234,240,255,.07)";
    var TCOL    = "rgba(234,240,255,.68)";
    var MT = 32, MR = 20, MB = 76, ML = 60;  // 마진 (아래 76px: 회전 레이블)
    var n = series.length;

    var maxV = 0;
    for (var ci = 0; ci < n; ci++) maxV = Math.max(maxV, Number(series[ci] || 0));
    var yMax = niceMax(maxV);

    // 날짜 파싱 "2026-04-06" → { year:"2026", md:"4/6" }
    var _parseLbl = function (dl) {
      var rm = String(dl || "").match(/^(\d{4})-(\d{2})-(\d{2})$/);
      if (!rm) return { year: "", md: String(dl || "") };
      return { year: rm[1], md: String(parseInt(rm[2])) + "/" + String(parseInt(rm[3])) };
    };

    // 모든 데이터 캔버스에 저장 (호버 핸들러에서 재사용)
    canvas._rd = { series: series, dateLabels: dateLabels, n: n, yMax: yMax,
                   accent: accent, MT: MT, MR: MR, MB: MB, ML: ML };

    var _render = function (hoverIdx) {
      var d = canvas._rd;
      if (!d) return;

      var scaled = dprScale(canvas);
      var ctx = scaled.ctx, W = scaled.w, H = scaled.h;
      clear(ctx, W, H);

      var iW = Math.max(1, W - d.ML - d.MR);
      var iH = Math.max(1, H - d.MT - d.MB);
      var x0 = d.ML, y0 = d.MT;

      var _px = function (idx) { return x0 + (iW * idx) / (d.n - 1); };
      var _py = function (val) { return y0 + iH - (iH * Number(val || 0)) / Math.max(1, d.yMax); };

      // 레이아웃 캐시 (hover 위치 계산용)
      canvas._rl = { iW: iW, iH: iH, x0: x0, y0: y0, W: W, H: H };

      // 그리드
      drawGrid(ctx, x0, y0, iW, iH, 32, GRID);

      // Y축
      ctx.save();
      ctx.fillStyle = TCOL;
      ctx.font = "11px ui-sans-serif,system-ui,sans-serif";
      ctx.textAlign = "right";
      ctx.textBaseline = "middle";
      for (var ti = 0; ti <= 4; ti++) {
        ctx.fillText(fmtShort(d.yMax * (4 - ti) / 4), x0 - 6, y0 + (iH * ti) / 4);
      }
      ctx.restore();

      // X축 날짜 레이블 (−36° 회전)
      var stepPx = iW / (d.n - 1);
      var skip = Math.max(1, Math.ceil(56 / Math.max(1, stepPx)));
      var prevYr = "";
      ctx.save();
      for (var xi = 0; xi < d.n; xi++) {
        if (xi % skip !== 0) continue;
        var pl = _parseLbl(d.dateLabels && d.dateLabels[xi]);
        var yrChanged = pl.year && pl.year !== prevYr;
        if (pl.year) prevYr = pl.year;
        var lbl = yrChanged ? ("'" + pl.year.slice(2) + " " + pl.md) : pl.md;
        ctx.save();
        ctx.translate(_px(xi), y0 + iH + 8);
        ctx.rotate(-Math.PI / 5);
        ctx.font = yrChanged ? "bold 10px ui-sans-serif,system-ui,sans-serif" : "10px ui-sans-serif,system-ui,sans-serif";
        ctx.fillStyle = yrChanged ? "rgba(234,240,255,.92)" : "rgba(234,240,255,.55)";
        ctx.textAlign = "right";
        ctx.textBaseline = "top";
        ctx.fillText(lbl, 0, 0);
        ctx.restore();
      }
      ctx.restore();

      // 선
      ctx.save();
      ctx.lineWidth = 2.2;
      ctx.strokeStyle = d.accent;
      ctx.shadowColor = hexToRgba(d.accent, 0.28);
      ctx.shadowBlur = 14;
      ctx.beginPath();
      for (var li = 0; li < d.n; li++) {
        if (li === 0) ctx.moveTo(_px(li), _py(d.series[li]));
        else ctx.lineTo(_px(li), _py(d.series[li]));
      }
      ctx.stroke();
      ctx.restore();

      // 점
      ctx.save();
      for (var pi = 0; pi < d.n; pi++) {
        var isH = (pi === hoverIdx);
        ctx.beginPath();
        ctx.fillStyle = isH ? "rgba(255,255,255,.95)" : hexToRgba(d.accent, 0.80);
        ctx.arc(_px(pi), _py(d.series[pi]), isH ? 5.5 : 3, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.restore();

      // 호버: 수직선 + 툴팁
      if (hoverIdx >= 0 && hoverIdx < d.n) {
        var hx = _px(hoverIdx);
        var hy = _py(d.series[hoverIdx]);

        ctx.save();
        ctx.strokeStyle = "rgba(234,240,255,.22)";
        ctx.lineWidth = 1;
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        ctx.moveTo(hx, y0);
        ctx.lineTo(hx, y0 + iH);
        ctx.stroke();
        ctx.restore();

        var hp = _parseLbl(d.dateLabels && d.dateLabels[hoverIdx]);
        var dtxt = hp.year ? (hp.year + "년 " + hp.md) : hp.md;
        var ptxt = Number(d.series[hoverIdx] || 0).toLocaleString("ko-KR") + "원";

        ctx.save();
        ctx.font = "bold 12px ui-sans-serif,system-ui,sans-serif";
        var bw = Math.max(ctx.measureText(ptxt).width, (ctx.font = "10px ui-sans-serif,system-ui,sans-serif", ctx.measureText(dtxt).width)) + 22;
        var bh = 44;
        var bx = hx + 12;
        var by = hy - 28;
        if (bx + bw > W - 4) bx = hx - bw - 12;
        if (by < y0) by = y0 + 2;
        if (by + bh > y0 + iH) by = y0 + iH - bh;

        ctx.fillStyle = "rgba(8,14,28,.90)";
        ctx.strokeStyle = hexToRgba(d.accent, 0.55);
        ctx.lineWidth = 1;
        roundRect(ctx, bx, by, bw, bh, 8);
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = "rgba(234,240,255,.72)";
        ctx.font = "10px ui-sans-serif,system-ui,sans-serif";
        ctx.textAlign = "left";
        ctx.textBaseline = "top";
        ctx.fillText(dtxt, bx + 11, by + 8);
        ctx.fillStyle = d.accent;
        ctx.font = "bold 13px ui-sans-serif,system-ui,sans-serif";
        ctx.fillText(ptxt, bx + 11, by + 23);
        ctx.restore();
      }
    };

    _render(-1);

    var _lastHover = -1;
    var _onMove = function (e) {
      var lay = canvas._rl;
      if (!lay) return;
      var rect = canvas.getBoundingClientRect();
      var mx = (e.clientX - rect.left) * (canvas.width / rect.width);  // DPR 보정
      // CSS 픽셀 기준으로 다시 계산
      mx = e.clientX - rect.left;
      var closest = -1, minD = Infinity;
      for (var ii = 0; ii < n; ii++) {
        var xi2 = lay.x0 + (lay.iW * ii) / (n - 1);
        var dd = Math.abs(mx - xi2);
        if (dd < minD) { minD = dd; closest = ii; }
      }
      if (minD > lay.iW / Math.max(1, n - 1) * 0.6 + 12) closest = -1;
      if (closest !== _lastHover) { _lastHover = closest; _render(closest); }
    };
    var _onLeave = function () {
      if (_lastHover !== -1) { _lastHover = -1; _render(-1); }
    };

    canvas.addEventListener("mousemove", _onMove);
    canvas.addEventListener("mouseleave", _onLeave);
    canvas._riceCleanup = function () {
      canvas.removeEventListener("mousemove", _onMove);
      canvas.removeEventListener("mouseleave", _onLeave);
      canvas._rd = null;
      canvas._rl = null;
    };
  }

  function barChart(canvas, values, opts) {
    if (!canvas) return;
    var o = opts || {};
    var accent = o.accent || getCssVar("--accent2") || "#A78BFF";
    var grid = o.grid || "rgba(234,240,255,.08)";

    var m = { t: 18, r: 14, b: 18, l: 14 };
    var scaled = dprScale(canvas);
    var ctx = scaled.ctx, W = scaled.w, H = scaled.h;
    clear(ctx, W, H);

    var innerW = Math.max(1, W - m.l - m.r);
    var innerH = Math.max(1, H - m.t - m.b);
    var x0 = m.l, y0 = m.t;

    var maxV = 0;
    for (var i = 0; i < values.length; i++) maxV = Math.max(maxV, Number(values[i] || 0));
    var yMax = niceMax(maxV);

    drawGrid(ctx, x0, y0, innerW, innerH, 28, grid);

    var n = Math.max(1, values.length);
    var gap = 10;
    var bw = (innerW - gap * (n - 1)) / n;
    bw = Math.max(10, bw);

    ctx.save();
    for (var k = 0; k < values.length; k++) {
      var v = Number(values[k] || 0);
      var h = (innerH * v) / Math.max(1, yMax);
      var x = x0 + k * (bw + gap);
      var y = y0 + innerH - h;

      var grad = ctx.createLinearGradient(0, y, 0, y + h);
      grad.addColorStop(0, hexToRgba(accent, 0.92));
      grad.addColorStop(1, hexToRgba(accent, 0.22));

      ctx.fillStyle = grad;
      ctx.strokeStyle = hexToRgba(accent, 0.28);
      ctx.lineWidth = 1;
      roundRect(ctx, x, y, bw, h, 10);
      ctx.fill();
      ctx.stroke();
    }
    ctx.restore();
  }

  function donutChart(canvas, parts, opts) {
    if (!canvas) return;
    var o = opts || {};
    var a1 = getCssVar("--accent") || "#00D4FF";
    var a2 = getCssVar("--accent2") || "#A78BFF";
    var colors = o.colors || [a1, a2, "#FFD36A", "#9AF7D0", "#FF7AD9"];
    var bgRing = o.bgRing || "rgba(234,240,255,.10)";

    var scaled = dprScale(canvas);
    var ctx = scaled.ctx, W = scaled.w, H = scaled.h;
    clear(ctx, W, H);

    var cx = W / 2, cy = H / 2;
    var r = Math.min(W, H) * 0.34;
    var thickness = Math.max(10, Math.min(22, r * 0.35));

    var sum = 0;
    for (var i = 0; i < parts.length; i++) sum += Number(parts[i] || 0);
    sum = Math.max(1, sum);

    ctx.save();
    ctx.lineCap = "round";
    ctx.lineWidth = thickness;
    ctx.strokeStyle = bgRing;
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.stroke();
    ctx.restore();

    var start = -Math.PI / 2;
    for (var p = 0; p < parts.length; p++) {
      var v = Number(parts[p] || 0);
      var angle = (v / sum) * Math.PI * 2;
      ctx.save();
      ctx.lineCap = "round";
      ctx.lineWidth = thickness;
      ctx.strokeStyle = colors[p % colors.length];
      ctx.shadowColor = hexToRgba(colors[p % colors.length], 0.22);
      ctx.shadowBlur = 16;
      ctx.beginPath();
      ctx.arc(cx, cy, r, start, start + angle);
      ctx.stroke();
      ctx.restore();
      start += angle;
    }
  }

  function roundRect(ctx, x, y, w, h, r) {
    var radius = Math.min(r, w / 2, h / 2);
    ctx.beginPath();
    ctx.moveTo(x + radius, y);
    ctx.arcTo(x + w, y, x + w, y + h, radius);
    ctx.arcTo(x + w, y + h, x, y + h, radius);
    ctx.arcTo(x, y + h, x, y, radius);
    ctx.arcTo(x, y, x + w, y, radius);
    ctx.closePath();
  }

  window.EtCharts = {
    lineChart: lineChart,
    barChart: barChart,
    donutChart: donutChart,
    riceLineChart: riceLineChart
  };
})();
