/* Atmosphere: deterministic particle systems (pure functions of t). Each draws into the visible rect `v` = {x0,y0,x1,y1}. */
(function () {
  const SF = window.SF;
  const { rgba, rnd, clamp, lerp, noise } = SF;
  const P = SF.paint;
  const fx = (SF.fx = {});
  const area = (v) => [v.x0 - 60, v.y0 - 60, v.x1 - v.x0 + 120, v.y1 - v.y0 + 120];

  fx.rain = (g, t, v, o = {}) => {
    const [x0, y0, w, h] = area(v);
    const n = Math.round((o.density || 1) * 420 * (w * h) / (1920 * 1080));
    const ang = (o.angle === undefined ? 8 : o.angle) * Math.PI / 180;
    g.save(); g.lineCap = 'round';
    for (let i = 0; i < n; i++) {
      const depth = 0.35 + rnd(i, 5) * 0.65;
      const sp = (1500 + rnd(i, 3) * 900) * depth;
      const len = (26 + rnd(i, 4) * 30) * depth;
      const yy = ((rnd(i, 2) * h + t * sp) % h) + y0;
      const xx = ((rnd(i, 1) * w + t * sp * Math.tan(ang)) % w) + x0;
      g.strokeStyle = rgba(o.color || '#c9d6ea', (0.18 + 0.32 * depth) * (o.alpha || 1)); g.lineWidth = 1 + 1.4 * depth;
      g.beginPath(); g.moveTo(xx, yy); g.lineTo(xx + Math.sin(ang) * len, yy + Math.cos(ang) * len); g.stroke();
    }
    if (o.splashY) for (let i = 0; i < n / 6; i++) {
      const per = 0.35 + rnd(i, 9) * 0.4, ph = ((t + rnd(i, 8) * per) % per) / per;
      const xx = x0 + rnd(i, 7) * w, yy = o.splashY + rnd(i, 6) * 160;
      P.ell(g, xx, yy, 6 + ph * 14, (2 + ph * 4) * 0.5, null, 0, rgba(o.color || '#c9d6ea', 0.35 * (1 - ph)), 1.5);
    }
    g.restore();
  };
  fx.snow = (g, t, v, o = {}) => {
    const [x0, y0, w, h] = area(v);
    const n = Math.round((o.density || 1) * 260 * (w * h) / (1920 * 1080));
    for (let i = 0; i < n; i++) {
      const d = 0.3 + rnd(i, 5) * 0.7, sp = 60 + 90 * d;
      const yy = ((rnd(i, 2) * h + t * sp) % h) + y0;
      const xx = x0 + ((rnd(i, 1) * w + Math.sin(t * 0.8 + i) * 30 * d) % w + w) % w;
      P.circle(g, xx, yy, 1.5 + 3.5 * d, rgba('#ffffff', 0.35 + 0.5 * d));
    }
  };
  fx.leaves = (g, t, v, o = {}) => {
    const [x0, y0, w, h] = area(v);
    const n = Math.round((o.density || 1) * 26);
    const cols = o.colors || ['#c58b48', '#b46a3d', '#d6a557', '#9c5a35'];
    for (let i = 0; i < n; i++) {
      const sp = 70 + rnd(i, 3) * 80, drift = (o.wind === undefined ? 90 : o.wind) * (0.6 + rnd(i, 4));
      const yy = ((rnd(i, 2) * h + t * sp) % h) + y0;
      const xx = x0 + ((rnd(i, 1) * w + t * drift + Math.sin(t * 1.7 + i) * 40) % w + w) % w;
      const rot = t * (1.5 + rnd(i, 6) * 2) + i;
      g.save(); g.translate(xx, yy); g.rotate(rot); g.scale(1, Math.abs(Math.sin(rot * 0.7)) * 0.8 + 0.2);
      P.ell(g, 0, 0, 13, 6, cols[i % cols.length]); g.restore();
    }
  };
  fx.dust = (g, t, v, o = {}) => { // floating motes, best inside a light beam
    const [x0, y0, w, h] = o.rect ? [o.rect[0], o.rect[1], o.rect[2], o.rect[3]] : area(v);
    const n = Math.round((o.density || 1) * 70);
    for (let i = 0; i < n; i++) {
      const xx = x0 + ((rnd(i, 1) * w + noise(t * 0.2 + i, 3) * 60 + t * 6) % w + w) % w;
      const yy = y0 + ((rnd(i, 2) * h + noise(t * 0.17 + i, 4) * 50 - t * 4) % h + h) % h;
      const a = (0.25 + 0.5 * rnd(i, 5)) * (0.5 + 0.5 * Math.sin(t * 1.3 + i));
      P.circle(g, xx, yy, 1.2 + rnd(i, 6) * 2.2, rgba(o.color || '#fff6dd', a * (o.alpha || 0.8)));
    }
  };
  fx.steamPuff = (g, x, y, s = 1, t = 0) => {
    g.save(); g.lineCap = 'round';
    for (let k = 0; k < 3; k++) {
      g.beginPath();
      for (let i = 0; i <= 12; i++) { const u = i / 12; const xx = x + (k - 1) * 8 * s + Math.sin(u * 6 + t * 2.4 + k) * 7 * s * u; const yy = y - u * 70 * s; i ? g.lineTo(xx, yy) : g.moveTo(xx, yy); }
      g.strokeStyle = rgba('#ffffff', 0.22 - k * 0.04); g.lineWidth = 6 * s; g.stroke();
    }
    g.restore();
  };
  fx.steam = (g, t, v, o = {}) => fx.steamPuff(g, o.x, o.y, o.s || 1, t);
  fx.sparkles = (g, t, v, o = {}) => {
    const [x0, y0, w, h] = o.rect ? [o.rect[0], o.rect[1], o.rect[2], o.rect[3]] : area(v);
    for (let i = 0; i < (o.n || 30); i++) {
      const per = 1.2 + rnd(i, 3) * 1.4, ph = ((t + rnd(i, 4) * per) % per) / per, a = Math.sin(ph * Math.PI);
      const xx = x0 + rnd(i, 1) * w, yy = y0 + rnd(i, 2) * h, r = (4 + rnd(i, 5) * 8) * a;
      g.save(); g.translate(xx, yy); g.fillStyle = rgba(o.color || '#fff4cf', 0.9 * a);
      g.beginPath(); g.moveTo(0, -r * 2); g.lineTo(r * 0.4, 0); g.lineTo(0, r * 2); g.lineTo(-r * 0.4, 0); g.closePath(); g.fill();
      g.beginPath(); g.moveTo(-r * 2, 0); g.lineTo(0, r * 0.4); g.lineTo(r * 2, 0); g.lineTo(0, -r * 0.4); g.closePath(); g.fill(); g.restore();
    }
  };
  fx.fireflies = (g, t, v, o = {}) => { const [x0, y0, w, h] = area(v); for (let i = 0; i < (o.n || 24); i++) { const xx = x0 + ((rnd(i, 1) * w + noise(t * 0.3 + i, 2) * 120) % w + w) % w, yy = y0 + h * 0.4 + rnd(i, 2) * h * 0.5 + noise(t * 0.25 + i, 5) * 60; const a = 0.5 + 0.5 * Math.sin(t * 2 + i * 1.7); P.glow(g, xx, yy, 26, '#ffe58a', 0.8 * a); } };
  fx.fog = (g, t, v, o = {}) => {
    const [x0, y0, w, h] = area(v);
    for (let i = 0; i < 6; i++) { const yy = (o.y || v.y0 + (v.y1 - v.y0) * 0.65) + (i - 3) * 50; const xx = x0 + ((t * (12 + i * 5) + i * 400) % (w + 800)) - 400; P.ell(g, xx, yy, 700, 70, rgba(o.color || '#c9d2dd', (o.alpha || 0.08))); P.ell(g, xx + w * 0.5, yy + 20, 600, 60, rgba(o.color || '#c9d2dd', (o.alpha || 0.08))); }
  };
  fx.confetti = (g, t, v, o = {}) => {
    const [x0, y0, w, h] = area(v); const cols = ['#f2b84b', '#e86b5a', '#4f8ef0', '#4fb38a', '#ec6ba8'];
    const t0 = o.t0 || 0; if (t < t0) return; const u = t - t0;
    for (let i = 0; i < (o.n || 120); i++) { const xx = x0 + rnd(i, 1) * w + Math.sin(u * 3 + i) * 20, yy = y0 - 50 + u * (180 + rnd(i, 2) * 200) - rnd(i, 3) * 300; if (yy > y0 + h) continue; g.save(); g.translate(xx, yy); g.rotate(u * 4 + i); P.rect(g, -6, -3, 12, 6, cols[i % 5]); g.restore(); }
  };
  /** returns a 0..1 flash amount for a lightning strike at t0 */
  fx.lightningAmount = (t, t0) => { const u = t - t0; if (u < 0 || u > 0.6) return 0; return Math.max(0, 1 - u * 6) + (u > 0.15 && u < 0.3 ? 0.6 : 0); };
})();
