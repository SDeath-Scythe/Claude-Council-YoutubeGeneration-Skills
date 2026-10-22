/* Sets: lit, flat-vector environments with a consistent 2.5D model.
   World is 1920x1080 at camera rest. Interiors: horizon y=430, back wall meets floor at y=740, main standing line y=900.
   scaleAt(y) gives character scale for feet at y (1.85 on the standing line); zAt(y) gives depth for blur/order.
   A set returns { name, horizon, wallY, floorY, scaleAt, zAt, marks, layers:[{id,z,static,draw(g,t,Pa,view)}], lights(t,Pa), amb }.
   SF.build holds the pieces so films can compose new sets. */
(function () {
  const SF = window.SF;
  const { clamp, lerp, rgba, shade, mixColor, rnd } = SF;
  const P = SF.paint;
  const B = (SF.build = {});
  const sets = (SF.sets = {});

  const HOR = 430, WALL = 740, STAND = 900, SC = 1.85;
  B.persp = (horizon = HOR, standY = STAND, sc = SC) => (y) => Math.max(0.15, (sc * (y - horizon)) / (standY - horizon));
  B.depth = (standY = STAND, k = 80) => (y) => (standY - y) / k;
  const unit = (s) => 178 * s; // pixels per metre at scale s

  // ---------- skies ----------
  B.sky = (g, Pa, o = {}) => {
    const x0 = o.x0 === undefined ? -800 : o.x0, x1 = o.x1 === undefined ? 2720 : o.x1, y0 = o.y0 === undefined ? -400 : o.y0, y1 = o.y1 === undefined ? 900 : o.y1;
    g.fillStyle = P.lin(g, 0, y0, 0, y1, [[0, Pa.sky[0]], [1, Pa.sky[1]]]); g.fillRect(x0, y0, x1 - x0, y1 - y0);
    const tod = o.time || 'day';
    if (tod === 'night' || o.stars) for (let i = 0; i < 90; i++) { const x = x0 + rnd(i, 71) * (x1 - x0), y = y0 + rnd(i, 72) * (y1 - y0) * 0.6; P.circle(g, x, y, 1 + rnd(i, 73) * 1.6, rgba('#ffffff', 0.25 + rnd(i, 74) * 0.5)); }
    if (o.moon) { P.glow(g, o.moon[0], o.moon[1], 160, '#dfe8ff', 0.5); P.circle(g, o.moon[0], o.moon[1], 34, '#eef2ff'); }
    if (o.sun) { P.glow(g, o.sun[0], o.sun[1], o.sunR || 420, Pa.accent, 0.9, 'screen'); P.circle(g, o.sun[0], o.sun[1], 70, mixColor(Pa.light, '#ffffff', 0.4)); }
    if (o.clouds) for (let i = 0; i < 7; i++) { const cx = x0 + 300 + i * 520 + rnd(i, 81) * 200, cy = y0 + 220 + rnd(i, 82) * 260; for (let j = 0; j < 5; j++) P.ell(g, cx + j * 60 - 120, cy + Math.sin(j) * 12, 90 + rnd(i * 5 + j, 83) * 40, 34 + rnd(j, i) * 12, rgba(mixColor(Pa.sky[1], '#ffffff', 0.5), 0.35)); }
  };
  /** distant city silhouette band */
  B.cityline = (g, Pa, baseY, o = {}) => {
    const x0 = o.x0 === undefined ? -800 : o.x0, x1 = o.x1 === undefined ? 2720 : o.x1;
    const col = o.color || mixColor(Pa.sky[1], Pa.dark, 0.55);
    let x = x0; let i = 0;
    while (x < x1) {
      const w = 60 + rnd(i, o.seed || 3) * 120, h = (o.h || 160) * (0.4 + rnd(i, (o.seed || 3) + 1));
      P.rect(g, x, baseY - h, w + 1, h + 400, col);
      if (o.lit) for (let k = 0; k < 6; k++) if (rnd(i * 7 + k, 9) > 0.55) P.rect(g, x + 8 + (k % 3) * (w / 3.2), baseY - h + 14 + Math.floor(k / 3) * 26, 8, 10, rgba(Pa.light, 0.55));
      x += w; i++;
    }
  };

  // ---------- interior shell ----------
  /** back wall + ceiling + floor in one-point perspective */
  B.room = (g, Pa, o = {}) => {
    const hor = o.horizon || HOR, wallY = o.wallY || WALL, s = (o.persp || B.persp(hor))(wallY);
    const ceilY = wallY - unit(s) * (o.ceiling || 2.7);
    const vx = 960;
    // ceiling plane
    g.fillStyle = P.lin(g, 0, -600, 0, ceilY, [[0, shade(Pa.wall, -0.32)], [1, shade(Pa.wall, -0.12)]]); g.fillRect(-900, -600, 3720, ceilY + 600);
    // back wall
    g.fillStyle = P.lin(g, 0, ceilY, 0, wallY, [[0, shade(Pa.wall, -0.07)], [0.55, Pa.wall], [1, shade(Pa.wall, 0.04)]]); g.fillRect(-900, ceilY, 3720, wallY - ceilY);
    if (o.wallpaper === 'panels') for (let x = -900; x < 2820; x += 230) P.rect(g, x, ceilY, 3, wallY - ceilY, rgba('#000000', 0.05));
    if (o.wallpaper === 'stripes') for (let x = -900; x < 2820; x += 46) P.rect(g, x, ceilY, 20, wallY - ceilY, rgba('#ffffff', 0.035));
    // crown + baseboard
    P.rect(g, -900, ceilY - 2, 3720, 8, shade(Pa.trim, -0.05));
    P.rect(g, -900, wallY - unit(s) * 0.11, 3720, unit(s) * 0.11, Pa.trim);
    P.rect(g, -900, wallY - unit(s) * 0.11, 3720, 3, rgba('#ffffff', 0.25));
    // floor
    g.fillStyle = P.lin(g, 0, wallY, 0, 1400, [[0, shade(Pa.floor, 0.04)], [1, shade(Pa.floor, -0.22)]]);
    g.fillRect(-900, wallY, 3720, 900);
    const kind = o.floor || 'planks';
    g.save(); g.beginPath(); g.rect(-900, wallY, 3720, 900); g.clip();
    if (kind === 'planks' || kind === 'tiles') {
      const n = kind === 'planks' ? 34 : 22;
      for (let i = -n; i <= n; i++) {
        const xw = vx + i * (kind === 'planks' ? 80 : 130);
        const k = (1400 - hor) / (wallY - hor);
        P.line(g, xw, wallY, vx + (xw - vx) * k, 1400, rgba('#000000', 0.07), 2);
      }
      if (kind === 'tiles' || kind === 'planks') {
        let y = wallY, d = 16;
        while (y < 1400) { P.line(g, -900, y, 2820, y, rgba('#000000', kind === 'tiles' ? 0.07 : 0.035), 2); d *= 1.28; y += d; }
      }
    }
    g.restore();
    P.rect(g, -900, wallY, 3720, 3, rgba('#000000', 0.18));
    // side walls (optional, for wide establishing shots)
    if (o.sideWalls) {
      const lx = o.sideWalls[0], rx = o.sideWalls[1];
      const kB = (1400 - hor) / (wallY - hor);
      P.poly(g, [[lx, ceilY], [lx, wallY], [vx + (lx - vx) * kB, 1400], [-900, 1400], [-900, -600], [vx + (lx - vx) * ((-600 - hor) / (ceilY - hor)), -600]], shade(Pa.wall, -0.12));
      P.poly(g, [[rx, ceilY], [rx, wallY], [vx + (rx - vx) * kB, 1400], [2820, 1400], [2820, -600], [vx + (rx - vx) * ((-600 - hor) / (ceilY - hor)), -600]], shade(Pa.wall, -0.18));
      P.line(g, lx, ceilY, lx, wallY, rgba('#000000', 0.12), 3); P.line(g, rx, ceilY, rx, wallY, rgba('#000000', 0.12), 3);
    }
    return { ceilY, s };
  };
  /** window on a wall: x,y top-left, w,h; o.time: day|dusk|night ; o.view: city|trees|sky ; o.blinds/o.curtains */
  B.window = (g, Pa, x, y, w, h, o = {}) => {
    const fr = o.frame || shade(Pa.trim, -0.02);
    P.rect(g, x - 10, y - 10, w + 20, h + 20, fr);
    g.save(); g.beginPath(); g.rect(x, y, w, h); g.clip();
    B.sky(g, Pa, { x0: x, x1: x + w, y0: y, y1: y + h * 1.4, time: o.time, stars: o.time === 'night', moon: o.moon ? [x + w * 0.72, y + h * 0.25] : null });
    const view = o.view || 'city';
    if (view === 'city') B.cityline(g, Pa, y + h * 0.95, { x0: x - 40, x1: x + w + 40, h: h * 0.5, lit: o.time !== 'day', seed: Math.floor(x) % 97, color: o.time === 'day' ? mixColor(Pa.sky[1], '#8c9aa8', 0.55) : null });
    if (view === 'trees') for (let i = 0; i < 6; i++) { const cx = x + (i + 0.3) * w / 5, cy = y + h * (0.7 + 0.15 * rnd(i, 5)); for (let j = 0; j < 4; j++) P.circle(g, cx + (j - 1.5) * 26, cy - j % 2 * 24, 46, rgba(o.time === 'night' ? '#1c2a26' : mixColor(Pa.green, Pa.sky[1], 0.25), 0.95)); }
    g.fillStyle = rgba(Pa.glass, 0.18); g.fillRect(x, y, w, h);
    // glass sheen
    P.poly(g, [[x + w * 0.1, y], [x + w * 0.25, y], [x + w * 0.05, y + h], [x - w * 0.1, y + h]], rgba('#ffffff', 0.07));
    g.restore();
    const mw = 10;
    const cols = o.cols || 2, rows = o.rows || 1;
    for (let i = 1; i < cols; i++) P.rect(g, x + (w * i) / cols - mw / 2, y, mw, h, fr);
    for (let i = 1; i < rows; i++) P.rect(g, x, y + (h * i) / rows - mw / 2, w, mw, fr);
    P.rect(g, x - 18, y + h + 6, w + 36, 12, shade(fr, -0.06));
    if (o.blinds) for (let i = 0; i < h / 22; i++) P.rect(g, x, y + i * 22, w, 9, rgba(shade(Pa.trim, -0.1), 0.85));
    if (o.curtains) { const cc = o.curtains === true ? shade(Pa.wall, -0.25) : o.curtains; for (const sx of [-1, 1]) { const cx = sx < 0 ? x - 40 : x + w - 50; g.beginPath(); g.moveTo(cx, y - 30); g.lineTo(cx + 90, y - 30); g.quadraticCurveTo(cx + 60 + sx * 10, y + h * 0.5, cx + 80, y + h + 40); g.lineTo(cx - 10, y + h + 40); g.closePath(); g.fillStyle = cc; g.fill(); } }
  };
  B.door = (g, Pa, x, y, w, h, o = {}) => {
    P.rect(g, x - 12, y - 12, w + 24, h + 12, shade(Pa.trim, -0.04));
    P.rect(g, x, y, w, h, o.color || shade(Pa.furn2, -0.05));
    if (o.open) { P.rect(g, x, y, w * 0.85, h, Pa.dark); P.poly(g, [[x + w * 0.85, y], [x + w * 1.05, y - 10], [x + w * 1.05, y + h + 6], [x + w * 0.85, y + h]], o.color || shade(Pa.furn2, -0.1)); if (o.light) P.glow(g, x + w * 0.4, y + h * 0.5, h * 0.8, o.light, 0.35); }
    else { P.rect(g, x + w * 0.12, y + h * 0.08, w * 0.76, h * 0.36, rgba('#000000', 0.06)); P.rect(g, x + w * 0.12, y + h * 0.52, w * 0.76, h * 0.4, rgba('#000000', 0.06)); P.circle(g, x + w * 0.85, y + h * 0.52, 7, Pa.metal); }
  };
  B.cabinets = (g, Pa, x, y, w, h, n, o = {}) => {
    const c = o.color || Pa.furn2;
    P.rect(g, x, y, w, h, c);
    for (let i = 0; i < n; i++) { const cx = x + (w / n) * i; P.rect(g, cx + 4, y + 4, w / n - 8, h - 8, shade(c, 0.05)); P.rect(g, cx + w / n / 2 - (i % 2 ? 30 : -18), y + (o.top ? h - 26 : 20), 12, 4, Pa.metal); }
    P.rect(g, x, y + h - 4, w, 4, rgba('#000000', 0.15));
  };
  B.counter = (g, Pa, x, y, w, h, o = {}) => { // y = top surface
    B.cabinets(g, Pa, x, y + 14, w, h - 14, Math.max(1, Math.round(w / 160)), o);
    P.rect(g, x - 12, y, w + 24, 16, o.top || shade(Pa.furn, 0.06)); P.rect(g, x - 12, y + 14, w + 24, 4, rgba('#000000', 0.18));
  };
  B.fridge = (g, Pa, x, y, w, h, o = {}) => { // x,y top-left
    const c = o.color || shade(Pa.furn, 0.02);
    P.rr(g, x, y, w, h, 14, c); P.rect(g, x + 6, y + h * 0.36, w - 12, 4, rgba('#000000', 0.14));
    g.fillStyle = P.lin(g, x, 0, x + w, 0, [[0, rgba('#ffffff', 0.12)], [0.4, rgba('#ffffff', 0)], [1, rgba('#000000', 0.1)]]); g.fillRect(x, y, w, h);
    P.rr(g, x + 14, y + h * 0.1, 9, h * 0.2, 4, shade(c, -0.2)); P.rr(g, x + 14, y + h * 0.44, 9, h * 0.26, 4, shade(c, -0.2));
    if (o.magnets !== false) for (let i = 0; i < 5; i++) P.circle(g, x + w * (0.3 + 0.15 * i), y + 34 + (i % 2) * 22, 7, ['#d6453d', '#4f8ef0', '#f2b84b', '#4fb38a', '#9a6ff0'][i]);
  };
  B.shelfGrid = (g, Pa, x, y, cols, rows, cw, chh, o = {}) => {
    const fr = o.frame || shade(Pa.trim, 0.04);
    P.rect(g, x - 8, y - 8, cols * cw + 16, rows * chh + 16, fr);
    for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
      const cx = x + c * cw, cy = y + r * chh;
      P.rect(g, cx + 5, cy + 5, cw - 10, chh - 10, shade(fr, -0.06));
      P.rect(g, cx + 5, cy + 5, cw - 10, 6, rgba('#000000', 0.06));
      if (o.item) o.item(g, cx + cw / 2, cy + chh - 8, Math.min(cw, chh) / 100, r * cols + c);
    }
  };
  /** item painters for shelves */
  B.items = {
    shoe: (g, x, y, s, i) => { const cols = ['#5f8f8a', '#4a6d96', '#8d88a3', '#6f7f99', '#7a9b8f', '#5b6f8f']; const c = cols[(i * 7 + 3) % cols.length]; P.rr(g, x - 34 * s, y - 9 * s, 68 * s, 9 * s, 4 * s, '#eceef0'); g.beginPath(); g.moveTo(x - 33 * s, y - 8 * s); g.lineTo(x - 27 * s, y - 26 * s); g.lineTo(x - 8 * s, y - 28 * s); g.quadraticCurveTo(x + 30 * s, y - 18 * s, x + 34 * s, y - 8 * s); g.closePath(); g.fillStyle = c; g.fill(); P.line(g, x - 14 * s, y - 20 * s, x + 6 * s, y - 16 * s, 'rgba(255,255,255,0.7)', 2.5 * s); },
    book: (g, x, y, s, i) => { const cols = ['#7b4f3a', '#3f5a7a', '#8a7a4f', '#5b6e57', '#8b4a52', '#4f5f7f']; let xx = x - 38 * s; for (let k = 0; k < 7; k++) { const w = (8 + rnd(i * 9 + k, 2) * 6) * s, h = (44 + rnd(i * 9 + k, 3) * 22) * s; P.rect(g, xx, y - h, w, h, cols[(i + k) % cols.length]); xx += w + 1.5 * s; } },
    box: (g, x, y, s, i) => { const cols = ['#a89a86', '#8f9ba8', '#b3a28f']; P.rect(g, x - 34 * s, y - 40 * s, 68 * s, 40 * s, cols[i % 3]); P.rect(g, x - 34 * s, y - 40 * s, 68 * s, 8 * s, rgba('#ffffff', 0.15)); },
    jar: (g, x, y, s, i) => { for (let k = -1; k <= 1; k++) P.rr(g, x + k * 22 * s - 9 * s, y - 34 * s, 18 * s, 34 * s, 5 * s, ['#c98f5b', '#9fb27a', '#d9c27a', '#a46f6f'][(i + k + 4) % 4]); },
    plant: (g, x, y, s, i, Pa) => { P.rect(g, x - 14 * s, y - 24 * s, 28 * s, 24 * s, '#c9b8a3'); for (let k = 0; k < 5; k++) P.ell(g, x + (k - 2) * 7 * s, y - 34 * s - (k % 2) * 8 * s, 8 * s, 16 * s, '#6f9a59', (k - 2) * 0.35); },
    trophy: (g, x, y, s) => { P.rect(g, x - 10 * s, y - 10 * s, 20 * s, 10 * s, '#4a3b2a'); P.ell(g, x, y - 30 * s, 13 * s, 16 * s, '#d9ab3e'); },
  };
  /** furniture is sized in character units (CU) times the scale s at its base, so characters sit/lie on it correctly:
      seat 50 CU, table/desk 100 CU, counter 120 CU, mattress 58 CU (these characters have short legs: knee ~47 CU) */
  B.bed = (g, Pa, x, y, s, o = {}) => { // x = headboard side (left), y = floor at the bed's front, side view
    const w = (o.len || 520) * s, top = 58 * s, c = o.frame || shade(Pa.furn2, -0.15), sheet = o.sheet || shade(Pa.furn, 0.04);
    P.rect(g, x, y - 150 * s, 16 * s, 150 * s, c); P.rect(g, x + w - 12 * s, y - 80 * s, 12 * s, 80 * s, c);
    P.rect(g, x + 8 * s, y - top + 10 * s, w - 16 * s, top - 18 * s, c);
    P.rr(g, x + 12 * s, y - top - 6 * s, w - 26 * s, 22 * s, 9 * s, sheet);
    P.rr(g, x + 20 * s, y - top - 26 * s, 130 * s, 28 * s, 12 * s, shade(sheet, 0.08));
    if (o.blanket !== false && !o.inBed) B.blanket(g, Pa, x, y, s, o);
    P.rect(g, x + 8 * s, y - 10 * s, w - 16 * s, 10 * s, shade(c, -0.12));
  };
  B.blanket = (g, Pa, x, y, s, o = {}) => {
    const w = (o.len || 520) * s, top = 58 * s, from = o.blanketFrom || 0.3, lump = (o.lump || (o.inBed ? 1 : 0)) * 34 * s;
    g.beginPath(); g.moveTo(x + w * from, y - top - 4 * s); g.quadraticCurveTo(x + w * 0.62, y - top - 6 * s - lump, x + w - 14 * s, y - top + 2 * s);
    g.lineTo(x + w - 8 * s, y - 12 * s); g.lineTo(x + w * from - 6 * s, y - 12 * s); g.closePath(); g.fillStyle = o.blanketColor || Pa.accent2; g.fill();
    P.line(g, x + w * from, y - top, x + w * from - 4 * s, y - 14 * s, rgba('#000000', 0.15), 4 * s);
  };
  B.sofa = (g, Pa, x, y, s, o = {}) => { // front view, x centre, y floor at the front edge; seat at 50 CU
    const c = o.color || Pa.accent2, w = (o.w || 470) * s, seat = 50 * s, back = 118 * s, arm = 78 * s;
    P.rr(g, x - w / 2, y - back, w, back - seat + 14 * s, 18 * s, shade(c, -0.08));
    P.rr(g, x - w / 2 + 26 * s, y - seat - 8 * s, w - 52 * s, 26 * s, 10 * s, c);
    for (const sx of [-1, 1]) P.rr(g, x + sx * (w / 2 - 16 * s) - 26 * s, y - arm, 52 * s, arm - 6 * s, 14 * s, shade(c, -0.12));
    P.rect(g, x - w / 2 + 14 * s, y - seat + 16 * s, w - 28 * s, seat - 24 * s, shade(c, -0.18));
    P.line(g, x, y - seat - 8 * s, x, y - seat + 18 * s, rgba('#000000', 0.12), 3);
    for (const sx of [-1, 1]) P.rect(g, x + sx * (w / 2 - 30 * s) - 5 * s, y - 9 * s, 10 * s, 9 * s, Pa.dark);
  };
  B.table = (g, Pa, x, y, w, h, o = {}) => { // x centre, y floor
    const c = o.color || Pa.furn2;
    P.rect(g, x - w / 2, y - h, w, 16, shade(c, 0.08)); P.rect(g, x - w / 2, y - h + 14, w, 5, rgba('#000000', 0.2));
    for (const sx of [-1, 1]) P.rect(g, x + sx * (w / 2 - 22) - 7, y - h + 16, 14, h - 16, shade(c, -0.1));
  };
  B.desk = (g, Pa, x, y, w, h, o = {}) => { B.table(g, Pa, x, y, w, h, o); P.rect(g, x + w / 2 - 150, y - h + 18, 130, h * 0.45, shade(o.color || Pa.furn2, -0.04)); };
  B.chair = (g, Pa, x, y, o = {}) => { // side view, back on the left; seat at 50 CU
    const s = o.s || 1, c = o.color || Pa.dark;
    P.rect(g, x - 30 * s, y - 52 * s, 62 * s, 8 * s, c);
    P.rect(g, x - 30 * s, y - 130 * s, 9 * s, 82 * s, c);
    P.rect(g, x - 27 * s, y - 46 * s, 6 * s, 46 * s, c); P.rect(g, x + 22 * s, y - 46 * s, 6 * s, 46 * s, c);
  };
  B.tv = (g, Pa, x, y, w, o = {}) => { // x centre, y bottom of screen
    const h = w * 0.56;
    P.rr(g, x - w / 2, y - h, w, h, 6, '#121418');
    P.rect(g, x - w / 2 + 8, y - h + 8, w - 16, h - 16, o.on ? (o.screen || '#5b7fb5') : '#0b0d10');
    if (o.on) P.glow(g, x, y - h / 2, w * 1.2, o.screen || '#7fa6e6', 0.4);
  };
  B.rug = (g, Pa, x, y, w, h, o = {}) => { P.ell(g, x, y, w / 2, h / 2, o.color || rgba(Pa.accent, 0.25)); P.ell(g, x, y, w / 2 - 14, h / 2 - 6, null, 0, rgba('#ffffff', 0.15), 3); };
  B.pendant = (g, Pa, x, y, o = {}) => { // y = lamp bottom
    P.line(g, x, y - 400, x, y - 40, Pa.dark, 3);
    P.poly(g, [[x - 50, y], [x + 50, y], [x + 22, y - 44], [x - 22, y - 44]], o.color || Pa.dark);
    if (o.on !== false) { P.ell(g, x, y, 46, 8, mixColor(Pa.light, '#ffffff', 0.5)); }
  };
  B.trackLights = (g, Pa, y, o = {}) => {
    P.rect(g, -900, y - 3, 3720, 6, Pa.dark);
    for (let x = (o.x0 || -200); x < (o.x1 || 2200); x += o.gap || 170) { P.rect(g, x - 4, y, 8, 18, Pa.dark); P.rr(g, x - 12, y + 16, 24, 26, 6, Pa.dark); }
  };
  B.frameArt = (g, Pa, x, y, w, h, o = {}) => { SF.props.poster(g, x, y, 1, Object.assign({ w, h }, o)); };

  // ---------- exterior pieces ----------
  B.streetLamp = (g, Pa, x, y, s, o = {}) => { // y ground
    const c = o.color || shade(Pa.dark, 0.1);
    P.rect(g, x - 4 * s, y - 330 * s, 8 * s, 330 * s, c);
    if (o.style === 'lantern') { P.poly(g, [[x - 18 * s, y - 330 * s], [x + 18 * s, y - 330 * s], [x + 22 * s, y - 380 * s], [x - 22 * s, y - 380 * s]], mixColor(Pa.light, '#ffffff', 0.4)); P.poly(g, [[x - 26 * s, y - 380 * s], [x + 26 * s, y - 380 * s], [x, y - 400 * s]], c); }
    else { P.path(g, [[x, y - 320 * s], [x, y - 350 * s], [x + 50 * s, y - 360 * s]], c, 7 * s); P.rr(g, x + 34 * s, y - 368 * s, 50 * s, 12 * s, 5 * s, c); P.ell(g, x + 59 * s, y - 355 * s, 20 * s, 4 * s, mixColor(Pa.light, '#ffffff', 0.4)); }
  };
  B.lampGlow = (g, Pa, x, y, s, a = 1) => { P.glow(g, x + 50 * s, y - 356 * s, 260 * s, Pa.light, 0.8 * a); P.cone(g, x + 59 * s, y - 352 * s, 90, 58, 380 * s, Pa.light, 0.12 * a); P.ell(g, x + 59 * s, y, 110 * s, 16 * s, rgba(Pa.light, 0.12 * a)); };
  B.tree = (g, Pa, x, y, s, o = {}) => {
    const trunk = o.trunk || shade(Pa.dark, 0.05), leaf = o.leaf || Pa.green;
    P.poly(g, [[x - 7 * s, y], [x + 7 * s, y], [x + 4 * s, y - 180 * s], [x - 4 * s, y - 180 * s]], trunk);
    P.path(g, [[x, y - 130 * s], [x - 40 * s, y - 190 * s]], trunk, 5 * s); P.path(g, [[x, y - 150 * s], [x + 36 * s, y - 210 * s]], trunk, 5 * s);
    if (o.bare) { P.path(g, [[x, y - 180 * s], [x - 10 * s, y - 250 * s]], trunk, 4 * s); P.path(g, [[x, y - 175 * s], [x + 30 * s, y - 240 * s]], trunk, 3 * s); return; }
    const seed = Math.floor(x * 3.1) % 997;
    for (let i = 0; i < 9; i++) { const a = rnd(i, seed) * Math.PI * 2, r = (30 + rnd(i, seed + 1) * 50) * s; P.circle(g, x + Math.cos(a) * r * 1.1, y - 230 * s + Math.sin(a) * r * 0.7, (45 + rnd(i, seed + 2) * 30) * s, shade(leaf, (rnd(i, seed + 3) - 0.5) * 0.24)); }
  };
  // park bench in character units: seat 50, backrest to 112, default 300 CU wide (two adults side by side). (x,y) = front-centre on the ground
  B.bench = (g, Pa, x, y, s, o = {}) => { const c = o.color || shade(Pa.furn2, -0.2), hw = (o.w || 300) / 2 * s; P.rect(g, x - hw, y - 52 * s, hw * 2, 10 * s, c); P.rect(g, x - hw, y - 112 * s, hw * 2, 10 * s, c); P.rect(g, x - hw, y - 92 * s, hw * 2, 10 * s, c); for (const sx of [-1, 1]) { P.rect(g, x + sx * (hw - 18 * s) - 5 * s, y - 52 * s, 10 * s, 52 * s, Pa.dark); P.rect(g, x + sx * (hw - 18 * s) - 4 * s, y - 112 * s, 8 * s, 60 * s, shade(c, -0.15)); } };
  // marks for sitting on a bench drawn with B.bench at (x,y,s): bench (middle), benchL, benchR
  B.benchMarks = (x, y, s, z) => ({ bench: { x, y, seat: 50, z }, benchL: { x: x - 72 * s, y, seat: 50, z }, benchR: { x: x + 72 * s, y, seat: 50, z } });
  B.car = (g, Pa, x, y, s, o = {}) => { // side view, x centre, y ground
    const c = o.color || '#9a5550';
    P.rr(g, x - 150 * s, y - 70 * s, 300 * s, 50 * s, 18 * s, c);
    g.beginPath(); g.moveTo(x - 90 * s, y - 68 * s); g.lineTo(x - 55 * s, y - 112 * s); g.lineTo(x + 50 * s, y - 112 * s); g.lineTo(x + 95 * s, y - 68 * s); g.closePath(); g.fillStyle = c; g.fill();
    P.poly(g, [[x - 78 * s, y - 70 * s], [x - 50 * s, y - 104 * s], [x - 4 * s, y - 104 * s], [x - 4 * s, y - 70 * s]], rgba(Pa.glass, 0.9));
    P.poly(g, [[x + 4 * s, y - 70 * s], [x + 4 * s, y - 104 * s], [x + 46 * s, y - 104 * s], [x + 80 * s, y - 70 * s]], rgba(Pa.glass, 0.9));
    for (const sx of [-1, 1]) { P.circle(g, x + sx * 92 * s, y - 20 * s, 24 * s, '#1b1d22'); P.circle(g, x + sx * 92 * s, y - 20 * s, 10 * s, '#7b818a'); }
  };
  B.building = (g, Pa, x, y, w, h, o = {}) => { // facade, x left, y ground
    const c = o.color || Pa.wall2;
    P.rect(g, x, y - h, w, h, c);
    P.rect(g, x, y - h, w, 10, shade(c, -0.15));
    const lit = o.lit;
    for (let fy = y - h + 40; fy < y - (o.shop ? 150 : 60); fy += 70) for (let fx = x + 20; fx < x + w - 40; fx += 60) {
      const on = lit && rnd(Math.floor(fx * 3 + fy), 5) > 0.55;
      P.rect(g, fx, fy, 30, 38, on ? rgba(Pa.light, 0.8) : rgba(Pa.glass, 0.7));
    }
    if (o.shop) { P.rect(g, x + 14, y - 130, w - 28, 120, o.shopLit ? rgba(Pa.light, 0.45) : rgba(Pa.glass, 0.8)); P.rect(g, x + 8, y - 150, w - 16, 18, o.awning || shade(c, -0.25)); }
  };

  /** group depth-placed items ({y, draw(g,Pa)}) into near/mid/far static layers; far items draw first inside a band */
  B.depthBands = (set, items, zAt, edges = [1.5, 3.5]) => {
    const bands = [[], [], []];
    for (const it of items) { const z = zAt(it.y); bands[z < edges[0] ? 0 : z < edges[1] ? 1 : 2].push(it); }
    bands.forEach((b, i) => {
      if (!b.length) return;
      b.sort((a, c) => a.y - c.y);
      const z = b.reduce((a, it) => a + zAt(it.y), 0) / b.length;
      set.layers.push({ id: 'band' + i, z, static: true, draw: (g, t, Pa) => { for (const it of b) it.draw(g, Pa); } });
    });
  };

  // ======================= SETS =======================
  const interior = (name, draw, extra = {}) => (o = {}) => {
    const hor = o.horizon || HOR, wallY = o.wallY || WALL;
    const persp = B.persp(hor, STAND, SC), zAt = B.depth(STAND, 80);
    const set = Object.assign({ name, horizon: hor, wallY, floorY: STAND, scaleAt: persp, zAt, marks: {}, layers: [], amb: 'room', time: o.time || 'day' }, extra);
    draw(set, o);
    set.marks.center = set.marks.center || { x: 960, y: STAND };
    set.marks.left = set.marks.left || { x: 560, y: STAND };
    set.marks.right = set.marks.right || { x: 1360, y: STAND };
    set.marks.offLeft = { x: -260, y: STAND }; set.marks.offRight = { x: 2180, y: STAND };
    set.marks.back = set.marks.back || { x: 960, y: wallY + 40 };
    return set;
  };
  const nightish = (o) => o.time === 'night' || o.time === 'dusk' || o.lights === true;

  sets.kitchen = interior('kitchen', (S, o) => {
    S.amb = nightish(o) ? 'room_night' : 'room';
    S.marks = { fridge: { x: 560, y: 770 }, counter: { x: 1230, y: 770 }, sink: { x: 1330, y: 770 }, door: { x: 140, y: 800 }, table: { x: 1580, y: 940 }, counterTop: { x: 1230, y: 594 } };
    S.layers.push({ id: 'room', z: 3, static: true, draw: (g, t, Pa) => {
      B.room(g, Pa, { floor: 'tiles' });
      B.window(g, Pa, 1150, 300, 400, 230, { time: o.time, view: 'city', moon: o.time === 'night', cols: 2 });
      B.cabinets(g, Pa, 820, 250, 290, 170, 2, { top: true }); B.cabinets(g, Pa, 1590, 250, 300, 170, 2, { top: true });
      B.door(g, Pa, 60, 300, 170, 440, {});
      P.rect(g, 820, 430, 1070, 166, shade(Pa.wall, 0.06)); // backsplash
      for (let x = 820; x < 1890; x += 36) P.rect(g, x, 430, 2, 166, rgba('#000000', 0.04));
    }});
    S.layers.push({ id: 'furniture', z: 2.6, static: true, draw: (g, t, Pa) => {
      B.fridge(g, Pa, 420, 330, 260, 410, {});
      B.counter(g, Pa, 820, 594, 1070, 146, {});
      P.rr(g, 1270, 588, 200, 12, 6, shade(Pa.metal, -0.1)); // sink
      P.path(g, [[1440, 594], [1440, 534], [1405, 534]], Pa.metal, 7);
      SF.props.mug(g, 960, 594, 0.9, { steam: false }, Pa);
      P.rr(g, 1010, 554, 70, 40, 8, shade(Pa.accent2, -0.1)); // toaster
      SF.props.plant(g, 1560, 300, 0.7, {}, Pa);
      SF.props.clock(g, 300, 230, 0.8, { hours: o.clock === undefined ? (o.time === 'night' ? 11.8 : 7.5) : o.clock }, Pa);
    }});
    S.lights = (t, Pa) => nightish(o)
      ? [{ type: 'glow', x: 1350, y: 400, r: 420, color: o.time === 'night' ? '#9bb4e6' : Pa.light, a: 0.25 }, { type: 'pendant', x: 960, y: 160 }]
      : [{ type: 'patch', pts: [[1150, 740], [1550, 740], [1720, 1080], [1260, 1080]], color: Pa.light, a: 0.16 }, { type: 'glow', x: 1350, y: 410, r: 520, color: Pa.light, a: 0.18 }];
  });

  sets.bedroom = interior('bedroom', (S, o) => {
    S.amb = nightish(o) ? 'room_night' : 'room';
    const sb = 1.22, bx = 300, by = 760; // bed against the back wall
    // marks: 'bed' = lying on the mattress (use act [[0,'lie']]), 'bedEdge' = sitting on the side, others standing spots
    S.marks = { bed: { x: bx + 85 * sb + 256 * sb, y: by - 58 * sb - 12 * sb + 10, z: 2.0, s: sb }, bedEdge: { x: bx + 420 * sb, y: by + 6, seat: 58 }, bedside: { x: 1120, y: 790 }, desk: { x: 1500, y: 790 }, deskChair: { x: 1440, y: 762, seat: 50 }, window: { x: 1180, y: 760 }, door: { x: 160, y: 800 } };
    S.layers.push({ id: 'room', z: 3, static: true, draw: (g, t, Pa) => {
      B.room(g, Pa, { floor: 'planks', wallpaper: 'panels' });
      B.window(g, Pa, 1020, 250, 330, 280, { time: o.time, view: o.view || 'city', moon: o.time === 'night', curtains: true });
      B.door(g, Pa, 40, 300, 170, 440, { open: o.doorOpen, light: Pa.light });
      SF.props.poster(g, 700, 380, 1, { w: 150, h: 200, icon: o.poster || 'mountain' });
    }});
    S.layers.push({ id: 'furniture', z: 2.4, static: true, draw: (g, t, Pa) => {
      B.bed(g, Pa, bx, by, sb, { inBed: o.inBed, lump: o.lump, blanket: o.blanket });
      B.table(g, Pa, 1060, 760, 110, 86, {}); // nightstand ~70 CU
      SF.props.alarmClock(g, 1040, 674, 0.85, { time: o.alarm || (o.time === 'night' ? '2:14' : '7:00') }, Pa, t);
      if (o.lamp !== false) SF.props.lamp(g, 1092, 676, 0.55, { on: nightish(o) && o.lampOn !== false }, Pa);
      B.desk(g, Pa, 1560, 760, 380, 122, {});
      SF.props.laptop(g, 1530, 638, 0.7, { on: !!o.laptopOn }, Pa);
      SF.props.books(g, 1690, 638, 0.65, {});
      B.chair(g, Pa, 1440, 762, { s: 1.24 });
      B.rug(g, Pa, 820, 800, 520, 70, {});
    }});
    if (o.inBed) S.layers.push({ id: 'blanket', z: 1.9, static: true, draw: (g, t, Pa) => B.blanket(g, Pa, bx, by, sb, { inBed: true, lump: o.lump === undefined ? 0.6 : o.lump, blanketFrom: 0.3 }) });
    S.lights = (t, Pa) => o.time === 'night'
      ? [{ type: 'patch', pts: [[1020, 740], [1350, 740], [1500, 1080], [1000, 1080]], color: '#9fb4e8', a: 0.08 }]
      : [{ type: 'patch', pts: [[1020, 740], [1350, 740], [1560, 1080], [1040, 1080]], color: Pa.light, a: 0.16 }];
  });

  sets.living = interior('living', (S, o) => {
    S.amb = nightish(o) ? 'room_night' : 'room';
    const sy = 772, ss = S.scaleAt(sy); // sofa front edge
    S.marks = { sofa: { x: 960, y: sy, seat: 50 }, sofaL: { x: 845, y: sy, seat: 50 }, sofaR: { x: 1075, y: sy, seat: 50 }, window: { x: 1560, y: 770 }, door: { x: 200, y: 800 }, front: { x: 960, y: 900 } };
    S.layers.push({ id: 'room', z: 3, static: true, draw: (g, t, Pa) => {
      B.room(g, Pa, { floor: 'planks', wallpaper: 'stripes' });
      B.window(g, Pa, 1420, 270, 330, 300, { time: o.time, view: 'trees', curtains: true });
      SF.props.photo(g, 780, 420, 1.1, {}); SF.props.photo(g, 1110, 400, 0.9, { bg: '#d9c7b0' });
      P.rect(g, 140, 300, 300, 14, shade(Pa.furn2, -0.15)); SF.props.books(g, 240, 300, 0.6, {}); SF.props.plant(g, 380, 300, 0.45, {}, Pa);
    }});
    S.layers.push({ id: 'furniture', z: 1.9, static: true, draw: (g, t, Pa) => {
      B.sofa(g, Pa, 960, sy, ss, { color: o.sofa || Pa.accent2 });
      SF.props.floorLamp(g, 1330, 760, 0.85, { on: nightish(o) }, Pa);
      SF.props.plant(g, 560, 760, 1, {}, Pa);
      B.rug(g, Pa, 960, 860, 900, 120, {});
    }});
    S.layers.push({ id: 'coffee', z: -1.2, static: true, draw: (g, t, Pa) => { B.table(g, Pa, 960, 1120, 620, 150, { color: shade(Pa.furn2, -0.2) }); SF.props.mug(g, 820, 970, 1.2, { steam: false }, Pa); } });
    S.lights = (t, Pa) => nightish(o) ? [{ type: 'glow', x: 1330, y: 440, r: 600, color: Pa.light, a: 0.35 }] : [{ type: 'patch', pts: [[1420, 740], [1750, 740], [1980, 1080], [1460, 1080]], color: Pa.light, a: 0.14 }];
  });

  sets.office = interior('office', (S, o) => {
    S.amb = 'office';
    S.marks = { desk: { x: 740, y: 772 }, deskChair: { x: 690, y: 772, seat: 50 }, window: { x: 1400, y: 760 }, door: { x: 160, y: 800 } };
    S.layers.push({ id: 'room', z: 3.2, static: true, draw: (g, t, Pa) => {
      B.room(g, Pa, { floor: 'tiles', wallpaper: 'panels' });
      for (let i = 0; i < 4; i++) B.window(g, Pa, 140 + i * 450, 240, 330, 330, { time: o.time, view: 'city', blinds: i % 2 === 0 });
    }});
    S.layers.push({ id: 'desks', z: 2.4, static: true, draw: (g, t, Pa) => {
      for (let i = 0; i < 4; i++) { const x = 300 + i * 440; B.desk(g, Pa, x, 760, 340, 122, { color: Pa.furn }); P.rr(g, x - 70, 528, 140, 90, 6, '#20242b'); P.rect(g, x - 62, 536, 124, 74, nightish(o) && i === 1 ? '#9fbbe6' : '#2c3442'); P.rect(g, x - 6, 618, 12, 20, '#20242b'); }
    }});
    S.lights = (t, Pa) => [{ type: 'glow', x: 740, y: 520, r: 300, color: '#a9c4f0', a: nightish(o) ? 0.35 : 0.08 }];
  });

  sets.store = interior('store', (S, o) => {
    S.amb = 'store';
    S.marks = { counter: { x: 960, y: 760 }, behind: { x: 1080, y: 720 }, front: { x: 720, y: 900 }, door: { x: 120, y: 860 }, shelf: { x: 520, y: 760 } };
    const itemFn = B.items[o.item || 'shoe'] || B.items.shoe;
    S.layers.push({ id: 'room', z: 3.2, static: true, draw: (g, t, Pa) => {
      B.room(g, Pa, { floor: 'tiles', sideWalls: [70, 1850] });
      B.trackLights(g, Pa, 190, {});
      B.shelfGrid(g, Pa, 160, 260, 5, 5, 110, 92, { item: (gg, x, y, s, i) => itemFn(gg, x, y, s, i, Pa) });
      P.rect(g, 760, 200, 220, 540, shade(Pa.wall, 0.08)); // pillar
      B.shelfGrid(g, Pa, 990, 260, 7, 5, 110, 92, { item: (gg, x, y, s, i) => itemFn(gg, x, y, s, i + 31, Pa) });
      SF.props.poster(g, 1890, 380, 1, { w: 90, h: 120, icon: o.poster || 'runner' });
    }});
    S.layers.push({ id: 'counter', z: 1.6, static: true, draw: (g, t, Pa) => {
      const top = 600, x0 = 560, x1 = 1460;
      P.rect(g, x0, top, x1 - x0, 260, shade(Pa.furn2, 0.12));
      for (let x = x0 + 10; x < x1; x += 22) P.rect(g, x, top + 30, 10, 228, rgba('#000000', 0.07));
      P.rect(g, x0 - 20, top - 10, x1 - x0 + 40, 26, shade(Pa.furn, 0.08)); P.rect(g, x0 - 20, top + 14, x1 - x0 + 40, 6, rgba('#000000', 0.18));
      P.rr(g, x1 - 160, top - 46, 70, 46, 4, shade(Pa.dark, 0.1)); // register
      P.rr(g, x1 - 240, top - 52, 64, 44, 3, '#f4f4f2'); P.text(g, o.sign || '14-DAY', x1 - 208, top - 38, { size: 13, color: '#222', weight: 800 }); P.text(g, o.sign2 || 'RETURNS', x1 - 208, top - 22, { size: 11, color: '#222', weight: 800 });
    }});
    S.layers.push({ id: 'floorlight', z: 0.4, static: true, draw: (g, t, Pa) => {
      for (let i = 0; i < 3; i++) P.lightPatch(g, [[200 + i * 520, 1080], [430 + i * 520, 1080], [600 + i * 520, 880], [420 + i * 520, 880]], Pa.light, 0.07);
      if (o.mat !== false) P.rect(g, 640, 980, 640, 100, rgba(Pa.dark, 0.35));
    }});
    S.lights = (t, Pa) => [{ type: 'glow', x: 960, y: 260, r: 900, color: Pa.light, a: 0.12 }];
  });

  sets.hallway = interior('hallway', (S, o) => {
    S.amb = 'room';
    S.marks = { door1: { x: 420, y: 780 }, door2: { x: 1500, y: 780 }, end: { x: 960, y: 760 } };
    S.layers.push({ id: 'room', z: 3, static: true, draw: (g, t, Pa) => {
      B.room(g, Pa, { floor: 'tiles', sideWalls: [620, 1300], ceiling: 2.5 });
      B.door(g, Pa, 860, 380, 200, 360, { open: o.endOpen, light: Pa.light });
      for (let i = 0; i < 3; i++) { P.rect(g, 300 + i * 30, 200 + i * 60, 20, 520 - i * 120, rgba('#000000', 0.05)); }
      for (let i = 0; i < 4; i++) P.ell(g, 960, 200 + i * 40, 90 - i * 18, 10 - i * 2, mixColor(Pa.light, '#ffffff', 0.5));
    }});
    S.lights = (t, Pa) => [{ type: 'glow', x: 960, y: 220, r: 500, color: Pa.light, a: 0.25 }];
  });

  sets.classroom = interior('classroom', (S, o) => {
    S.amb = 'room';
    S.marks = { board: { x: 960, y: 760 }, desk1: { x: 520, y: 900 }, desk2: { x: 1400, y: 900 }, teacher: { x: 1300, y: 770 } };
    S.layers.push({ id: 'room', z: 3, static: true, draw: (g, t, Pa) => {
      B.room(g, Pa, { floor: 'tiles' });
      P.rect(g, 520, 300, 880, 300, '#2f4a3d'); P.rect(g, 510, 290, 900, 10, '#a08868'); P.rect(g, 510, 600, 900, 14, '#a08868');
      if (o.board) P.text(g, o.board, 960, 440, { size: 64, font: SF.FONTS.hand, color: 'rgba(240,240,230,0.85)', weight: 500 });
      SF.props.clock(g, 1620, 320, 0.8, { hours: o.clock || 10.2 }, Pa);
      for (let i = 0; i < 2; i++) B.window(g, Pa, 1560 + i * 0, 420, 260, 200, { time: o.time, view: 'trees' });
    }});
    S.layers.push({ id: 'desks', z: -0.6, static: true, draw: (g, t, Pa) => { for (const x of [360, 1560]) B.table(g, Pa, x, 1160, 520, 230, { color: '#b8946a' }); } });
  });

  sets.gym = interior('gym', (S, o) => {
    S.amb = 'gym';
    S.marks = { rack: { x: 600, y: 780 }, bench: { x: 1200, y: 860 } };
    S.layers.push({ id: 'room', z: 3, static: true, draw: (g, t, Pa) => {
      B.room(g, Pa, { floor: 'tiles', wallpaper: 'panels' });
      P.rect(g, 140, 270, 1640, 260, rgba(Pa.glass, 0.5)); for (let x = 140; x < 1780; x += 82) P.rect(g, x, 270, 3, 260, rgba('#ffffff', 0.25));
      P.rect(g, 300, 610, 600, 18, Pa.dark); for (let i = 0; i < 8; i++) SF.props.dumbbell(g, 340 + i * 72, 600, 0.6, {});
    }});
    S.layers.push({ id: 'eq', z: 1.8, static: true, draw: (g, t, Pa) => { B.bench(g, Pa, 1200, 820, 1.3, {}); P.rect(g, 1500, 520, 14, 300, Pa.dark); P.rect(g, 1700, 520, 14, 300, Pa.dark); P.rect(g, 1460, 560, 300, 10, Pa.metal); } });
  });

  // ---- exteriors ----
  /** one-point perspective residential street: a sidewalk receding to the horizon, houses on the left, road on the right,
      lamp posts and trees along the kerb. o.variant 'city' swaps houses for shop fronts. Each lamp/tree is its own depth layer. */
  sets.street = (o = {}) => {
    const hor = o.horizon || 470, VX = o.vx || 900;
    const persp = (y) => Math.max(0.06, 0.95 * (y - hor) / (760 - hor));
    const zAt = (y) => (900 - y) / 60;
    const time = o.time || 'dusk';
    const set = { name: 'street', horizon: hor, floorY: 900, scaleAt: persp, zAt, surface: 'street', marks: { near: { x: 560, y: 1000 }, mid: { x: 760, y: 760 }, far: { x: 850, y: 560 }, center: { x: 700, y: 880 }, road: { x: 1500, y: 900 }, lamp: { x: 980, y: 820 } }, layers: [], amb: o.rain ? 'rain' : time === 'night' ? 'night_street' : 'street', time };
    const P2 = (x, y, k) => [VX + (x - VX) * k, hor + (y - hor) * k]; // point at depth factor k (1 = near plane y=1080 reference)
    const night = time !== 'day';
    set.layers.push({ id: 'sky', z: 14, static: true, draw: (g, t, Pa) => { B.sky(g, Pa, { time, stars: time === 'night' && !o.rain, clouds: time === 'day' }); B.cityline(g, Pa, hor + 4, { h: 70, lit: night, seed: 12, color: mixColor(Pa.sky[1], Pa.dark, 0.45) }); } });
    set.layers.push({ id: 'ground', z: 2.2, sortZ: 30, static: true, draw: (g, t, Pa) => {
      const road = shade(Pa.floor, night ? -0.35 : -0.2), walk = shade(Pa.floor, night ? -0.08 : 0.06), grass = shade(Pa.green, night ? -0.62 : -0.15), kerb = shade(Pa.trim, night ? -0.35 : -0.05);
      P.rect(g, -900, hor, 3720, 1000, grass);
      P.poly(g, [[VX + 4, hor], [VX + 16, hor], [3000, 1400], [1180, 1400]], road);               // road
      P.poly(g, [[VX + 1, hor], [VX + 4, hor], [1180, 1400], [1080, 1400]], kerb);                // kerb
      P.poly(g, [[VX - 10, hor], [VX - 2, hor], [880, 1400], [180, 1400]], walk);                 // sidewalk
      for (let i = 0; i < 26; i++) { const k = Math.pow(1.22, i) * 0.012; if (k > 2.2) break; const a = P2(180, 1400, k), b = P2(880, 1400, k); P.line(g, a[0], a[1], b[0], b[1], rgba('#000000', 0.12), Math.max(0.6, 2.2 * k)); }
      for (let i = 0; i < 16; i++) { const k0 = Math.pow(1.3, i) * 0.03, k1 = k0 * 1.12; const a = P2(1900, 1400, k0), b = P2(1900, 1400, k1); if (b[1] > hor + 1) P.poly(g, [[a[0] - 4 * k0 * 4, a[1]], [a[0] + 4 * k0 * 4, a[1]], [b[0] + 4 * k1 * 4, b[1]], [b[0] - 4 * k1 * 4, b[1]]], rgba('#e8e6df', night ? 0.35 : 0.7)); }
      if (o.rain || o.wet) { for (let i = 0; i < 9; i++) { const k = 0.25 + i * 0.12; const [x, y] = P2(1080 + 260, 1400, k); P.ell(g, x + 40 * k, y, 90 * k, 6 * k, rgba(Pa.light, 0.18)); } }
      // houses / shop fronts on the left, receding
      for (let i = 11; i >= 0; i--) {
        const k = 1 / (1 + i * 0.42), k2 = 1 / (1 + (i + 0.78) * 0.42);
        const a = P2(-120, 1400, k), b = P2(-120, 1400, k2);
        const h = (o.variant === 'city' ? 900 + (i % 3) * 160 : 520 + (i % 2) * 90) * k, h2 = h * (k2 / k);
        const col = shade(i % 2 ? Pa.wall : Pa.wall2, night ? -0.24 - i * 0.012 : -0.06 - i * 0.015);
        P.poly(g, [[a[0], a[1]], [b[0], b[1]], [b[0], b[1] - h2], [a[0], a[1] - h]], col);
        if (o.variant !== 'city') { const mx = (a[0] + b[0]) / 2, my = (a[1] - h + b[1] - h2) / 2; P.poly(g, [[a[0] - 6 * k, a[1] - h], [b[0], b[1] - h2], [mx, my - 150 * k]], shade(col, -0.25)); }
        for (let w = 0; w < 2; w++) {
          const f0 = 0.22 + w * 0.38, f1 = f0 + 0.2;
          const pa = [lerp(a[0], b[0], f0), lerp(a[1] - h * 0.62, b[1] - h2 * 0.62, f0)], pb = [lerp(a[0], b[0], f1), lerp(a[1] - h * 0.62, b[1] - h2 * 0.62, f1)];
          const wh = (h * lerp(1, k2 / k, f0)) * 0.24;
          const lit = night && rnd(i * 5 + w, 3) > 0.45;
          P.poly(g, [[pa[0], pa[1]], [pb[0], pb[1]], [pb[0], pb[1] + wh * (k2 / k)], [pa[0], pa[1] + wh]], lit ? rgba(Pa.light, 0.8) : rgba(Pa.glass, night ? 0.6 : 0.9));
        }
      }
      // far right: low houses beyond the road
      for (let i = 0; i < 8; i++) { const k = 1 / (1 + i * 0.6); const a = P2(3300, 1400, k), b = P2(3300, 1400, 1 / (1 + (i + 0.8) * 0.6)); P.poly(g, [[a[0], a[1] - 30 * k], [b[0], b[1] - 30 * k], [b[0], b[1] - 420 * k], [a[0], a[1] - 420 * k]], shade(Pa.wall2, night ? -0.5 : -0.2)); }
    }});
    // lamps and trees, grouped into three depth bands (near/mid/far): actors sort against each band, each band is cached once
    const lampK = [0.95, 0.62, 0.43, 0.31, 0.23, 0.17], treeK = [0.9, 0.6, 0.42, 0.3, 0.22, 0.16];
    set.lampPts = lampK.map((k) => P2(1040, 1400, k));
    const items = [];
    set.lampPts.forEach(([x, y], i) => items.push({ y, draw: (g, Pa) => B.streetLamp(g, Pa, x, y, lampK[i] * 1.5, { style: o.lampStyle }) }));
    treeK.forEach((k, i) => { const [x, y] = P2(o.variant === 'city' ? 1180 : -260, 1400, k); items.push({ y, draw: (g, Pa) => B.tree(g, Pa, x, y, k * 1.7, { leaf: o.leaf || (time === 'day' ? Pa.green : time === 'dusk' ? '#b0834a' : shade(Pa.green, -0.6)), bare: o.bare, trunk: shade(Pa.dark, -0.1) }) }); });
    B.depthBands(set, items, zAt);
    set.layers.push({ id: 'leaves', z: 0.5, sortZ: 25, static: true, draw: (g, t, Pa) => { if (o.leavesOnGround === false || time === 'night') return; for (let i = 0; i < 46; i++) { const k = 0.18 + rnd(i, 21) * 0.95; const [x, y] = P2(180 + rnd(i, 22) * 700, 1400, k); P.ell(g, x, y, 10 * k, 4.5 * k, rgba(o.leafColor || '#c08a49', 0.8)); } } });
    set.lights = (t, Pa) => (night ? set.lampPts.map(([x, y], i) => ({ type: 'lamp', x, y, s: lampK[i] * 1.5, a: 1 })) : []);
    return set;
  };

  /** side-scrolling street (facades parallel to the frame); walk long distances with camera tracking */
  sets.streetSide = (o = {}) => {
    const groundY = o.groundY || 900;
    const set = { name: 'streetSide', horizon: 600, floorY: groundY, scaleAt: () => o.s || 1.5, zAt: () => 0, marks: { start: { x: 200, y: groundY }, mid: { x: 1200, y: groundY }, end: { x: 3000, y: groundY } }, layers: [], amb: o.rain ? 'rain' : o.time === 'night' ? 'night_street' : 'street', time: o.time || 'day', infinite: true };
    set.layers.push({ id: 'sky', z: 30, draw: (g, t, Pa, v) => B.sky(g, Pa, { x0: v.x0 - 50, x1: v.x1 + 50, y0: -600, y1: groundY - 100, time: set.time, clouds: set.time === 'day', stars: set.time === 'night' }) });
    set.layers.push({ id: 'far', z: 9, draw: (g, t, Pa, v) => B.cityline(g, Pa, groundY - 210, { x0: Math.floor(v.x0 / 400) * 400 - 400, x1: v.x1 + 400, h: 220, lit: set.time !== 'day', seed: 31 }) });
    set.layers.push({ id: 'buildings', z: 2.4, draw: (g, t, Pa, v) => {
      const W = 420; const i0 = Math.floor(v.x0 / W) - 1, i1 = Math.ceil(v.x1 / W) + 1;
      for (let i = i0; i <= i1; i++) {
        const h = 380 + rnd(i, 41) * 260, col = [Pa.wall, Pa.wall2, shade(Pa.accent, -0.35), shade(Pa.wall, -0.1)][(i % 4 + 4) % 4];
        B.building(g, Pa, i * W, groundY - 120, W - 6, h, { color: col, lit: set.time !== 'day', shop: rnd(i, 42) > 0.4, shopLit: set.time !== 'day', awning: shade(Pa.accent2, -0.2) });
      }
      P.rect(g, v.x0 - 50, groundY - 120, v.x1 - v.x0 + 100, 120, shade(Pa.floor, 0.05)); // sidewalk
      for (let x = Math.floor(v.x0 / 90) * 90; x < v.x1 + 90; x += 90) P.rect(g, x, groundY - 120, 2, 120, rgba('#000000', 0.08));
    }});
    set.layers.push({ id: 'street', z: -0.3, draw: (g, t, Pa, v) => {
      P.rect(g, v.x0 - 50, groundY, v.x1 - v.x0 + 100, 26, shade(Pa.floor, -0.12));
      P.rect(g, v.x0 - 50, groundY + 26, v.x1 - v.x0 + 100, 600, shade(Pa.floor, -0.32));
      for (let x = Math.floor(v.x0 / 260) * 260; x < v.x1 + 260; x += 260) P.rect(g, x, groundY + 120, 120, 10, rgba('#e8e6df', 0.6));
    }});
    set.layers.push({ id: 'lamps', z: 0.8, draw: (g, t, Pa, v) => {
      const W = 700; for (let i = Math.floor(v.x0 / W) - 1; i <= Math.ceil(v.x1 / W) + 1; i++) { B.streetLamp(g, Pa, i * W + 120, groundY - 100, 1.25, {}); if (o.trees !== false && i % 2 === 0) B.tree(g, Pa, i * W + 470, groundY - 100, 1.3, { leaf: o.leaf || (set.time === 'day' ? Pa.green : '#b8894a'), bare: o.bare }); }
    }});
    set.lights = (t, Pa, v) => {
      const L = []; if (set.time === 'day') return L;
      const W = 700; for (let i = Math.floor((v ? v.x0 : -1000) / W) - 1; i <= Math.ceil((v ? v.x1 : 3000) / W) + 1; i++) L.push({ type: 'lamp', x: i * W + 120, y: groundY - 100, s: 1.25 });
      return L;
    };
    return set;
  };

  sets.park = (o = {}) => {
    const hor = o.horizon || 520, VX = 960;
    const persp = (y) => Math.max(0.06, 1.85 * (y - hor) / (900 - hor));
    const zAt = (y) => (900 - y) / 60;
    const time = o.time || 'day';
    const set = { name: 'park', horizon: hor, floorY: 900, scaleAt: persp, zAt, surface: 'grass', marks: { path: { x: 900, y: 900 }, far: { x: 960, y: 620 }, left: { x: 640, y: 900 }, right: { x: 1240, y: 900 } }, layers: [], amb: time === 'night' ? 'night_park' : 'park', time };
    const night = time === 'night';
    set.layers.push({ id: 'sky', z: 14, static: true, draw: (g, t, Pa) => { B.sky(g, Pa, { time, clouds: time === 'day', stars: night, sun: o.sun || null }); B.cityline(g, Pa, hor - 8, { h: 140, lit: time !== 'day', seed: 7 }); } });
    set.layers.push({ id: 'ground', z: 2.2, sortZ: 30, static: true, draw: (g, t, Pa) => {
      P.rect(g, -900, hor - 10, 3720, 1400, shade(Pa.green, night ? -0.55 : 0));
      g.fillStyle = P.lin(g, 0, hor, 0, 1080, [[0, rgba('#000000', 0.05)], [1, rgba('#000000', 0.22)]]); g.fillRect(-900, hor, 3720, 900);
      P.poly(g, [[VX - 18, hor], [VX + 18, hor], [1520, 1400], [380, 1400]], shade(Pa.floor, night ? -0.3 : 0.08));
      for (let i = 0; i < 60; i++) { const k = 0.1 + rnd(i, 31) * 0.9, x = -400 + rnd(i, 32) * 2700, y = hor + (1080 - hor) * k; P.ell(g, x, y, 22 * k, 6 * k, rgba('#000000', 0.06)); }
    }});
    const bx = o.benchX || 1310, by = o.benchY || 800;  // the bench; trees in front of it are left out so it stays visible
    const treePts = [];
    for (let i = 0; i < 10; i++) { const k = 1 / (1 + i * 0.45); treePts.push([VX + (-760 - 260 * (i % 2)) * k, hor + 600 * k, k]); treePts.push([VX + (780 + 240 * (i % 2)) * k, hor + 600 * k, k]); }
    B.depthBands(set, treePts.filter(([x, y, k]) => !(y > by - 60 && Math.abs(x - bx) < 300 + 220 * k)).map(([x, y, k], i) => ({ y, draw: (g, Pa) => B.tree(g, Pa, x, y, k * 1.45, { leaf: o.leaf || (night ? shade(Pa.green, -0.55) : shade(Pa.green, (i % 3) * 0.06)) }) })), zAt);
    Object.assign(set.marks, B.benchMarks(bx, by, persp(by)));
    set.layers.push({ id: 'bench', z: zAt(by) + 0.05, static: true, draw: (g, t, Pa) => { B.bench(g, Pa, bx, by, persp(by), {}); if (night || o.lamps) B.streetLamp(g, Pa, 1180, 860, 1.25, { style: 'lantern' }); } });
    set.lights = (t, Pa) => (night ? [{ type: 'glow', x: 1180, y: 380, r: 380, color: Pa.light, a: 0.8 }, { type: 'cone', x: 1180, y: 400, dir: 90, spread: 60, len: 520, color: Pa.light, a: 0.15 }] : []);
    return set;
  };

  /** Day One Films style void stage: black space, one spotlight, floor pool, haze */
  sets.stage = (o = {}) => {
    const set = { name: 'stage', horizon: 560, floorY: 900, scaleAt: () => o.s || 1.6, zAt: (y) => (900 - y) / 80, marks: { spot: { x: o.spotX || 960, y: 900 }, left: { x: 520, y: 900 }, right: { x: 1400, y: 900 } }, layers: [], amb: 'void' };
    set.layers.push({ id: 'void', z: 6, static: true, draw: (g, t, Pa) => {
      g.fillStyle = P.lin(g, 0, -400, 0, 1400, [[0, Pa.sky[0]], [0.6, Pa.sky[1]], [1, shade(Pa.floor, -0.2)]]); g.fillRect(-900, -400, 3720, 1800);
      P.ell(g, o.spotX || 960, 905, 560, 92, rgba(Pa.light, 0.12)); P.ell(g, o.spotX || 960, 905, 330, 52, rgba(Pa.light, 0.12));
    }});
    set.lights = (t, Pa) => (o.spot === false ? [] : [{ type: 'cone', x: o.spotX || 960, y: -60, dir: 90, spread: 22, len: 1050, color: Pa.light, a: o.spotA || 0.22 }, { type: 'glow', x: o.spotX || 960, y: 880, r: 520, color: Pa.light, a: 0.18 }]);
    return set;
  };

  /** metaphorical staircase rising to the right into light */
  sets.stairs = (o = {}) => {
    const n = o.steps || 9, sx = o.x || 420, sy = o.y || 960, w = o.w || 150, h = o.h || 70;
    const marks = {};
    for (let i = 0; i <= n; i++) marks['step' + i] = { x: sx + i * w + w * 0.5, y: sy - i * h };
    const set = { name: 'stairs', horizon: 500, floorY: sy, scaleAt: () => o.s || 1.1, zAt: () => 0, marks, layers: [], amb: 'void' };
    set.layers.push({ id: 'bg', z: 8, static: true, draw: (g, t, Pa) => { g.fillStyle = P.lin(g, 0, -300, 1920, 900, [[0, Pa.sky[0]], [1, Pa.sky[1]]]); g.fillRect(-900, -400, 3720, 1800); P.glow(g, sx + n * w + 200, sy - n * h - 100, 900, Pa.light, 0.8, 'screen'); } });
    set.layers.push({ id: 'steps', z: 0.2, static: true, draw: (g, t, Pa) => { for (let i = 0; i <= n; i++) { const x = sx + i * w, y = sy - i * h; P.rect(g, x, y, w + 2, 1400, shade(Pa.wall2, -0.25 + i * 0.03)); P.rect(g, x, y, w + 2, 10, shade(Pa.trim, 0.1 + i * 0.03)); } P.rect(g, -900, sy, sx + 900, 600, shade(Pa.wall2, -0.3)); } });
    return set;
  };

  /** horizon vista for payoffs: sunrise/sunset over a city or hills; a ledge to stand/sit on */
  sets.vista = (o = {}) => {
    const hor = o.horizon || 640;
    const set = { name: 'vista', horizon: hor, floorY: 900, scaleAt: () => o.s || 1.4, zAt: () => 0, marks: { ledge: { x: 820, y: 900 }, left: { x: 520, y: 900 }, right: { x: 1300, y: 900 } }, layers: [], amb: o.time === 'night' ? 'night_park' : 'wind', time: o.time || 'sunrise' };
    set.layers.push({ id: 'sky', z: 20, static: true, draw: (g, t, Pa) => { B.sky(g, Pa, { sun: o.sun === false ? null : [o.sunX || 1240, hor - (o.sunH || 60)], sunR: 640, stars: set.time === 'night' }); } });
    set.layers.push({ id: 'city', z: 8, static: true, draw: (g, t, Pa) => { if (o.hills) { P.ell(g, 500, hor + 160, 900, 220, shade(Pa.green, -0.35)); P.ell(g, 1500, hor + 180, 900, 240, shade(Pa.green, -0.45)); } else B.cityline(g, Pa, hor + 20, { h: 220, color: shade(Pa.dark, 0.15), lit: set.time === 'night', seed: 17 }); } });
    set.layers.push({ id: 'ledge', z: 0.3, static: true, draw: (g, t, Pa) => { P.rect(g, -900, 900, 3720, 600, shade(Pa.dark, 0.08)); P.rect(g, -900, 900, 3720, 14, shade(Pa.trim, -0.3)); } });
    return set;
  };

  /** plain coloured backdrop for title cards and abstract moments */
  sets.blank = (o = {}) => ({ name: 'blank', horizon: 500, floorY: 900, scaleAt: () => o.s || 1.6, zAt: () => 0, marks: {}, layers: [{ id: 'bg', z: 5, static: true, draw: (g, t, Pa) => { g.fillStyle = o.color || Pa.dark; g.fillRect(-900, -400, 3720, 1800); } }], amb: o.amb || 'void' });

  SF.SET_NAMES = Object.keys(sets);
})();
