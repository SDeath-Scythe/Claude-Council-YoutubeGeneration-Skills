/* Props (world objects), held items (drawn at a hand), and insert shots (full-frame close-ups).
   World props: SF.props.name(g, x, y, s, st, P, t) — (x,y) is the bottom-centre resting point, set scale.
   Held items:  SF.held.name(g, hx, hy, ang, s, o) — drawn at the hand centre.
   Inserts:     SF.inserts.name(g, t, S, st) — draws a whole 1920x1080 close-up composition. */
(function () {
  const SF = window.SF;
  const { clamp, lerp, rgba, shade, mixColor, ev } = SF;
  const P = SF.paint;
  const FONT = () => SF.FONTS;
  const props = (SF.props = {});
  const held = (SF.held = {});
  const inserts = (SF.inserts = {});

  // ---------- phone screens (shared by world phone, held phone and the insert) ----------
  /** draw a phone screen UI into rect (x,y,w,h). st.screen: lock|alarm|chat|feed|timer|call|note|stats|home|off */
  function phoneScreen(g, x, y, w, h, st = {}, t = 0) {
    const r = w * 0.09;
    g.save(); P.rrPath(g, x, y, w, h, r); g.clip();
    const kind = st.screen || 'lock';
    const dark = st.dark !== false;
    const bg = st.bg || (kind === 'alarm' ? ['#20304f', '#16213a'] : kind === 'call' ? ['#1f3b34', '#132620'] : dark ? ['#1b2232', '#0f141f'] : ['#eef1f5', '#dfe4ea']);
    g.fillStyle = P.lin(g, 0, y, 0, y + h, [[0, bg[0]], [1, bg[1]]]); g.fillRect(x, y, w, h);
    const fg = dark ? '#f3f5f8' : '#1d2330', sub = dark ? 'rgba(235,240,248,0.62)' : 'rgba(30,36,48,0.6)';
    const U = w / 100; // 1% of width
    const T = (s, px, py, size, o = {}) => P.text(g, s, x + px * U, y + py * U, Object.assign({ size: size * U, color: fg, font: FONT().ui, weight: 600 }, o));
    if (kind === 'off') { g.fillStyle = '#07090c'; g.fillRect(x, y, w, h); g.restore(); return; }
    if (kind === 'lock' || kind === 'alarm') {
      if (st.date) T(st.date, 50, 30, 6.2, { weight: 500, color: sub });
      T(st.time || '5:30', 50, 50, 25, { weight: 300 + (kind === 'alarm' ? 300 : 0) });
      if (kind === 'alarm') {
        if (st.label) T(st.label, 50, 70, 6.8, { weight: 700, spacing: 1.5, color: 'rgba(225,232,245,0.85)' });
        const pressed = st.pressed === 'snooze' ? clamp(1 - Math.abs((t - (st.pressAt || 1e9)) * 5)) : 0;
        P.rr(g, x + 14 * U, y + 100 * U, 72 * U, 18 * U, 9 * U, mixColor('#e9edf3', '#b9c3d3', pressed));
        T(st.snooze || 'SNOOZE', 50, 109, 7.6, { color: '#1d2433', weight: 700 });
        P.rr(g, x + 30 * U, y + 126 * U, 40 * U, 11 * U, 5.5 * U, null, 'rgba(220,228,240,0.55)', 0.8 * U);
        T(st.stop || 'STOP', 50, 131.5, 5.2, { color: 'rgba(225,232,245,0.8)', weight: 700 });
      } else if (st.notes) {
        let ny = 82;
        for (const n of st.notes.slice(0, 4)) {
          P.rr(g, x + 6 * U, y + ny * U, 88 * U, 17 * U, 4 * U, dark ? 'rgba(255,255,255,0.13)' : 'rgba(0,0,0,0.06)');
          P.rr(g, x + 9 * U, y + (ny + 3.5) * U, 10 * U, 10 * U, 2.5 * U, n.color || '#4f8ef0');
          T(n.app || 'Messages', 24, ny + 5.5, 3.6, { align: 'left', color: sub, weight: 600 });
          T(n.text || '', 24, ny + 11.5, 4.4, { align: 'left', weight: 600, maxW: 66 * U });
          ny += 20;
        }
      }
    } else if (kind === 'chat') {
      T(st.title || 'Mom', 50, 12, 5.5, { weight: 700 });
      P.line(g, x, y + 19 * U, x + w, y + 19 * U, sub, 0.4 * U);
      let cy = 26;
      const msgs = st.msgs || [];
      const shown = st.reveal !== undefined ? Math.floor(st.reveal) : msgs.length;
      for (let i = 0; i < Math.min(shown, msgs.length); i++) {
        const m = msgs[i]; const me = m.me;
        const lines = P.wrap(g, m.text, 58 * U, 4.6 * U, 500, FONT().ui);
        const bh = (lines.length * 6.4 + 5) * U, bw = Math.min(66 * U, Math.max(...lines.map((l) => P.measure(g, l, 4.6 * U, 500, FONT().ui))) + 9 * U);
        const bx = me ? x + w - 5 * U - bw : x + 5 * U;
        P.rr(g, bx, y + cy * U, bw, bh, 4.5 * U, me ? (st.meColor || '#3b82f6') : dark ? '#2c3445' : '#ffffff');
        lines.forEach((l, j) => P.text(g, l, bx + 4.5 * U, y + (cy + 5.6 + j * 6.4) * U, { size: 4.6 * U, weight: 500, align: 'left', color: me ? '#fff' : fg }));
        cy += bh / U + 4;
        if (m.read && i === shown - 1) T('Read ' + m.read, me ? 92 : 8, cy, 3.2, { align: me ? 'right' : 'left', color: sub, weight: 500 });
      }
      if (st.typing) { const k = Math.floor(t * 3) % 3; P.rr(g, x + 5 * U, y + cy * U, 20 * U, 9 * U, 4.5 * U, dark ? '#2c3445' : '#fff'); for (let i = 0; i < 3; i++) P.circle(g, x + (10 + i * 5) * U, y + (cy + 4.5) * U, 1.3 * U, i === k ? fg : sub); }
    } else if (kind === 'feed') {
      const off = (st.scroll || 0) * U;
      const cols = ['#c98f6b', '#6f9ac9', '#9c7fc2', '#71b08d', '#d1b360', '#c7707a'];
      for (let i = -1; i < 9; i++) {
        const py = y + 8 * U + i * 74 * U - (off % (74 * U));
        const idx = Math.floor((off) / (74 * U)) + i;
        P.circle(g, x + 9 * U, py + 5 * U, 3.5 * U, shade(cols[((idx % 6) + 6) % 6], -0.2));
        P.rr(g, x + 15 * U, py + 2.5 * U, 30 * U, 2.6 * U, 1.3 * U, sub);
        P.rr(g, x + 4 * U, py + 11 * U, 92 * U, 52 * U, 2 * U, cols[((idx % 6) + 6) % 6]);
        P.circle(g, x + 70 * U, py + 30 * U, 9 * U, rgba('#ffffff', 0.25));
        P.rr(g, x + 4 * U, py + 66 * U, 50 * U, 2.6 * U, 1.3 * U, sub);
      }
    } else if (kind === 'timer') {
      const left = st.seconds !== undefined ? st.seconds : 60;
      const mm = String(Math.floor(left / 60)).padStart(1, '0'), ss = String(Math.floor(left % 60)).padStart(2, '0');
      g.beginPath(); g.arc(x + 50 * U, y + 70 * U, 34 * U, 0, Math.PI * 2); g.strokeStyle = 'rgba(255,255,255,0.15)'; g.lineWidth = 3 * U; g.stroke();
      const frac = st.total ? left / st.total : 1;
      g.beginPath(); g.arc(x + 50 * U, y + 70 * U, 34 * U, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * frac); g.strokeStyle = st.accent || '#f2a73b'; g.lineWidth = 3 * U; g.lineCap = 'round'; g.stroke();
      T(mm + ':' + ss, 50, 70, 15, { weight: 300 });
      if (st.label) T(st.label, 50, 120, 6, { weight: 700, spacing: 1 });
    } else if (kind === 'call') {
      T(st.name || 'Mom', 50, 40, 9, { weight: 600 }); T(st.status || 'calling…', 50, 52, 4.8, { weight: 500, color: sub });
      P.circle(g, x + 25 * U, y + 150 * U, 9 * U, '#e5484d'); P.circle(g, x + 75 * U, y + 150 * U, 9 * U, '#30a46c');
    } else if (kind === 'stats') {
      T(st.title || 'Screen Time', 50, 18, 6, { weight: 700 });
      T(st.value || '9h 42m', 50, 36, 13, { weight: 700 });
      const bars = st.bars || [3, 5, 4, 7, 6, 9, 8];
      bars.forEach((b, i) => P.rr(g, x + (12 + i * 11) * U, y + (110 - b * 7) * U, 7 * U, b * 7 * U, 1.5 * U, st.accent || '#4f8ef0'));
    } else if (kind === 'note') {
      T(st.title || 'Notes', 8, 12, 6, { align: 'left', weight: 700 });
      (st.lines || []).forEach((l, i) => T(l, 8, 26 + i * 9, 5, { align: 'left', weight: 500 }));
    } else if (kind === 'home') {
      const cols = ['#e86b5a', '#f2b84b', '#4fb38a', '#4f8ef0', '#9a6ff0', '#ec6ba8', '#5ac8d8', '#8a96a8'];
      for (let i = 0; i < 16; i++) P.rr(g, x + (9 + (i % 4) * 22) * U, y + (24 + Math.floor(i / 4) * 26) * U, 15 * U, 15 * U, 4 * U, cols[i % 8]);
      T(st.time || '9:41', 50, 10, 4.6, { weight: 600 });
    }
    if (st.custom) st.custom(g, x, y, w, h, t);
    g.restore();
  }
  SF.phoneScreen = phoneScreen;

  // ---------- held items ----------
  held.phone = (g, hx, hy, ang, s, o) => {
    const glow = o.screen !== 'off';
    g.save(); g.translate(hx, hy); g.rotate((o.tilt || 0) * Math.PI / 180);
    const w = 15 * s, h = 29 * s;
    if (glow && o.view !== 'back') P.glow(g, 0, -h * 0.4, 60 * s, o.glowColor || '#bcd7ff', o.glowA || 0.55);
    P.rr(g, -w / 2, -h * 0.85, w, h, 3 * s, '#15171c', 'rgba(140,150,165,0.6)', 1);
    if (glow) P.rr(g, -w / 2 + 1.5 * s, -h * 0.85 + 1.5 * s, w - 3 * s, h - 3 * s, 2.2 * s, o.screenColor || '#a9c8f5');
    g.restore();
  };
  held.mug = (g, hx, hy, ang, s, o) => { P.rr(g, hx - 8 * s, hy - 14 * s, 16 * s, 18 * s, 3 * s, o.color || '#e9e4da', 'rgba(0,0,0,0.25)', 1); if (o.steam !== false) SF.fx && SF.fx.steamPuff && SF.fx.steamPuff(g, hx, hy - 16 * s, s, o.t || 0); };
  held.paper = (g, hx, hy, ang, s, o) => { g.save(); g.translate(hx, hy); g.rotate(-0.1); P.rect(g, -14 * s, -36 * s, 28 * s, 36 * s, o.color || '#f4f2ec'); for (let i = 0; i < 4; i++) P.line(g, -10 * s, (-30 + i * 7) * s, 10 * s, (-30 + i * 7) * s, 'rgba(60,70,90,0.45)', 1.2 * s); g.restore(); };
  held.book = (g, hx, hy, ang, s, o) => { P.rr(g, hx - 14 * s, hy - 10 * s, 28 * s, 20 * s, 2 * s, o.color || '#7b4f3a', 'rgba(0,0,0,0.35)', 1); P.rect(g, hx - 12 * s, hy - 8 * s, 2 * s, 16 * s, 'rgba(255,255,255,0.25)'); };
  held.box = (g, hx, hy, ang, s, o) => { P.rr(g, hx - 26 * s, hy - 16 * s, 52 * s, 26 * s, 2 * s, o.color || '#9aa3ad', 'rgba(0,0,0,0.3)', 1); P.rect(g, hx - 26 * s, hy - 16 * s, 52 * s, 6 * s, shade(o.color || '#9aa3ad', 0.25)); };
  held.bag = (g, hx, hy, ang, s, o) => { P.rr(g, hx - 15 * s, hy + 4 * s, 30 * s, 30 * s, 4 * s, o.color || '#c8b49a', 'rgba(0,0,0,0.3)', 1); P.path(g, [[hx - 8 * s, hy + 6 * s], [hx - 6 * s, hy - 4 * s], [hx + 6 * s, hy - 4 * s], [hx + 8 * s, hy + 6 * s]], 'rgba(60,50,40,0.8)', 2 * s); };
  held.umbrella = (g, hx, hy, ang, s, o) => { P.line(g, hx, hy, hx, hy - 120 * s, '#1b1b1f', 3 * s); g.beginPath(); g.moveTo(hx - 70 * s, hy - 110 * s); g.quadraticCurveTo(hx, hy - 190 * s, hx + 70 * s, hy - 110 * s); g.closePath(); g.fillStyle = o.color || '#2f3b52'; g.fill(); };
  held.ball = (g, hx, hy, ang, s, o) => { P.circle(g, hx, hy - 4 * s, 15 * s, o.color || '#d9772f', 'rgba(0,0,0,0.4)', 1); P.line(g, hx - 15 * s, hy - 4 * s, hx + 15 * s, hy - 4 * s, 'rgba(0,0,0,0.45)', 1.2 * s); };
  held.flower = (g, hx, hy, ang, s, o) => { P.line(g, hx, hy, hx + 4 * s, hy - 40 * s, '#4f7a45', 2 * s); for (let i = 0; i < 5; i++) { const a = i * 1.256; P.circle(g, hx + 4 * s + Math.cos(a) * 6 * s, hy - 42 * s + Math.sin(a) * 6 * s, 5 * s, o.color || '#e46f7a'); } P.circle(g, hx + 4 * s, hy - 42 * s, 4 * s, '#f2c95b'); };
  held.bottle = (g, hx, hy, ang, s, o) => { P.rr(g, hx - 6 * s, hy - 30 * s, 12 * s, 34 * s, 4 * s, o.color || 'rgba(170,205,235,0.85)'); P.rect(g, hx - 4 * s, hy - 36 * s, 8 * s, 7 * s, '#3c6fb0'); };
  held.pen = (g, hx, hy, ang, s, o) => { g.save(); g.translate(hx, hy); g.rotate(ang - 0.6); P.rr(g, -2 * s, -2 * s, 26 * s, 4 * s, 2 * s, o.color || '#2d4f8f'); g.restore(); };

  // ---------- world props ----------
  props.phone = (g, x, y, s = 1, st = {}, Pa, t = 0) => {
    const w = 34 * s, h = 64 * s;
    if (st.flat) { // lying on a surface, seen at an angle
      g.save(); g.translate(x, y); g.scale(1, 0.32); P.rr(g, -h / 2, -w, h, w * 2, 6 * s, '#15171c'); if (st.screen !== 'off') { P.rr(g, -h / 2 + 3 * s, -w + 3 * s, h - 6 * s, w * 2 - 6 * s, 4 * s, st.screenColor || '#9fc0ef'); } g.restore();
      if (st.screen !== 'off') P.glow(g, x, y - 6 * s, 90 * s, '#a8c6ff', st.glowA || 0.35);
      return;
    }
    P.rr(g, x - w / 2, y - h, w, h, 6 * s, '#16181d');
    phoneScreen(g, x - w / 2 + 2.5 * s, y - h + 2.5 * s, w - 5 * s, h - 5 * s, st, t);
  };
  props.alarmClock = (g, x, y, s = 1, st = {}, Pa, t = 0) => {
    const w = 70 * s, h = 40 * s;
    P.rr(g, x - w / 2, y - h, w, h, 10 * s, st.color || '#2a2e36');
    P.rr(g, x - w / 2 + 6 * s, y - h + 7 * s, w - 12 * s, h - 15 * s, 5 * s, '#0f1216');
    const blink = st.ringing ? (Math.floor(t * 4) % 2) : 1;
    if (blink) { P.text(g, st.time || '5:30', x, y - h / 2 - 1 * s, { size: 19 * s, color: st.digit || '#ff6b55', font: FONT().ui, weight: 700 }); P.glow(g, x, y - h / 2, 70 * s, st.digit || '#ff6b55', 0.25); }
    if (st.ringing) { const k = Math.sin(t * 50) * 2 * s; g.save(); g.translate(k, 0); g.restore(); }
  };
  props.mug = (g, x, y, s = 1, st = {}, Pa, t = 0) => {
    P.shadow(g, x, y, 26 * s, 5 * s, 0.25);
    P.rr(g, x - 18 * s, y - 40 * s, 36 * s, 40 * s, 6 * s, st.color || '#e8e2d6');
    g.beginPath(); g.arc(x + 20 * s, y - 22 * s, 10 * s, -Math.PI / 2, Math.PI / 2); g.strokeStyle = st.color || '#e8e2d6'; g.lineWidth = 5 * s; g.stroke();
    P.ell(g, x, y - 40 * s, 18 * s, 4 * s, shade(st.color || '#e8e2d6', -0.25));
    if (st.steam !== false && SF.fx) SF.fx.steamPuff(g, x, y - 46 * s, s, t);
  };
  props.laptop = (g, x, y, s = 1, st = {}, Pa, t = 0) => {
    const w = 190 * s, h = 120 * s;
    P.poly(g, [[x - w * 0.55, y], [x + w * 0.55, y], [x + w * 0.48, y - 12 * s], [x - w * 0.48, y - 12 * s]], '#9aa1ab');
    P.rr(g, x - w / 2, y - 12 * s - h, w, h, 7 * s, '#2a2f38');
    const on = st.on !== false;
    P.rr(g, x - w / 2 + 7 * s, y - 12 * s - h + 7 * s, w - 14 * s, h - 14 * s, 3 * s, on ? (st.screenColor || '#c9daf2') : '#14181e');
    if (on) {
      for (let i = 0; i < 6; i++) P.rr(g, x - w / 2 + 18 * s, y - h + (10 + i * 15) * s, (w - 50 * s) * (0.5 + 0.5 * SF.rnd(i, 3)), 6 * s, 3 * s, 'rgba(60,80,120,0.35)');
      P.glow(g, x, y - h * 0.6, 220 * s, st.glowColor || '#b9d3ff', st.glowA === undefined ? 0.35 : st.glowA);
    }
  };
  props.lamp = (g, x, y, s = 1, st = {}, Pa, t = 0) => { // desk lamp
    const on = st.on !== false;
    P.ell(g, x, y - 4 * s, 34 * s, 8 * s, st.color || '#2e3138');
    P.line(g, x, y - 6 * s, x + 10 * s, y - 110 * s, st.color || '#2e3138', 6 * s);
    P.poly(g, [[x - 20 * s, y - 100 * s], [x + 45 * s, y - 140 * s], [x + 60 * s, y - 110 * s], [x + 5 * s, y - 86 * s]], st.color || '#2e3138');
    if (on) { P.cone(g, x + 32 * s, y - 100 * s, 115, 70, 330 * s, (Pa && Pa.light) || '#ffd48e', 0.28); P.glow(g, x + 32 * s, y - 100 * s, 160 * s, (Pa && Pa.light) || '#ffd48e', 0.55); }
  };
  props.floorLamp = (g, x, y, s = 1, st = {}, Pa) => {
    const on = st.on !== false, c = st.color || '#2e3138';
    P.ell(g, x, y - 4 * s, 40 * s, 8 * s, c); P.line(g, x, y, x, y - 380 * s, c, 6 * s);
    P.poly(g, [[x - 55 * s, y - 330 * s], [x + 55 * s, y - 330 * s], [x + 38 * s, y - 410 * s], [x - 38 * s, y - 410 * s]], st.shade || '#e9dcc4');
    if (on) { P.glow(g, x, y - 360 * s, 330 * s, (Pa && Pa.light) || '#ffd48e', 0.6); P.cone(g, x, y - 330 * s, 90, 80, 420 * s, (Pa && Pa.light) || '#ffd48e', 0.18); }
  };
  props.books = (g, x, y, s = 1, st = {}) => {
    const cols = st.colors || ['#7b4f3a', '#3f5a7a', '#8a7a4f', '#5b6e57'];
    let yy = y;
    for (let i = 0; i < (st.n || 4); i++) { const w = (70 + 14 * SF.rnd(i, 5)) * s, h = 13 * s; P.rr(g, x - w / 2 + (SF.rnd(i, 9) - 0.5) * 10 * s, yy - h, w, h, 2 * s, cols[i % cols.length]); yy -= h + 1 * s; }
  };
  props.plant = (g, x, y, s = 1, st = {}, Pa) => {
    const green = st.color || (Pa && Pa.green) || '#6f9a59';
    P.poly(g, [[x - 34 * s, y - 70 * s], [x + 34 * s, y - 70 * s], [x + 26 * s, y], [x - 26 * s, y]], st.pot || '#c9b8a3');
    for (let i = 0; i < 9; i++) {
      const a = -Math.PI / 2 + (i - 4) * 0.28, L = (70 + 50 * SF.rnd(i, 4)) * s;
      g.save(); g.translate(x, y - 70 * s); g.rotate(a + Math.PI / 2);
      P.ell(g, 0, -L / 2, 13 * s, L / 2, shade(green, (SF.rnd(i, 2) - 0.5) * 0.3)); g.restore();
    }
  };
  props.calendar = (g, x, y, s = 1, st = {}, Pa, t = 0) => { // y = bottom of the sheet
    const w = 200 * s, h = 250 * s;
    P.rect(g, x - w / 2 + 6 * s, y - h + 8 * s, w, h, 'rgba(0,0,0,0.18)');
    P.rect(g, x - w / 2, y - h, w, h, st.paper || '#f2f2ef');
    P.text(g, st.title || 'PLAN', x, y - h + 24 * s, { size: 22 * s, weight: 800, color: '#2b2f36', maxW: w - 20 * s });
    P.line(g, x - w / 2 + 14 * s, y - h + 42 * s, x + w / 2 - 14 * s, y - h + 42 * s, '#2b2f36', 2 * s);
    const cols = 7, rows = st.rows || 4, cw = (w - 28 * s) / cols, chh = (h - 64 * s) / rows;
    const crossed = st.crossed === undefined ? 0 : st.crossed;
    const tint = ['#7e9fbf', '#8fb0a5', '#a29bbf', '#8aa7c4'];
    for (let i = 0; i < cols * rows; i++) {
      const cx = x - w / 2 + 14 * s + (i % cols) * cw, cy = y - h + 52 * s + Math.floor(i / cols) * chh;
      P.rr(g, cx + 2 * s, cy + 2 * s, cw - 4 * s, chh - 4 * s, 2 * s, rgba(tint[i % 4], 0.75));
      const k = clamp(crossed - i);
      if (k > 0) {
        const c = st.mark || '#d6453d', lw = 3.2 * s;
        const k1 = clamp(k * 2), k2 = clamp(k * 2 - 1);
        P.line(g, cx + 4 * s, cy + 4 * s, lerp(cx + 4 * s, cx + cw - 4 * s, k1), lerp(cy + 4 * s, cy + chh - 4 * s, k1), c, lw);
        if (k2 > 0) P.line(g, cx + cw - 4 * s, cy + 4 * s, lerp(cx + cw - 4 * s, cx + 4 * s, k2), lerp(cy + 4 * s, cy + chh - 4 * s, k2), c, lw);
      }
      if (st.check && i < (st.checked || 0)) P.path(g, [[cx + cw * 0.22, cy + chh * 0.55], [cx + cw * 0.42, cy + chh * 0.75], [cx + cw * 0.8, cy + chh * 0.28]], st.checkColor || '#3d9a5b', 3.4 * s);
    }
    P.circle(g, x - w / 2 + 16 * s, y - h + 8 * s, 6 * s, '#7a8fa3'); P.circle(g, x + w / 2 - 16 * s, y - h + 8 * s, 6 * s, '#7a8fa3');
  };
  props.clock = (g, x, y, s = 1, st = {}, Pa, t = 0) => { // wall clock, (x,y) = centre
    const r = 46 * s;
    P.circle(g, x + 4 * s, y + 5 * s, r + 4 * s, 'rgba(0,0,0,0.18)');
    P.circle(g, x, y, r + 4 * s, st.rim || '#2c3038'); P.circle(g, x, y, r, st.face || '#f2f1ec');
    for (let i = 0; i < 12; i++) { const a = (i / 12) * Math.PI * 2; P.line(g, x + Math.cos(a) * r * 0.8, y + Math.sin(a) * r * 0.8, x + Math.cos(a) * r * 0.92, y + Math.sin(a) * r * 0.92, '#2c3038', 2.5 * s); }
    const hours = st.hours !== undefined ? st.hours : 2.23; // decimal hours
    const ha = (hours / 12) * Math.PI * 2 - Math.PI / 2, ma = ((hours % 1) * Math.PI * 2) - Math.PI / 2;
    P.line(g, x, y, x + Math.cos(ha) * r * 0.5, y + Math.sin(ha) * r * 0.5, '#1d2027', 5 * s);
    P.line(g, x, y, x + Math.cos(ma) * r * 0.78, y + Math.sin(ma) * r * 0.78, '#1d2027', 3.5 * s);
    P.circle(g, x, y, 4 * s, '#c9463d');
  };
  props.poster = (g, x, y, s = 1, st = {}) => { // (x,y) = centre
    const w = (st.w || 120) * s, h = (st.h || 160) * s;
    P.rect(g, x - w / 2 + 5 * s, y - h / 2 + 6 * s, w, h, 'rgba(0,0,0,0.18)');
    P.rect(g, x - w / 2, y - h / 2, w, h, st.frame || '#2b2f36');
    P.rect(g, x - w / 2 + 7 * s, y - h / 2 + 7 * s, w - 14 * s, h - 14 * s, st.bg || '#e9e5dc');
    if (st.icon === 'runner') { // simple running figure pictogram
      const c = st.ink || '#2b2f36', cx = x, cy = y;
      P.circle(g, cx + 6 * s, cy - 34 * s, 8 * s, c);
      P.path(g, [[cx + 2 * s, cy - 24 * s], [cx - 4 * s, cy + 4 * s]], c, 6 * s);
      P.path(g, [[cx - 4 * s, cy + 4 * s], [cx + 12 * s, cy + 20 * s], [cx + 8 * s, cy + 40 * s]], c, 5 * s);
      P.path(g, [[cx - 4 * s, cy + 4 * s], [cx - 18 * s, cy + 22 * s], [cx - 34 * s, cy + 22 * s]], c, 5 * s);
      P.path(g, [[cx + 1 * s, cy - 18 * s], [cx + 18 * s, cy - 8 * s], [cx + 24 * s, cy - 20 * s]], c, 4.5 * s);
      P.path(g, [[cx + 1 * s, cy - 18 * s], [cx - 14 * s, cy - 12 * s], [cx - 20 * s, cy + 2 * s]], c, 4.5 * s);
    } else if (st.icon === 'mountain') {
      P.poly(g, [[x - w / 2 + 7 * s, y + h / 2 - 7 * s], [x - 10 * s, y - 20 * s], [x + 10 * s, y + 5 * s], [x + 25 * s, y - 10 * s], [x + w / 2 - 7 * s, y + h / 2 - 7 * s]], st.ink || '#7f97a8');
    } else if (st.text) P.text(g, st.text, x, y, { size: (st.size || 22) * s, weight: 800, color: st.ink || '#2b2f36', maxW: w - 24 * s });
  };
  props.shoes = (g, x, y, s = 1, st = {}, Pa) => { // a pair of sneakers seen from the side, (x,y) floor contact
    const c = st.color || '#5f7d99', sole = st.sole || '#eef0f2';
    for (const dx of [-14 * s, 18 * s]) {
      const X = x + dx, Y = y - (dx > 0 ? 0 : 3 * s);
      P.shadow(g, X, Y + 2 * s, 70 * s, 8 * s, 0.25);
      P.rr(g, X - 62 * s, Y - 14 * s, 124 * s, 14 * s, 7 * s, sole);
      g.beginPath(); g.moveTo(X - 60 * s, Y - 12 * s); g.lineTo(X - 52 * s, Y - 44 * s); g.lineTo(X - 20 * s, Y - 48 * s); g.lineTo(X + 10 * s, Y - 34 * s); g.quadraticCurveTo(X + 60 * s, Y - 26 * s, X + 62 * s, Y - 12 * s); g.closePath(); g.fillStyle = c; g.fill();
      P.poly(g, [[X - 40 * s, Y - 20 * s], [X + 30 * s, Y - 24 * s], [X - 10 * s, Y - 36 * s]], shade(c, 0.28));
      for (let i = 0; i < 4; i++) P.line(g, X - 18 * s + i * 7 * s, Y - 44 * s + i * 3 * s, X - 10 * s + i * 7 * s, Y - 41 * s + i * 3 * s, '#f4f5f7', 2.4 * s);
    }
    if (st.tag) { P.rr(g, x + 40 * s, y - 20 * s, 18 * s, 24 * s, 3 * s, '#f1f1ee'); P.line(g, x + 46 * s, y - 20 * s, x + 30 * s, y - 34 * s, '#d8d8d4', 1.2 * s); }
  };
  props.shoebox = (g, x, y, s = 1, st = {}) => {
    const w = 130 * s, h = 52 * s, c = st.color || '#7f8d9b';
    P.shadow(g, x, y, w * 0.6, 7 * s, 0.25);
    P.rect(g, x - w / 2, y - h, w, h, c); P.rect(g, x - w / 2 - 4 * s, y - h - 10 * s, w + 8 * s, 14 * s, shade(c, 0.2));
    if (st.logo !== false) { g.save(); g.translate(x, y - h / 2); P.path(g, [[-14 * s, 4 * s], [-4 * s, -6 * s], [14 * s, -6 * s]], '#eef0f2', 3 * s); g.restore(); }
  };
  props.paperBall = (g, x, y, s = 1, st = {}) => {
    P.shadow(g, x, y, 30 * s, 5 * s, 0.25);
    const r = 24 * s; g.beginPath();
    for (let i = 0; i < 12; i++) { const a = (i / 12) * Math.PI * 2; const rr = r * (0.8 + 0.3 * SF.rnd(i, 11)); i ? g.lineTo(x + Math.cos(a) * rr, y - r + Math.sin(a) * rr) : g.moveTo(x + Math.cos(a) * rr, y - r + Math.sin(a) * rr); }
    g.closePath(); g.fillStyle = st.color || '#e9e8e4'; g.fill();
    for (let i = 0; i < 5; i++) P.line(g, x - r * 0.5 + SF.rnd(i, 3) * r, y - r * 1.5 + SF.rnd(i, 4) * r, x - r * 0.4 + SF.rnd(i, 5) * r, y - r * 0.7 + SF.rnd(i, 6) * r * 0.6, i % 2 ? 'rgba(214,69,61,0.8)' : 'rgba(120,130,140,0.6)', 2 * s);
  };
  props.trophy = (g, x, y, s = 1, st = {}) => { const c = st.color || '#e2b33d'; P.rr(g, x - 30 * s, y - 16 * s, 60 * s, 16 * s, 3 * s, '#4a3b2a'); P.rect(g, x - 6 * s, y - 50 * s, 12 * s, 34 * s, c); g.beginPath(); g.moveTo(x - 34 * s, y - 110 * s); g.lineTo(x + 34 * s, y - 110 * s); g.quadraticCurveTo(x + 30 * s, y - 50 * s, x, y - 48 * s); g.quadraticCurveTo(x - 30 * s, y - 50 * s, x - 34 * s, y - 110 * s); g.fillStyle = c; g.fill(); P.glow(g, x, y - 80 * s, 120 * s, '#ffe2a0', 0.3); };
  props.trash = (g, x, y, s = 1, st = {}) => { P.poly(g, [[x - 36 * s, y - 90 * s], [x + 36 * s, y - 90 * s], [x + 28 * s, y], [x - 28 * s, y]], st.color || '#6f7781'); for (let i = -2; i <= 2; i++) P.line(g, x + i * 12 * s, y - 80 * s, x + i * 9 * s, y - 8 * s, 'rgba(0,0,0,0.18)', 3 * s); };
  props.bottle = (g, x, y, s = 1, st = {}) => { P.rr(g, x - 12 * s, y - 70 * s, 24 * s, 70 * s, 8 * s, st.color || 'rgba(170,205,235,0.8)'); P.rect(g, x - 8 * s, y - 82 * s, 16 * s, 14 * s, '#3c6fb0'); };
  props.photo = (g, x, y, s = 1, st = {}) => { const w = 90 * s, h = 70 * s; P.rect(g, x - w / 2, y - h, w, h, st.frame || '#3a3f48'); P.rect(g, x - w / 2 + 6 * s, y - h + 6 * s, w - 12 * s, h - 12 * s, st.bg || '#c8d6e2'); P.circle(g, x - 14 * s, y - h / 2 - 2 * s, 9 * s, '#2a2e35'); P.rr(g, x - 24 * s, y - h / 2 + 6 * s, 20 * s, 18 * s, 6 * s, '#2a2e35'); P.circle(g, x + 12 * s, y - h / 2, 8 * s, '#2a2e35'); P.rr(g, x + 3 * s, y - h / 2 + 7 * s, 18 * s, 16 * s, 6 * s, '#2a2e35'); };
  props.ball = (g, x, y, s = 1, st = {}) => { P.shadow(g, x, y, 34 * s, 6 * s, 0.25); P.circle(g, x, y - 30 * s, 30 * s, st.color || '#d9772f'); P.line(g, x - 30 * s, y - 30 * s, x + 30 * s, y - 30 * s, 'rgba(0,0,0,0.45)', 2 * s); g.beginPath(); g.arc(x, y - 30 * s, 30 * s, -0.5, 0.5); g.strokeStyle = 'rgba(0,0,0,0.45)'; g.stroke(); };
  props.gift = (g, x, y, s = 1, st = {}) => { const c = st.color || '#c8545b'; P.rect(g, x - 40 * s, y - 60 * s, 80 * s, 60 * s, c); P.rect(g, x - 6 * s, y - 60 * s, 12 * s, 60 * s, st.ribbon || '#f2d27a'); P.ell(g, x - 14 * s, y - 66 * s, 14 * s, 8 * s, st.ribbon || '#f2d27a'); P.ell(g, x + 14 * s, y - 66 * s, 14 * s, 8 * s, st.ribbon || '#f2d27a'); };
  props.dumbbell = (g, x, y, s = 1, st = {}) => { P.rect(g, x - 40 * s, y - 14 * s, 80 * s, 8 * s, '#666b73'); for (const dx of [-44, 32]) P.rr(g, x + dx * s, y - 26 * s, 12 * s, 26 * s, 3 * s, '#2a2d33'); };
  props.guitar = (g, x, y, s = 1, st = {}) => { const c = st.color || '#b0773f'; P.ell(g, x, y - 60 * s, 46 * s, 56 * s, c); P.ell(g, x, y - 128 * s, 34 * s, 38 * s, c); P.circle(g, x, y - 100 * s, 12 * s, '#2a1d14'); P.rect(g, x - 5 * s, y - 280 * s, 10 * s, 160 * s, '#3b2a1e'); };


  /** houseplant whose look follows st.health (0 wilted .. 1 lush) and st.bloom (0..1 flowers) — a progress device */
  props.houseplant = (g, x, y, s = 1, st = {}, Pa, t = 0) => {
    const h = clamp(st.health === undefined ? 1 : st.health), bl = clamp(st.bloom || 0);
    const leaf = SF.mixColor(st.dry || '#a08a5a', st.color || (Pa && Pa.green) || '#6f9a59', h);
    P.shadow(g, x, y, 60 * s, 9 * s, 0.25);
    P.poly(g, [[x - 46 * s, y - 92 * s], [x + 46 * s, y - 92 * s], [x + 34 * s, y], [x - 34 * s, y]], st.pot || '#c98f6b');
    P.rect(g, x - 50 * s, y - 100 * s, 100 * s, 14 * s, shade(st.pot || '#c98f6b', -0.1));
    const n = 9;
    for (let i = 0; i < n; i++) {
      const side = i - (n - 1) / 2;
      const up = lerp(0.25, 1, h);                      // stems stand up as health rises
      const sway = Math.sin(t * 1.3 + i) * 0.03 * h;
      const a = -Math.PI / 2 + side * lerp(0.42, 0.2, h) + (1 - up) * Math.sign(side || 0.3) * 1.25 + sway;
      const L = (70 + 40 * SF.rnd(i, 4)) * s * lerp(0.75, 1.1, h);
      const ex = x + Math.cos(a) * L, ey = y - 100 * s + Math.sin(a) * L;
      P.line(g, x + side * 3 * s, y - 100 * s, ex, ey, shade(leaf, -0.25), 3.5 * s);
      g.save(); g.translate(ex, ey); g.rotate(a + Math.PI / 2 + (1 - h) * 0.6 * Math.sign(side || 1));
      P.ell(g, 0, 0, 13 * s * lerp(0.7, 1, h), 26 * s * lerp(0.7, 1, h), leaf); P.line(g, 0, -20 * s, 0, 20 * s, rgba('#ffffff', 0.18 * h), 1.5 * s); g.restore();
      if (bl > 0 && i % 2 === 0) {
        const k = clamp(bl * 1.4 - (i / n) * 0.4);
        if (k > 0) { for (let p = 0; p < 5; p++) { const pa = (p / 5) * Math.PI * 2 + t * 0.2; P.circle(g, ex + Math.cos(pa) * 9 * s * k, ey - 18 * s + Math.sin(pa) * 9 * s * k, 7 * s * k, st.flower || '#ec8fa3'); } P.circle(g, ex, ey - 18 * s, 5 * s * k, '#f6d26b'); }
      }
    }
  };

  // ---------- inserts (close-up shots) ----------
  /** shared insert backdrop: a soft surface with vignette; st.surface: desk|bed|floor|wall|fridge|dark */
  function backdrop(g, S, st) {
    const Pa = S.P; const kind = st.surface || 'desk';
    const c0 = st.bg || (kind === 'bed' ? Pa.furn2 : kind === 'floor' ? Pa.floor : kind === 'fridge' ? Pa.furn : kind === 'dark' ? Pa.dark : Pa.furn2);
    g.fillStyle = P.lin(g, 0, 0, 0, 1080, [[0, shade(c0, 0.06)], [1, shade(c0, -0.25)]]); g.fillRect(-200, -200, 2320, 1480);
    if (kind === 'desk' || kind === 'floor') for (let i = 0; i < 14; i++) P.rect(g, -200, -200 + i * 110, 2320, 3, rgba('#000000', 0.06));
    if (kind === 'bed') for (let i = 0; i < 7; i++) { g.beginPath(); g.moveTo(-200, 120 + i * 170); g.bezierCurveTo(500, 60 + i * 170, 1300, 200 + i * 170, 2200, 100 + i * 170); g.strokeStyle = rgba('#000000', 0.07); g.lineWidth = 26; g.stroke(); }
    P.glow(g, 960, 470, 900, Pa.light || '#ffffff', 0.18, 'screen');
  }
  inserts.phone = (g, t, S, st = {}) => {
    backdrop(g, S, st);
    const w = st.w || 430, h = w * 2.05;
    const x = (st.x === undefined ? 960 : st.x), y = (st.y === undefined ? 560 : st.y);
    g.save(); g.translate(x, y); g.rotate(((st.tilt === undefined ? 6 : st.tilt) * Math.PI) / 180);
    P.rr(g, -w / 2 + 16, -h / 2 + 22, w, h, w * 0.12, 'rgba(0,0,0,0.35)');
    P.rr(g, -w / 2, -h / 2, w, h, w * 0.12, '#101217', 'rgba(150,160,175,0.6)', 3);
    phoneScreen(g, -w / 2 + 12, -h / 2 + 12, w - 24, h - 24, st, t);
    g.restore();
    if (st.glow !== false) P.glow(g, x, y, w * 1.6, '#9fc0ff', 0.25);
    if (st.hand) { // a silhouette hand tapping: st.hand = {x, y, ang, tapAt}
      const hd = st.hand; const tap = hd.tapAt !== undefined ? Math.max(0, 1 - Math.abs(t - hd.tapAt) * 6) : 0;
      P.handPoint(g, (hd.x || x + 180) - tap * 12, (hd.y || y + 260) + tap * 10, hd.ang === undefined ? -2.3 : hd.ang, hd.s || 3.2, S.P.ink);
    }
  };
  inserts.calendar = (g, t, S, st = {}) => {
    backdrop(g, S, Object.assign({ surface: 'fridge' }, st));
    props.calendar(g, st.x || 960, st.y || 1000, st.s || 3.4, st, S.P, t);
    if (st.hand) { const hd = st.hand; P.handPoint(g, hd.x || 1300, hd.y || 820, hd.ang === undefined ? -2.6 : hd.ang, hd.s || 3.6, S.P.ink); }
  };
  inserts.clock = (g, t, S, st = {}) => { backdrop(g, S, Object.assign({ surface: 'wall', bg: S.P.wall }, st)); props.clock(g, st.x || 960, st.y || 540, st.s || 8, st, S.P, t); };
  inserts.laptop = (g, t, S, st = {}) => {
    backdrop(g, S, st);
    const w = 1500, h = 900, x = 960 - w / 2, y = 90;
    P.rr(g, x - 30, y - 30, w + 60, h + 60, 30, '#20242b');
    P.rr(g, x, y, w, h, 10, st.bg || '#eef2f6');
    P.rect(g, x, y, w, 70, '#dfe5ec');
    P.text(g, st.title || 'Inbox (214)', x + 40, y + 36, { size: 34, align: 'left', color: '#2a3140', weight: 700 });
    const rows = st.rows || ['Re: urgent — need this tonight', 'Meeting moved to 7:00 AM', 'Reminder: deadline Friday', 'Can you jump on a quick call?', 'FWD: FWD: numbers'];
    rows.forEach((r, i) => { P.rr(g, x + 30, y + 100 + i * 120, w - 60, 100, 10, i === 0 ? '#ffffff' : '#f7f9fb'); P.circle(g, x + 90, y + 150 + i * 120, 26, ['#e07a5f', '#5f8fd0', '#77b28c', '#c9a14a', '#9a7fd0'][i % 5]); P.text(g, r, x + 140, y + 150 + i * 120, { size: 32, align: 'left', color: '#2a3140', weight: i === 0 ? 700 : 500 }); });
    P.glow(g, 960, 540, 1100, '#bcd5ff', 0.2);
  };
  inserts.note = (g, t, S, st = {}) => {
    backdrop(g, S, Object.assign({ surface: 'fridge' }, st));
    g.save(); g.translate(st.x || 960, st.y || 540); g.rotate(((st.tilt === undefined ? -3 : st.tilt) * Math.PI) / 180);
    P.rect(g, -330 + 14, -420 + 18, 660, 840, 'rgba(0,0,0,0.2)');
    P.rect(g, -330, -420, 660, 840, st.paper || '#f6f3ea');
    for (let i = 0; i < 12; i++) P.line(g, -300, -300 + i * 62, 300, -300 + i * 62, 'rgba(90,120,170,0.25)', 2);
    const lines = st.lines || [st.text || 'Start tomorrow.'];
    const reveal = st.reveal === undefined ? 1e9 : st.reveal;
    let shown = 0;
    lines.forEach((l, i) => { const n = clamp(reveal - shown, 0, l.length); shown += l.length; if (n > 0) P.text(g, l.slice(0, Math.floor(n)), -280, -330 + i * 62 + 20, { size: 48, align: 'left', font: SF.FONTS.hand, weight: 500, color: st.ink || '#28324a' }); });
    P.circle(g, 0, -400, 16, st.pin || '#d6453d');
    g.restore();
  };
  inserts.shoes = (g, t, S, st = {}) => { backdrop(g, S, Object.assign({ surface: 'floor' }, st)); props.shoes(g, st.x || 960, st.y || 760, st.s || 4.2, st, S.P, t); };


  /** close-up of any world prop: { type:'prop', prop:'houseplant', state:{...}, s:3, x, y, surface } */
  inserts.prop = (g, t, S, st = {}) => {
    backdrop(g, S, Object.assign({ surface: 'wall', bg: S.P.wall }, st));
    if (st.sill !== false) { P.rect(g, -200, (st.y || 900) - 6, 2320, 400, shade(S.P.trim, -0.08)); P.rect(g, -200, (st.y || 900) - 6, 2320, 10, rgba('#ffffff', 0.2)); }
    const fn = props[st.prop]; if (!fn) { SF.warn('prop', 'unknown prop "' + st.prop + '" in insert'); return; }
    fn(g, st.x || 960, st.y || 900, st.s || 3.2, SF.resolveState(st.state || {}, t), S.P, t);
  };

  SF.insertBackdrop = backdrop;
})();
