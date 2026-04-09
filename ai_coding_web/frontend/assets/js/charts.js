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
  function _riceDraw(canvas, hoverIdx) {
    var d = canvas._riceD;
    if (!d) return;

    var scaled = dprScale(canvas);
    var ctx = scaled.ctx, W = scaled.w, H = scaled.h;
    clear(ctx, W, H);

    var x0 = d.ml, y0 = d.mt;
    var iW = Math.max(1, W - d.ml - d.mr);
    var iH = Math.max(1, H - d.mt - d.mb);
    var n = d.n, yMax = d.yMax, accent = d.ac;

    // 레이아웃 캐시 업데이트
    canvas._riceL = { x0: x0, y0: y0, iW: iW, iH: iH, W: W, H: H };

    function gpx(i) { return x0 + (iW * i) / (n - 1); }
    function gpy(v) { return y0 + iH - (iH * (Number(v) || 0)) / yMax; }

    // 그리드
    drawGrid(ctx, x0, y0, iW, iH, 28, "rgba(234,240,255,.08)");

    // Y축 레이블
    ctx.save();
    ctx.fillStyle = "rgba(234,240,255,.70)";
    ctx.font = "11px ui-sans-serif, system-ui, sans-serif";
    ctx.textAlign = "right";
    ctx.textBaseline = "middle";
    for (var t = 0; t <= 4; t++) {
      ctx.fillText(fmtShort(yMax * (4 - t) / 4), x0 - 5, y0 + (iH * t) / 4);
    }
    ctx.restore();

    // 선
    ctx.save();
    ctx.lineWidth = 2.25;
    ctx.strokeStyle = accent;
    ctx.shadowColor = hexToRgba(accent, 0.25);
    ctx.shadowBlur = 18;
    ctx.beginPath();
    for (var k = 0; k < n; k++) {
      if (k === 0) ctx.moveTo(gpx(k), gpy(d.sv[k]));
      else         ctx.lineTo(gpx(k), gpy(d.sv[k]));
    }
    ctx.stroke();
    ctx.restore();

    // 포인트
    ctx.save();
    for (var p = 0; p < n; p++) {
      ctx.beginPath();
      ctx.fillStyle = (p === hoverIdx) ? "rgba(255,255,255,.95)" : hexToRgba(accent, 0.85);
      ctx.arc(gpx(p), gpy(d.sv[p]), (p === hoverIdx) ? 5 : 3, 0, 6.2832);
      ctx.fill();
    }
    ctx.restore();

    // X축 날짜 레이블 (-35° 회전)
    var spx = iW / (n - 1);
    var skip = Math.max(1, Math.ceil(52 / Math.max(1, spx)));
    var prevY = "";
    ctx.save();
    for (var li = 0; li < n; li++) {
      if (li % skip !== 0) continue;
      var dl = String(d.dl[li] || "");
      var dm = dl.match(/^(\d{4})-(\d{2})-(\d{2})$/);
      var yr = dm ? dm[1] : "";
      var md = dm ? (parseInt(dm[2]) + "/" + parseInt(dm[3])) : dl;
      var yc = (yr && yr !== prevY);
      if (yr) prevY = yr;
      ctx.save();
      ctx.translate(gpx(li), y0 + iH + 7);
      ctx.rotate(-0.61);           // ≈ −35°
      ctx.font      = yc ? "bold 10px ui-sans-serif,system-ui,sans-serif"
                         : "10px ui-sans-serif,system-ui,sans-serif";
      ctx.fillStyle = yc ? "rgba(234,240,255,.92)" : "rgba(234,240,255,.58)";
      ctx.textAlign    = "right";
      ctx.textBaseline = "top";
      ctx.fillText(yc ? ("'" + yr.slice(2) + " " + md) : md, 0, 0);
      ctx.restore();
    }
    ctx.restore();

    // 호버: 수직선 + 툴팁
    if (hoverIdx >= 0 && hoverIdx < n) {
      var hx = gpx(hoverIdx), hy = gpy(d.sv[hoverIdx]);

      ctx.save();
      ctx.strokeStyle = "rgba(234,240,255,.22)";
      ctx.lineWidth   = 1;
      ctx.setLineDash([4, 4]);
      ctx.beginPath(); ctx.moveTo(hx, y0); ctx.lineTo(hx, y0 + iH);
      ctx.stroke();
      ctx.restore();

      var hdl  = String(d.dl[hoverIdx] || "");
      var hm   = hdl.match(/^(\d{4})-(\d{2})-(\d{2})$/);
      var dtxt = hm ? (hm[1] + "년 " + parseInt(hm[2]) + "/" + parseInt(hm[3])) : hdl;
      var ptxt = (Number(d.sv[hoverIdx]) || 0).toLocaleString("ko-KR") + "원";

      ctx.save();
      ctx.font = "bold 12px ui-sans-serif,system-ui,sans-serif";
      var tw1 = ctx.measureText(ptxt).width;
      ctx.font = "10px ui-sans-serif,system-ui,sans-serif";
      var tw2 = ctx.measureText(dtxt).width;
      var bw = Math.max(tw1, tw2) + 22, bh = 44;
      var bx = hx + 12, by = hy - 28;
      if (bx + bw > W - 4) bx = hx - bw - 12;
      if (by < y0)        by = y0 + 2;
      if (by + bh > y0 + iH) by = y0 + iH - bh;

      ctx.fillStyle   = "rgba(8,14,28,.90)";
      ctx.strokeStyle = hexToRgba(accent, 0.55);
      ctx.lineWidth   = 1;
      roundRect(ctx, bx, by, bw, bh, 8);
      ctx.fill(); ctx.stroke();

      ctx.fillStyle    = "rgba(234,240,255,.72)";
      ctx.font         = "10px ui-sans-serif,system-ui,sans-serif";
      ctx.textAlign    = "left";
      ctx.textBaseline = "top";
      ctx.fillText(dtxt, bx + 11, by + 8);
      ctx.fillStyle = accent;
      ctx.font      = "bold 13px ui-sans-serif,system-ui,sans-serif";
      ctx.fillText(ptxt, bx + 11, by + 23);
      ctx.restore();
    }
  }

  function riceLineChart(canvas, series, dateLabels, opts) {
    if (!canvas || !series || series.length < 2) return;
    if (canvas._riceCleanup) { canvas._riceCleanup(); canvas._riceCleanup = null; }

    var o = opts || {};
    var maxV = 0;
    for (var i = 0; i < series.length; i++) {
      var v = Number(series[i]);
      if (!isNaN(v) && v > maxV) maxV = v;
    }

    canvas._riceD = {
      sv: series, dl: dateLabels || [], n: series.length,
      yMax: niceMax(maxV || 1), ac: o.accent || "#9AF7D0",
      mt: 28, mr: 18, mb: 72, ml: 52
    };

    _riceDraw(canvas, -1);

    var _hi = -1;
    var onMove = function (e) {
      var lay = canvas._riceL;
      if (!lay) return;
      var rect = canvas.getBoundingClientRect();
      var mx   = e.clientX - rect.left;
      var nn   = canvas._riceD ? canvas._riceD.n : 0;
      if (nn < 2) return;
      var closest = 0, minD = Infinity;
      for (var ii = 0; ii < nn; ii++) {
        var xx = lay.x0 + (lay.iW * ii) / (nn - 1);
        var dd = Math.abs(mx - xx);
        if (dd < minD) { minD = dd; closest = ii; }
      }
      if (minD > lay.iW / (nn - 1) + 8) closest = -1;
      if (closest !== _hi) { _hi = closest; _riceDraw(canvas, closest); }
    };
    var onLeave = function () {
      if (_hi !== -1) { _hi = -1; _riceDraw(canvas, -1); }
    };

    canvas.addEventListener("mousemove", onMove);
    canvas.addEventListener("mouseleave", onLeave);
    canvas._riceCleanup = function () {
      canvas.removeEventListener("mousemove", onMove);
      canvas.removeEventListener("mouseleave", onLeave);
      canvas._riceD = null;
      canvas._riceL = null;
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
