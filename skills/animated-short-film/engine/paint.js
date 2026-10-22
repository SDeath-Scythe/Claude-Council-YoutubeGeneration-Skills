/* Drawing helpers and palettes. All helpers take the 2D context `g` first. */
(function () {
  const SF = window.SF;
  const { rgba, mixColor, shade, clamp, lerp } = SF;
  const P = (SF.paint = {});

  // ---------- palettes (the film's colour script) ----------
  // Muted, desaturated world + one warm accent; characters are ink silhouettes with a rim.
  SF.PALETTES = {
    day: { sky: ['#b9cad8', '#e8edf1'], wall: '#d7dade', wall2: '#c3c7cd', trim: '#eceef0', floor: '#cbc7c0', floor2: '#b4b0a9', furn: '#e8eaed', furn2: '#b8bdc4', metal: '#9ba1a9', dark: '#3c4148', glass: '#d3dee8', accent: '#e2a54b', accent2: '#5d8db3', green: '#7fae58', light: '#fff4dc', ink: '#08080a', rim: '#eceef1', shadowA: 0.22, lightA: 0.25, ambient: null },
    overcast: { sky: ['#a6b1bc', '#d3d8dd'], wall: '#c4c8cd', wall2: '#adb2b9', trim: '#dadde1', floor: '#a9aaa8', floor2: '#96979a', furn: '#d5d8dc', furn2: '#a3a8b0', metal: '#8d939b', dark: '#353a41', glass: '#bcc6cf', accent: '#d39a4a', accent2: '#5b7f9f', green: '#6f8f5a', light: '#f3efe6', ink: '#08080a', rim: '#d9dce1', shadowA: 0.2, lightA: 0.15, ambient: { color: '#7d8a99', a: 0.12, mode: 'multiply' } },
    dusk: { sky: ['#283049', '#76616a'], wall: '#77727a', wall2: '#5f5b64', trim: '#8a858c', floor: '#4b4950', floor2: '#3c3a41', furn: '#8d8992', furn2: '#6b6870', metal: '#7b7b85', dark: '#22222a', glass: '#3e4a66', accent: '#e6a95a', accent2: '#6f86b5', green: '#5f7350', light: '#ffcf8a', ink: '#070709', rim: '#b7b2bd', shadowA: 0.3, lightA: 0.45, ambient: { color: '#3a3550', a: 0.18, mode: 'multiply' } },
    night: { sky: ['#0d121c', '#1c2638'], wall: '#4c5461', wall2: '#3c434e', trim: '#5a626e', floor: '#2f343c', floor2: '#262a31', furn: '#68707b', furn2: '#525963', metal: '#7a818b', dark: '#181b21', glass: '#26344d', accent: '#f0bf6c', accent2: '#5e7bb0', green: '#3c4c3e', light: '#ffd48e', ink: '#050507', rim: '#8892a1', shadowA: 0.35, lightA: 0.6, ambient: { color: '#1e2a44', a: 0.22, mode: 'multiply' } },
    warm: { sky: ['#1a2132', '#3a3a4c'], wall: '#a58f7c', wall2: '#8b7766', trim: '#b9a593', floor: '#5f4c40', floor2: '#4d3d33', furn: '#c2ad98', furn2: '#94806e', metal: '#9b8f84', dark: '#2b221d', glass: '#2f3a52', accent: '#f2b25c', accent2: '#6e86a8', green: '#61704f', light: '#ffcb80', ink: '#08070a', rim: '#d9c4ad', shadowA: 0.3, lightA: 0.5, ambient: { color: '#5a3d2a', a: 0.12, mode: 'multiply' } },
    cold: { sky: ['#8796a6', '#c3ccd5'], wall: '#9aa3ad', wall2: '#838c97', trim: '#aeb6bf', floor: '#6f767f', floor2: '#5f656e', furn: '#b3bac2', furn2: '#8c939c', metal: '#7f8790', dark: '#262b32', glass: '#9fb0c2', accent: '#c9a16a', accent2: '#5f7d9c', green: '#5d6f61', light: '#e8ecf0', ink: '#07080a', rim: '#cbd2da', shadowA: 0.25, lightA: 0.2, ambient: { color: '#4b5b70', a: 0.18, mode: 'multiply' } },
    sunrise: { sky: ['#f1a27c', '#fde0bd'], wall: '#e9cdb6', wall2: '#d3b39b', trim: '#f4e1d1', floor: '#c99b80', floor2: '#b4876d', furn: '#f1dccb', furn2: '#cfae97', metal: '#b89c8a', dark: '#4a3330', glass: '#f8d2b0', accent: '#ffb35c', accent2: '#7d8fc4', green: '#8aa35d', light: '#fff0c8', ink: '#0a0708', rim: '#ffe6cc', shadowA: 0.2, lightA: 0.5, ambient: { color: '#ffb07a', a: 0.08, mode: 'soft-light' } },
    void: { sky: ['#050608', '#101318'], wall: '#14171c', wall2: '#0d0f13', trim: '#1c2027', floor: '#181b20', floor2: '#0f1114', furn: '#2a2f37', furn2: '#1f232a', metal: '#3b414b', dark: '#050607', glass: '#1a2230', accent: '#f2c26b', accent2: '#5a78b0', green: '#2f3a33', light: '#fff1d0', ink: '#000000', rim: '#6d7480', shadowA: 0.5, lightA: 0.9, ambient: null },
  };
  /** palette by name, or a blend: SF.palette('night'), SF.palette('day','sunrise',0.4) */
  SF.palette = function (a, b, k) {
    const A = typeof a === 'string' ? SF.PALETTES[a] || SF.PALETTES.day : a;
    if (!b) return A;
    const B = typeof b === 'string' ? SF.PALETTES[b] : b;
    return SF.mixVal(A, B, k);
  };

  // ---------- shapes ----------
  P.rrPath = (g, x, y, w, h, r) => {
    r = Math.max(0, Math.min(r, Math.abs(w) / 2, Math.abs(h) / 2));
    g.beginPath(); g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r);
    g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath();
  };
  P.rr = (g, x, y, w, h, r, fill, stroke, lw = 2) => {
    P.rrPath(g, x, y, w, h, r);
    if (fill) { g.fillStyle = fill; g.fill(); }
    if (stroke) { g.strokeStyle = stroke; g.lineWidth = lw; g.stroke(); }
  };
  P.rect = (g, x, y, w, h, fill) => { g.fillStyle = fill; g.fillRect(x, y, w, h); };
  P.ell = (g, x, y, rx, ry, fill, rot = 0, stroke, lw = 2) => {
    g.beginPath(); g.ellipse(x, y, Math.abs(rx), Math.abs(ry), rot, 0, Math.PI * 2);
    if (fill) { g.fillStyle = fill; g.fill(); }
    if (stroke) { g.strokeStyle = stroke; g.lineWidth = lw; g.stroke(); }
  };
  P.circle = (g, x, y, r, fill, stroke, lw) => P.ell(g, x, y, r, r, fill, 0, stroke, lw);
  P.polyPath = (g, pts) => {
    g.beginPath();
    if (typeof pts[0] === 'number') { g.moveTo(pts[0], pts[1]); for (let i = 2; i < pts.length; i += 2) g.lineTo(pts[i], pts[i + 1]); }
    else { g.moveTo(pts[0][0], pts[0][1]); for (let i = 1; i < pts.length; i++) g.lineTo(pts[i][0], pts[i][1]); }
    g.closePath();
  };
  P.poly = (g, pts, fill, stroke, lw = 2) => {
    P.polyPath(g, pts);
    if (fill) { g.fillStyle = fill; g.fill(); }
    if (stroke) { g.strokeStyle = stroke; g.lineWidth = lw; g.lineJoin = 'round'; g.stroke(); }
  };
  P.line = (g, x1, y1, x2, y2, color, w = 2, cap = 'round') => {
    g.beginPath(); g.moveTo(x1, y1); g.lineTo(x2, y2); g.strokeStyle = color; g.lineWidth = w; g.lineCap = cap; g.stroke();
  };
  /** stroke a polyline [[x,y],...] */
  P.path = (g, pts, color, w = 2, cap = 'round', join = 'round') => {
    if (!pts.length) return;
    g.beginPath(); g.moveTo(pts[0][0], pts[0][1]);
    for (let i = 1; i < pts.length; i++) g.lineTo(pts[i][0], pts[i][1]);
    g.strokeStyle = color; g.lineWidth = w; g.lineCap = cap; g.lineJoin = join; g.stroke();
  };
  /** smooth curve through points (quadratic midpoints) */
  P.curve = (g, pts, color, w = 2, fill) => {
    if (pts.length < 2) return;
    g.beginPath(); g.moveTo(pts[0][0], pts[0][1]);
    for (let i = 1; i < pts.length - 1; i++) {
      const mx = (pts[i][0] + pts[i + 1][0]) / 2, my = (pts[i][1] + pts[i + 1][1]) / 2;
      g.quadraticCurveTo(pts[i][0], pts[i][1], mx, my);
    }
    const L = pts[pts.length - 1]; g.lineTo(L[0], L[1]);
    if (fill) { g.fillStyle = fill; g.fill(); }
    if (color) { g.strokeStyle = color; g.lineWidth = w; g.lineCap = 'round'; g.lineJoin = 'round'; g.stroke(); }
  };

  // ---------- gradients & light ----------
  P.lin = (g, x0, y0, x1, y1, stops) => { const gr = g.createLinearGradient(x0, y0, x1, y1); for (const [o, c] of stops) gr.addColorStop(o, c); return gr; };
  P.rad = (g, x, y, r0, r1, stops) => { const gr = g.createRadialGradient(x, y, r0, x, y, r1); for (const [o, c] of stops) gr.addColorStop(o, c); return gr; };
  /** soft additive light blob */
  P.glow = (g, x, y, r, color, a = 1, mode = 'lighter') => {
    if (a <= 0 || r <= 0) return;
    g.save(); g.globalCompositeOperation = mode;
    g.fillStyle = P.rad(g, x, y, 0, r, [[0, rgba(color, 0.55 * a)], [0.25, rgba(color, 0.28 * a)], [0.6, rgba(color, 0.08 * a)], [1, rgba(color, 0)]]);
    g.fillRect(x - r, y - r, r * 2, r * 2); g.restore();
  };
  /** light cone from (x,y) pointing at angle dir (deg, 90 = down), spread (deg), length */
  P.cone = (g, x, y, dir, spread, len, color, a = 0.35, mode = 'lighter') => {
    const d = (dir * Math.PI) / 180, s = (spread * Math.PI) / 360;
    g.save(); g.globalCompositeOperation = mode;
    g.beginPath(); g.moveTo(x, y);
    g.lineTo(x + Math.cos(d - s) * len, y + Math.sin(d - s) * len);
    g.lineTo(x + Math.cos(d + s) * len, y + Math.sin(d + s) * len); g.closePath();
    g.fillStyle = P.rad(g, x, y, 0, len, [[0, rgba(color, a)], [0.7, rgba(color, a * 0.25)], [1, rgba(color, 0)]]);
    g.fill(); g.restore();
  };
  /** soft elliptical contact shadow */
  P.shadow = (g, x, y, rx, ry, a = 0.3, color = '#000') => {
    g.save(); g.translate(x, y); g.scale(1, ry / rx);
    g.fillStyle = P.rad(g, 0, 0, 0, rx, [[0, rgba(color, a)], [0.6, rgba(color, a * 0.5)], [1, rgba(color, 0)]]);
    g.beginPath(); g.arc(0, 0, rx, 0, Math.PI * 2); g.fill(); g.restore();
  };
  /** parallelogram light patch (window light falling on a floor/wall) */
  P.lightPatch = (g, pts, color, a = 0.18) => { g.save(); g.globalCompositeOperation = 'lighter'; P.poly(g, pts, rgba(color, a)); g.restore(); };

  // ---------- text ----------
  SF.FONTS = { caption: '"Fredoka", "Nunito", "Arial Rounded MT Bold", sans-serif', ui: '"Inter", "Helvetica Neue", Arial, sans-serif', hand: '"Fredoka", sans-serif' };
  /** text with optional outline. o: {size, weight, font, color, align, base, stroke, sw, maxW, alpha, spacing} */
  P.text = (g, s, x, y, o = {}) => {
    const size = o.size || 40, weight = o.weight || 600;
    g.save();
    g.font = `${weight} ${size}px ${o.font || SF.FONTS.ui}`;
    g.textAlign = o.align || 'center'; g.textBaseline = o.base || 'middle';
    if (o.spacing) g.letterSpacing = o.spacing + 'px';
    if (o.alpha !== undefined) g.globalAlpha *= o.alpha;
    if (o.stroke) { g.lineJoin = 'round'; g.strokeStyle = o.stroke; g.lineWidth = o.sw || size * 0.16; g.strokeText(s, x, y, o.maxW); }
    g.fillStyle = o.color || '#fff'; g.fillText(s, x, y, o.maxW);
    g.restore();
  };
  P.measure = (g, s, size = 40, weight = 600, font = SF.FONTS.ui) => { g.save(); g.font = `${weight} ${size}px ${font}`; const w = g.measureText(s).width; g.restore(); return w; };
  /** greedy word wrap -> lines */
  P.wrap = (g, s, maxW, size = 40, weight = 600, font = SF.FONTS.ui) => {
    const words = String(s).split(/\s+/); const lines = []; let cur = '';
    for (const w of words) { const t = cur ? cur + ' ' + w : w; if (P.measure(g, t, size, weight, font) > maxW && cur) { lines.push(cur); cur = w; } else cur = t; }
    if (cur) lines.push(cur); return lines;
  };

  // ---------- composition helpers ----------
  /** draw fn into an offscreen layer then composite with blur / alpha / mode */
  P.layer = (g, fn, o = {}) => {
    // blurred layers are rendered and blurred at reduced resolution (blur hides the detail anyway): 4-16x cheaper
    const W = g.canvas.width, H = g.canvas.height;
    const blur = o.blur || 0;
    const k = blur > 10 ? 0.25 : blur > 2.5 ? 0.5 : 1;
    const w = Math.ceil(W * k), h = Math.ceil(H * k);
    const c = SF.scratch(w, h, (o.key || 'layer') + k);
    const x = c.getContext('2d');
    x.setTransform(1, 0, 0, 1, 0, 0); x.clearRect(0, 0, w, h);
    const m = g.getTransform();
    x.setTransform(m.a * k, m.b * k, m.c * k, m.d * k, m.e * k, m.f * k);
    if (o.raw) x.setTransform(k, 0, 0, k, 0, 0);
    fn(x);
    g.save(); g.setTransform(1, 0, 0, 1, 0, 0);
    if (blur > 0.3) g.filter = `blur(${(blur * k).toFixed(2)}px)`;
    if (o.alpha !== undefined) g.globalAlpha = o.alpha;
    if (o.mode) g.globalCompositeOperation = o.mode;
    g.imageSmoothingQuality = 'high';
    if (k === 1) g.drawImage(c, 0, 0);
    else { // blur at low res into a second scratch, then upscale (filter on a scaled draw would blur in output pixels)
      const c2 = SF.scratch(w, h, 'blur2' + k); const x2 = c2.getContext('2d');
      x2.setTransform(1, 0, 0, 1, 0, 0); x2.clearRect(0, 0, w, h); x2.filter = g.filter; x2.drawImage(c, 0, 0); x2.filter = 'none';
      g.filter = 'none'; g.drawImage(c2, 0, 0, w, h, 0, 0, W, H);
    }
    g.restore();
  };
  P.withAlpha = (g, a, fn) => { g.save(); g.globalAlpha *= a; fn(g); g.restore(); };
  P.clip = (g, pathFn, fn) => { g.save(); pathFn(g); g.clip(); fn(g); g.restore(); };

  // ---------- small reusable bits used by props/sets ----------
  /** vertical gradient fill of a rect */
  P.vgrad = (g, x, y, w, h, c0, c1) => { g.fillStyle = P.lin(g, 0, y, 0, y + h, [[0, c0], [1, c1]]); g.fillRect(x, y, w, h); };
  /** a tiny mitten hand silhouette helper for inserts (pointing/tapping) */
  P.handPoint = (g, x, y, ang, s, color) => {
    g.save(); g.translate(x, y); g.rotate(ang); g.scale(s, s);
    g.fillStyle = color;
    P.rrPath(g, -10, -9, 24, 20, 9); g.fill();               // palm
    P.rrPath(g, 8, -8, 26, 9, 4.5); g.fill();                // index finger
    P.rrPath(g, -4, 6, 20, 8, 4); g.fill();                  // curled fingers
    P.rrPath(g, -40, -8, 40, 17, 8); g.fill();               // wrist/forearm
    g.restore();
  };
  P.mix = mixColor; P.shade = shade; P.rgba = rgba; P.clamp = clamp; P.lerp = lerp;
})();
