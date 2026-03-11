(function () {
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

  function lineChart(canvas, series, opts) {
    if (!canvas) return;
    var o = opts || {};
    var accent = o.accent || "#6AE4FF";
    var grid = o.grid || "rgba(234,240,255,.08)";
    var text = o.text || "rgba(234,240,255,.70)";

    var m = { t: 18, r: 14, b: 26, l: 34 };
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

    // axes labels (minimal)
    ctx.save();
    ctx.fillStyle = text;
    ctx.font = "12px ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial";
    ctx.textAlign = "right";
    ctx.textBaseline = "middle";
    var ticks = 4;
    for (var t = 0; t <= ticks; t++) {
      var v = (yMax * (ticks - t)) / ticks;
      var yy = y0 + (innerH * t) / ticks;
      ctx.fillText(String(Math.round(v)), x0 - 8, yy);
    }
    ctx.restore();

    // line
    var n = Math.max(2, series.length);
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

    // points
    ctx.save();
    for (var p = 0; p < series.length; p++) {
      var xp = x0 + (innerW * p) / (n - 1);
      var vp = Number(series[p] || 0);
      var yp = y0 + innerH - (innerH * vp) / Math.max(1, yMax);
      ctx.beginPath();
      ctx.fillStyle = hexToRgba(accent, 0.92);
      ctx.arc(xp, yp, 3.2, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();
  }

  function barChart(canvas, values, opts) {
    if (!canvas) return;
    var o = opts || {};
    var accent = o.accent || "#B79BFF";
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
    var colors = o.colors || ["#6AE4FF", "#B79BFF", "#FFD36A", "#9AF7D0", "#FF7AD9"];
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
    donutChart: donutChart
  };
})();
