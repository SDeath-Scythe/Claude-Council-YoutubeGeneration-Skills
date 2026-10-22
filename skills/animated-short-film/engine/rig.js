/* Character rig: proportions, pose solving with anatomical joint limits, IK, and drawing.
   Styles: 'silhouette' (ink body + thin rim, white face marks — the Last Soul look),
           'toon' (coloured clothes/skin, dark outline), 'shadow' (translucent inner-voice double).
   Angles are degrees measured from straight down; positive = forward (side view) or outward (front view). */
(function () {
  const SF = window.SF;
  const { clamp, lerp, rgba, shade } = SF;
  const P = SF.paint;
  const R2D = 180 / Math.PI, D2R = Math.PI / 180;
  const v = (a) => [Math.sin(a * D2R), Math.cos(a * D2R)]; // direction for angle a (deg) from down, +x forward

  // proportions measured from reference silhouettes: head ~27%, bean torso ~44%, short thick legs ~29% of height
  const BUILDS = {
    adult: { R: 41, torsoH: 131, shW: 88, hipW: 85, thigh: 44, shin: 42, ankle: 5, foot: 30, upper: 58, fore: 53, hand: 12, armW: 19, legW: 26 },
    slim: { R: 40, torsoH: 130, shW: 74, hipW: 70, thigh: 45, shin: 43, ankle: 5, foot: 29, upper: 58, fore: 53, hand: 11.5, armW: 16, legW: 22 },
    stocky: { R: 42, torsoH: 128, shW: 106, hipW: 104, thigh: 43, shin: 41, ankle: 5, foot: 31, upper: 57, fore: 52, hand: 13, armW: 22, legW: 30 },
    teen: { R: 40, torsoH: 112, shW: 76, hipW: 73, thigh: 38, shin: 36, ankle: 5, foot: 27, upper: 50, fore: 46, hand: 11, armW: 17, legW: 23 },
    kid: { R: 38, torsoH: 86, shW: 66, hipW: 66, thigh: 27, shin: 26, ankle: 4, foot: 22, upper: 38, fore: 35, hand: 10, armW: 15, legW: 20 },
    elder: { R: 40, torsoH: 126, shW: 84, hipW: 84, thigh: 42, shin: 40, ankle: 5, foot: 29, upper: 56, fore: 51, hand: 11.5, armW: 18, legW: 24, stoop: 7 },
  };

  // Joint limits per view. Side view: elbows only flex forward, knees only flex backward.
  const LIMITS = {
    side: { lean: [-35, 80], neck: [-40, 40], sh: [-75, 200], el: [0, 150], hp: [-50, 125], kn: [0, 155], an: [-35, 45] },
    front: { lean: [-25, 25], neck: [-35, 35], sh: [-30, 195], el: [-150, 150], hp: [-15, 70], kn: [-35, 35], an: [-30, 30] },
  };
  const JOINT_KEYS = ['shL', 'elL', 'shR', 'elR', 'hpL', 'knL', 'hpR', 'knR', 'anL', 'anR'];

  const DEFAULT_POSE = {
    x: 0, y: 0, rot: 0, lean: 0, neck: 0, turn: 0, nod: 0, squash: 1,
    shL: 7, elL: 0, shR: 7, elR: 0, hpL: 0, knL: 0, hpR: 0, knR: 0, anL: 0, anR: 0,
    foreL: 1, foreR: 1, fsL: 1, fsR: 1, ssL: 1, ssR: 1, handL: 'mitten', handR: 'mitten',
    face: 'neutral', blink: 0, lookX: 0, lookY: 0, mouth: 0, tears: 0,
  };

  // ---------- facing ----------
  function facingInfo(f) {
    switch (f) {
      case 'right': return { view: 'side', dir: 1, turn: 0 };
      case 'left': return { view: 'side', dir: -1, turn: 0 };
      case 'back': return { view: 'back', dir: 1, turn: 0 };
      case 'back-left': return { view: 'back', dir: -1, turn: -0.3 };
      case 'back-right': return { view: 'back', dir: 1, turn: 0.3 };
      case 'front-left': return { view: 'front', dir: -1, turn: -0.55 };
      case 'front-right': return { view: 'front', dir: 1, turn: 0.55 };
      default: return { view: 'front', dir: 1, turn: 0 };
    }
  }
  /** anatomical side ('L'|'R') nearest the camera for a facing; 'near'/'far' resolve through this */
  function sideOf(which, facing) {
    if (which === 'L' || which === 'R') return which;
    const f = facingInfo(facing);
    const near = f.view === 'side' ? (f.dir > 0 ? 'R' : 'L') : f.view === 'back' ? 'R' : 'R';
    return which === 'far' ? (near === 'R' ? 'L' : 'R') : near;
  }

  // ---------- constraints ----------
  function constrain(pose, view, who) {
    const L = view === 'side' ? LIMITS.side : LIMITS.front;
    const out = Object.assign({}, pose);
    const chk = (k, lim) => {
      const val = out[k];
      if (typeof val !== 'number' || isNaN(val)) { out[k] = DEFAULT_POSE[k] || 0; return; }
      const c = clamp(val, lim[0], lim[1]);
      if (Math.abs(c - val) > 2) {
        SF.log.violations.push({ who, joint: k, value: Math.round(val), limit: lim, view, shot: SF.ctx && SF.ctx.shot, t: SF.ctx && +(SF.ctx.t || 0).toFixed(2) });
        if (SF.log.violations.length > 2000) SF.log.violations.splice(0, 1000);
      }
      out[k] = c;
    };
    chk('lean', L.lean); chk('neck', L.neck);
    for (const s of ['L', 'R']) { chk('sh' + s, L.sh); chk('el' + s, L.el); chk('hp' + s, L.hp); chk('kn' + s, L.kn); chk('an' + s, L.an); }
    return out;
  }

  // ---------- two-bone IK (local coords, +x forward, y down) ----------
  /** returns absolute angles {a1,a2,reached}. bend: +1 joint in front (knees), -1 joint behind (elbows) */
  function ik2(ax, ay, tx, ty, l1, l2, bend) {
    let dx = tx - ax, dy = ty - ay; let d = Math.hypot(dx, dy);
    const reached = d <= l1 + l2 - 0.5;
    d = clamp(d, Math.abs(l1 - l2) + 0.5, l1 + l2 - 0.01);
    const base = Math.atan2(dx, dy) * R2D;
    const cosA = clamp((l1 * l1 + d * d - l2 * l2) / (2 * l1 * d), -1, 1);
    const alpha = Math.acos(cosA) * R2D;
    const a1 = base + bend * alpha;
    const e = v(a1); const ex = ax + e[0] * l1, ey = ay + e[1] * l1;
    const a2 = Math.atan2(tx - ex, ty - ey) * R2D;
    return { a1, a2, reached };
  }

  // ---------- skeleton solve ----------
  /** joint positions in local space (origin = ground point under pelvis, facing +x for side view) */
  function solve(ch, pose, view) {
    const B = ch.body;
    const sq = pose.squash || 1;
    const hipH = (B.thigh + B.shin) * 0.985 + B.ankle;
    const pel = [0, -hipH * sq + (pose.y || 0)];
    const lean = (view === 'side' ? pose.lean : pose.lean * 0.4) + (B.stoop || 0) * (view === 'side' ? 1 : 0.2);
    const up = view === 'side' ? [Math.sin(lean * D2R), -Math.cos(lean * D2R)] : [Math.sin(lean * D2R), -Math.cos(lean * D2R)];
    const rt = [-up[1], up[0]]; // perpendicular (screen right-ish)
    const tH = B.torsoH * sq;
    const shC = [pel[0] + up[0] * tH, pel[1] + up[1] * tH];
    const neck = (pose.neck || 0) + lean * 0.25;
    const hu = [Math.sin((lean + neck) * D2R), -Math.cos((lean + neck) * D2R)];
    const head = [shC[0] + hu[0] * B.R * 0.86 + (view === 'side' ? B.R * 0.08 : 0), shC[1] + hu[1] * B.R * 0.86 + (view === 'side' ? 0 : Math.max(0, pose.nod || 0) * B.R * 0.1)];
    const J = { pel, shC, head, up, rt, lean, neckAng: lean + neck, tH };
    const armY = B.armW * 0.95;
    const sides = view === 'side' ? { L: -1, R: 1 } : { L: 1, R: -1 }; // front view: character's L is screen-right
    for (const s of ['L', 'R']) {
      const sg = sides[s];
      let sh, hp;
      if (view === 'side') {
        sh = [shC[0] - up[0] * armY + up[0] * 0 + 2 + sg * 1.5, shC[1] - up[1] * armY];
        hp = [pel[0] + sg * 2.5, pel[1] - 3];
      } else {
        const ox = B.shW / 2 - B.armW * 0.55;
        sh = [shC[0] + rt[0] * ox * sg - up[0] * armY, shC[1] + rt[1] * ox * sg - up[1] * armY];
        const hx = B.hipW / 2 - B.legW * 0.62;
        hp = [pel[0] + sg * hx, pel[1] - 2];
      }
      // arm
      const f = pose['fore' + s] === undefined ? 1 : pose['fore' + s];
      let a1, a2;
      if (view === 'side') { a1 = lean + pose['sh' + s]; a2 = a1 + pose['el' + s]; }
      else { a1 = pose['sh' + s]; a2 = a1 + pose['el' + s]; }
      const u1 = view === 'side' ? v(a1) : [Math.sin(a1 * D2R) * sg, Math.cos(a1 * D2R)];
      const u2 = view === 'side' ? v(a2) : [Math.sin(a2 * D2R) * sg, Math.cos(a2 * D2R)];
      const el = [sh[0] + u1[0] * B.upper * f, sh[1] + u1[1] * B.upper * f];
      const wr = [el[0] + u2[0] * B.fore * f, el[1] + u2[1] * B.fore * f];
      J['sh' + s] = sh; J['el' + s] = el; J['wr' + s] = wr; J['armDir' + s] = u2;
      // leg
      let b1, b2;
      if (view === 'side') { b1 = lean * 0.15 + pose['hp' + s]; b2 = b1 - pose['kn' + s]; }
      else { b1 = pose['hp' + s]; b2 = b1 + pose['kn' + s]; }
      const w1 = view === 'side' ? v(b1) : [Math.sin(b1 * D2R) * sg, Math.cos(b1 * D2R)];
      const w2 = view === 'side' ? v(b2) : [Math.sin(b2 * D2R) * sg, Math.cos(b2 * D2R)];
      const fs = view === 'side' ? 1 : (pose['fs' + s] === undefined ? 1 : pose['fs' + s]);
      const kn = [hp[0] + w1[0] * B.thigh * fs, hp[1] + w1[1] * B.thigh * fs];
      const ss = view === 'side' ? 1 : (pose['ss' + s] === undefined ? 1 : pose['ss' + s]);
      const an = [kn[0] + w2[0] * B.shin * ss, kn[1] + w2[1] * B.shin * ss];
      J['hp' + s] = hp; J['kn' + s] = kn; J['an' + s] = an; J['shinAng' + s] = b2; J['sg' + s] = sg;
    }
    return J;
  }

  // ---------- expressions ----------
  // eyes: dot|arc|oval|half|closed|wide|glow ; brow: deg (+ = inner end up/sad, - = angry) ; mouth: none|smile|grin|frown|flat|o|open|wobble
  const EXPR = {
    neutral: { eyes: 'dot', es: 1, brow: null, mouth: 'none' },
    calm: { eyes: 'dot', es: 0.95, brow: 4, mouth: 'none' },
    happy: { eyes: 'arc', es: 1, brow: null, mouth: 'smile' },
    content: { eyes: 'arc', es: 1, brow: 6, mouth: 'none' },
    smile: { eyes: 'dot', es: 1, brow: null, mouth: 'smile' },
    grin: { eyes: 'arc', es: 1.05, brow: null, mouth: 'grin' },
    sad: { eyes: 'dot', es: 0.95, brow: 22, mouth: 'frown' },
    worried: { eyes: 'oval', es: 1.05, brow: 26, mouth: 'wobble' },
    tired: { eyes: 'half', es: 1, brow: 10, mouth: 'flat' },
    bored: { eyes: 'half', es: 0.9, brow: 0, mouth: 'flat' },
    surprised: { eyes: 'oval', es: 1.35, brow: 8, browUp: 1, mouth: 'o' },
    shock: { eyes: 'wide', es: 1.5, brow: 10, browUp: 1, mouth: 'o' },
    determined: { eyes: 'dot', es: 1, brow: -18, mouth: 'flat' },
    angry: { eyes: 'half', es: 1.05, brow: -30, mouth: 'frown' },
    cry: { eyes: 'closed', es: 1, brow: 26, mouth: 'frown', tears: 1 },
    teary: { eyes: 'dot', es: 1.05, brow: 24, mouth: 'wobble', tears: 0.5 },
    sleep: { eyes: 'closed', es: 1, brow: null, mouth: 'none' },
    blank: { eyes: 'dot', es: 0.75, brow: 0, mouth: 'none' },
    thinking: { eyes: 'dot', es: 1, brow: 14, mouth: 'flat', look: [0.6, -0.6] },
    proud: { eyes: 'arc', es: 1, brow: -4, mouth: 'smile' },
    hopeful: { eyes: 'oval', es: 1.08, brow: 14, mouth: 'smile' },
    glow: { eyes: 'glow', es: 1.1, brow: -20, mouth: 'none' },
  };
  SF.EXPRESSIONS = EXPR;

  function drawFace(g, ch, pose, J, view, P0, opts) {
    if (view === 'back') return;
    const B = ch.body, R = B.R, st = ch.style;
    const ex = EXPR[pose.face] || EXPR.neutral;
    const eyeCol = st === 'toon' ? '#141418' : opts.C.eye;
    const markCol = st === 'toon' ? '#141418' : opts.C.eye;
    const [hx, hy] = J.head;
    const turn = clamp((pose.turn || 0) + (opts.turn || 0), -1, 1);
    const look = ex.look || [0, 0];
    const lx = clamp((pose.lookX || 0) + look[0], -1, 1), ly = clamp((pose.lookY || 0) + look[1], -1, 1);
    const nod = pose.nod || 0;
    g.save(); g.translate(hx, hy); g.rotate((J.neckAng || 0) * D2R * (view === 'side' ? 1 : 0.6));
    let eyes;
    if (view === 'side') eyes = [[R * 0.52 + lx * R * 0.05, -R * 0.02 + ly * R * 0.05 + nod * R * 0.12]];
    else {
      const cx = turn * R * 0.4 + lx * R * 0.07, cy = R * 0.02 + ly * R * 0.07 + nod * R * 0.15;
      const sp = R * 0.36 * (1 - Math.abs(turn) * 0.3);
      eyes = [[cx - sp, cy], [cx + sp, cy]];
    }
    const es = ex.es * (ch.face.eyeSize || 1);
    const r0 = R * 0.105 * es;
    const blink = clamp(pose.blink || 0);
    const kind = blink > 0.6 ? 'closed' : ex.eyes;
    g.lineCap = 'round'; g.lineJoin = 'round';
    for (const [x, y] of eyes) {
      if (kind === 'dot') { P.ell(g, x, y, r0, r0 * (1.15 - blink * 0.9), eyeCol); if (st === 'toon') P.circle(g, x + r0 * 0.3, y - r0 * 0.35, r0 * 0.3, '#fff'); }
      else if (kind === 'oval') { P.ell(g, x, y, r0 * 1.05, r0 * 1.45 * (1 - blink * 0.8), eyeCol); if (st === 'toon') P.circle(g, x + r0 * 0.3, y - r0 * 0.4, r0 * 0.3, '#fff'); }
      else if (kind === 'wide') {
        P.ell(g, x, y, r0 * 1.25, r0 * 1.5, st === 'toon' ? '#fff' : eyeCol, 0, st === 'toon' ? '#141418' : null, 2);
        P.circle(g, x + lx * r0 * 0.4, y + ly * r0 * 0.4, r0 * 0.38, st === 'toon' ? '#141418' : opts.C.body);
      }
      else if (kind === 'arc') { g.beginPath(); g.arc(x, y + r0 * 0.7, r0 * 1.35, Math.PI * 1.15, Math.PI * 1.85); g.strokeStyle = markCol; g.lineWidth = r0 * 0.75; g.stroke(); }
      else if (kind === 'half') {
        g.save(); g.beginPath(); g.rect(x - r0 * 2, y - r0 * 0.1, r0 * 4, r0 * 3); g.clip();
        P.ell(g, x, y, r0 * 1.05, r0 * 1.2, eyeCol); g.restore();
        P.line(g, x - r0 * 1.25, y - r0 * 0.1, x + r0 * 1.25, y - r0 * 0.1, markCol, r0 * 0.45);
      }
      else if (kind === 'closed') { g.beginPath(); g.arc(x, y - r0 * 0.6, r0 * 1.25, Math.PI * 0.2, Math.PI * 0.8); g.strokeStyle = markCol; g.lineWidth = r0 * 0.6; g.stroke(); }
      else if (kind === 'glow') { P.glow(g, x, y, r0 * 6, opts.C.glow || '#ff5a4a', 0.9); P.ell(g, x, y, r0 * 1.2, r0 * 0.75, '#fff6f0'); }
    }
    // brows
    if (ex.brow !== null && ex.brow !== undefined && kind !== 'glow') {
      const by = -R * (0.26 + (ex.browUp ? 0.1 : 0)) + nod * R * 0.1;
      for (let i = 0; i < eyes.length; i++) {
        const [x] = eyes[i];
        const inner = view === 'side' ? 1 : i === 0 ? 1 : -1; // +1: inner end of this brow lies toward +x
        const a = ex.brow * D2R, L = R * 0.17, dy = Math.sin(a) * L, dx = Math.cos(a) * L;
        P.line(g, x - inner * dx, by + dy, x + inner * dx, by - dy, markCol, R * 0.06);
      }
    }
    // mouth
    const talk = clamp(pose.mouth || 0);
    const mx = view === 'side' ? R * 0.62 : turn * R * 0.38 + lx * R * 0.04, my = R * 0.42 + nod * R * 0.12;
    const mw = R * 0.16;
    let mouth = ex.mouth;
    if (talk > 0.05) mouth = 'talk';
    g.strokeStyle = markCol; g.lineWidth = R * 0.055; g.lineCap = 'round';
    if (mouth === 'smile') { g.beginPath(); g.arc(mx, my - mw * 0.7, mw, Math.PI * 0.2, Math.PI * 0.8); g.stroke(); }
    else if (mouth === 'grin') { g.beginPath(); g.arc(mx, my - mw * 0.9, mw * 1.2, Math.PI * 0.1, Math.PI * 0.9); g.closePath(); g.fillStyle = markCol; g.fill(); }
    else if (mouth === 'frown') { g.beginPath(); g.arc(mx, my + mw * 0.8, mw * 0.9, Math.PI * 1.25, Math.PI * 1.75); g.stroke(); }
    else if (mouth === 'flat') { P.line(g, mx - mw * 0.6, my, mx + mw * 0.6, my, markCol, R * 0.05); }
    else if (mouth === 'o') { P.ell(g, mx, my, mw * 0.32, mw * 0.42, markCol); }
    else if (mouth === 'wobble') { P.path(g, [[mx - mw * 0.7, my + 1], [mx - mw * 0.25, my - 2], [mx + mw * 0.2, my + 1.5], [mx + mw * 0.7, my - 1]], markCol, R * 0.045); }
    else if (mouth === 'talk') { P.ell(g, mx, my, mw * 0.45, mw * (0.12 + talk * 0.42), markCol); }
    // tears
    const tears = Math.max(ex.tears || 0, pose.tears || 0);
    if (tears > 0 && view !== 'back') {
      const tt = (opts.t || 0);
      for (let i = 0; i < eyes.length; i++) {
        const [x, y] = eyes[i];
        const len = R * (0.35 + 0.3 * tears) * (0.75 + 0.25 * Math.sin(tt * 3 + i));
        P.line(g, x, y + r0 * 1.2, x + (view === 'side' ? 0 : (i ? 1 : -1) * 1), y + r0 * 1.2 + len, rgba('#bfe3ff', 0.85 * tears), R * 0.045);
        const dy = ((tt * 0.9 + i * 0.37) % 1) * R * 0.9;
        P.circle(g, x, y + r0 * 1.4 + dy, R * 0.035, rgba('#d9f0ff', 0.9 * tears * (1 - dy / (R * 0.9))));
      }
    }
    g.restore();
  }

  // ---------- hands ----------
  function drawHand(g, ch, J, s, kind, fill, rimFn) {
    const B = ch.body; const [wx, wy] = J['wr' + s]; const d = J['armDir' + s];
    const hr = B.hand;
    const cx = wx + d[0] * hr * 0.35, cy = wy + d[1] * hr * 0.35;
    const shapes = [];
    shapes.push((x) => { x.beginPath(); x.arc(cx, cy, kind === 'fist' ? hr * 0.95 : hr, 0, Math.PI * 2); });
    const capsule = (ang, len, w) => (x) => {
      const ux = Math.cos(ang), uy = Math.sin(ang);
      x.beginPath(); x.moveTo(cx, cy); x.lineTo(cx + ux * len, cy + uy * len);
      x.lineWidth = w; x.lineCap = 'round';
    };
    const along = Math.atan2(d[1], d[0]);
    if (kind === 'point') shapes.push(['s', capsule(along, hr * 1.9, hr * 0.62)]);
    if (kind === 'up') shapes.push(['s', capsule(-Math.PI / 2 + (J.sg ? 0 : 0), hr * 1.95, hr * 0.62)]);
    if (kind === 'thumb') shapes.push(['s', capsule(-Math.PI / 2, hr * 1.5, hr * 0.62)]);
    if (kind === 'open') { shapes.push(['s', capsule(along - 0.9, hr * 1.1, hr * 0.6)]); shapes.push(['s', capsule(along + 0.25, hr * 1.4, hr * 1.25)]); }
    if (kind === 'peace') { shapes.push(['s', capsule(-Math.PI / 2 - 0.25, hr * 1.9, hr * 0.55)]); shapes.push(['s', capsule(-Math.PI / 2 + 0.25, hr * 1.9, hr * 0.55)]); }
    // rim pass then fill pass
    for (const pass of [0, 1]) {
      for (const sh of shapes) {
        if (Array.isArray(sh)) {
          sh[1](g);
          const w = g.lineWidth;
          if (pass === 0) { if (rimFn) { g.strokeStyle = rimFn(); g.lineWidth = w + ch.rimW * 2; g.stroke(); } }
          else { g.strokeStyle = fill; g.lineWidth = w; g.stroke(); }
        } else {
          sh(g);
          if (pass === 0) { if (rimFn) { g.strokeStyle = rimFn(); g.lineWidth = ch.rimW * 2; g.stroke(); } }
          else { g.fillStyle = fill; g.fill(); }
        }
      }
    }
    return [cx, cy];
  }

  // ---------- the character object ----------
  function character(spec) {
    const build = BUILDS[spec.build || 'adult'] || BUILDS.adult;
    const hm = spec.height || 1;
    const body = {};
    for (const k in build) body[k] = build[k] * (['R', 'armW', 'legW', 'hand', 'shW', 'hipW'].includes(k) ? Math.sqrt(hm) : hm);
    const ch = {
      name: spec.name || 'someone', id: spec.id || spec.name || 'someone',
      style: spec.style || 'silhouette', body, build: spec.build || 'adult',
      hair: spec.hair || null, wear: spec.wear || [], face: spec.face || {},
      colorsSpec: spec.colors || {}, wearColors: spec.wearColors || {}, rimW: spec.rimW || 2.3,
      spec,
    };
    ch.resolveColors = (Pal) => {
      const c = ch.colorsSpec, st = ch.style;
      const base = {
        body: c.body || (st === 'toon' ? '#2c3440' : Pal.ink),
        rim: c.rim || (st === 'toon' ? '#141418' : Pal.rim),
        eye: c.eye || '#f4f4f2',
        skin: c.skin || '#e9bf99', top: c.top || '#5b7fa6', bottom: c.bottom || '#3a3f4a', shoe: c.shoe || '#f2f2f2',
        hairCol: c.hair || (st === 'toon' ? '#2b2018' : Pal.ink), glow: c.glow || '#ff5a4a',
      };
      return base;
    };
    /** world position of head centre etc. for framing: returns {head:[x,y], chest:[x,y], feet:[x,y], hand:{L,R}} */
    ch.anchors = (pose, o = {}) => {
      const f = facingInfo(o.facing || 'front');
      const view = f.view === 'back' ? 'front' : f.view;
      const J = solve(ch, Object.assign({}, DEFAULT_POSE, pose), view);
      const s = o.s || 1, x = o.x || 0, y = o.y || 0, dir = f.view === 'side' ? f.dir : 1;
      const W = (p) => [x + p[0] * s * dir, y + p[1] * s];
      return { head: W(J.head), chest: W([(J.shC[0] + J.pel[0]) / 2, (J.shC[1] + J.pel[1]) / 2]), feet: [x, y], top: W([J.head[0], J.head[1] - ch.body.R]), handL: W(J.wrL), handR: W(J.wrR), J };
    };
    ch.draw = (g, pose, o = {}) => drawCharacter(g, ch, pose, o);
    return ch;
  }

  // ---------- accessories & hair ----------
  function drawHairBack(g, ch, J, view, fill, rim, t, vel) {
    const R = ch.body.R, [hx, hy] = J.head; const h = ch.hair;
    if (!h) return;
    g.save();
    const sway = clamp(-(vel || 0) * 0.04, -0.6, 0.6) + Math.sin(t * 2.1) * 0.05;
    const stroke = (fn) => { fn(); if (rim) { g.strokeStyle = rim; g.lineWidth = ch.rimW * 2; g.stroke(); } g.fillStyle = fill; g.fill(); };
    if (h === 'ponytail') {
      // tied at the back-top of the head; sticks out to the side in front view, trails behind in side view
      const side = view === 'side' ? -1 : 1;
      const bx = view === 'side' ? hx - R * 0.72 : view === 'back' ? hx : hx + R * 0.78, by = hy - R * 0.62;
      const sw = sway * R * 0.5;
      stroke(() => {
        g.beginPath();
        if (view === 'back') {
          g.moveTo(bx - R * 0.2, by); g.quadraticCurveTo(bx - R * 0.25 + sw, by + R * 0.8, bx + sw, by + R * 1.45);
          g.quadraticCurveTo(bx + R * 0.25 + sw, by + R * 0.8, bx + R * 0.2, by);
        } else {
          g.moveTo(bx - side * R * 0.05, by - R * 0.22);
          g.quadraticCurveTo(bx + side * R * 0.62 + sw, by - R * 0.1, bx + side * R * 0.5 + sw, by + R * 0.75);
          g.quadraticCurveTo(bx + side * R * 0.42 + sw, by + R * 1.15, bx + side * R * 0.3 + sw * 1.4, by + R * 1.35);
          g.quadraticCurveTo(bx + side * R * 0.22 + sw, by + R * 0.6, bx - side * R * 0.08, by + R * 0.18);
        }
        g.closePath();
      });
    } else if (h === 'long' || h === 'bob') {
      const L = h === 'long' ? R * 1.75 : R * 1.05;
      stroke(() => { P.rrPath(g, hx - R * 1.06, hy - R * 0.95, R * 2.12, L + R * 0.55, R * 0.95); });
    } else if (h === 'curly' || h === 'afro') {
      const rr = h === 'afro' ? R * 1.32 : R * 1.12;
      stroke(() => {
        g.beginPath();
        for (let i = 0; i <= 14; i++) { const a = (i / 14) * Math.PI * 2; const r = rr * (1 + 0.07 * Math.sin(i * 2.7)); const px = hx + Math.cos(a) * r, py = hy - R * 0.1 + Math.sin(a) * r * 0.95; i ? g.lineTo(px, py) : g.moveTo(px, py); }
        g.closePath();
      });
    }
    g.restore();
  }
  function drawHairFront(g, ch, J, view, fill, rim) {
    const R = ch.body.R, [hx, hy] = J.head; const h = ch.hair;
    if (!h) return;
    const sideSign = view === 'side' ? -1 : 0;
    if (h === 'bun') {
      const bx = view === 'side' ? hx - R * 0.55 : hx, by = hy - R * 1.02;
      if (rim) P.circle(g, bx, by, R * 0.36 + ch.rimW, rim);
      P.circle(g, bx, by, R * 0.36, fill);
    } else if (h === 'spiky') {
      g.beginPath();
      const n = 6;
      for (let i = 0; i <= n; i++) {
        const a = Math.PI * (1.05 + (i / n) * 0.9);
        const r = i % 2 ? R * 1.32 : R * 0.98;
        const px = hx + Math.cos(a) * r + sideSign * R * 0.12, py = hy + Math.sin(a) * r;
        i ? g.lineTo(px, py) : g.moveTo(px, py);
      }
      g.closePath(); if (rim) { g.strokeStyle = rim; g.lineWidth = ch.rimW * 2; g.stroke(); } g.fillStyle = fill; g.fill();
    } else if (h === 'short' || h === 'mohawk') {
      g.beginPath(); g.arc(hx + sideSign * R * 0.1, hy - R * 0.05, R * 1.07, Math.PI * 1.08, Math.PI * 1.92); g.closePath();
      if (rim) { g.strokeStyle = rim; g.lineWidth = ch.rimW * 2; g.stroke(); } g.fillStyle = fill; g.fill();
      if (h === 'mohawk') { P.rr(g, hx - R * 0.12, hy - R * 1.45, R * 0.24, R * 0.6, R * 0.1, fill, rim, ch.rimW * 2); }
    }
  }
  function drawWear(g, ch, J, view, C, Pal, t, layer) {
    const R = ch.body.R, [hx, hy] = J.head; const W = new Set(ch.wear);
    const col = (k, d) => ch.wearColors[k] || d;
    if (layer === 'head') {
      if (W.has('headband')) {
        g.save(); g.beginPath(); g.arc(hx, hy, R + 0.5, 0, Math.PI * 2); g.clip();
        const by = hy - R * 0.5;
        g.fillStyle = col('headband', '#efefea');
        if (view === 'side') { g.beginPath(); g.moveTo(hx - R * 1.1, by - R * 0.02); g.lineTo(hx + R * 1.1, by - R * 0.22); g.lineTo(hx + R * 1.1, by + R * 0.06); g.lineTo(hx - R * 1.1, by + R * 0.24); g.fill(); }
        else { g.beginPath(); g.moveTo(hx - R * 1.1, by + R * 0.08); g.quadraticCurveTo(hx, by - R * 0.12, hx + R * 1.1, by + R * 0.08); g.lineTo(hx + R * 1.1, by + R * 0.33); g.quadraticCurveTo(hx, by + R * 0.12, hx - R * 1.1, by + R * 0.33); g.fill(); }
        g.restore();
      }
      if (W.has('cap') || W.has('beanie')) {
        const c = col('cap', W.has('beanie') ? '#b0473e' : '#3e5c86');
        const fill = ch.style === 'silhouette' && !ch.wearColors.cap ? C.body : c;
        g.beginPath(); g.arc(hx, hy - R * 0.12, R * 1.04, Math.PI, 0); g.closePath();
        if (C.rimS) { g.strokeStyle = C.rimS; g.lineWidth = ch.rimW * 2; g.stroke(); } g.fillStyle = fill; g.fill();
        if (W.has('cap')) {
          if (view === 'side') P.rr(g, hx + R * 0.3, hy - R * 0.2, R * 1.05, R * 0.16, R * 0.08, fill, C.rimS, ch.rimW * 2);
          else if (view === 'front') P.ell(g, hx, hy - R * 0.14, R * 1.15, R * 0.2, fill, 0, C.rimS, ch.rimW * 2);
        } else P.rr(g, hx - R * 1.06, hy - R * 0.3, R * 2.12, R * 0.3, R * 0.12, shade(fill, -0.12), C.rimS, ch.rimW * 2);
      }
      if (W.has('glasses') && view !== 'back') {
        const gc = ch.style === 'toon' ? '#1a1a1a' : C.eye;
        g.save(); g.translate(hx, hy); g.lineWidth = R * 0.05; g.strokeStyle = gc;
        if (view === 'side') { P.rr(g, R * 0.36, -R * 0.2, R * 0.36, R * 0.32, R * 0.08, null, gc, R * 0.05); P.line(g, R * 0.36, -R * 0.08, -R * 0.4, -R * 0.12, gc, R * 0.04); }
        else { const tx = (J.turn || 0) * R * 0.4; for (const sx of [-1, 1]) P.rr(g, tx + sx * R * 0.28 - R * 0.19, -R * 0.17, R * 0.38, R * 0.34, R * 0.09, null, gc, R * 0.05); P.line(g, tx - R * 0.09, -R * 0.05, tx + R * 0.09, -R * 0.05, gc, R * 0.04); }
        g.restore();
      }
      if (W.has('beard') && view !== 'back') {
        const bc = ch.style === 'toon' ? col('beard', '#3b2a20') : C.body;
        g.beginPath(); const bx = view === 'side' ? hx + R * 0.35 : hx;
        g.arc(bx, hy + R * 0.25, R * (view === 'side' ? 0.6 : 0.78), 0.05 * Math.PI, 0.95 * Math.PI); g.closePath();
        g.fillStyle = bc; g.fill();
      }
    }
  }

  // ---------- main draw ----------
  /**
   * o: { x, y, s (scale), facing, P (palette), t, vel (horizontal velocity, px/s), alpha, hold: {L,R}: fn(g, x, y, ang, s) | prop name }
   */
  function drawCharacter(g, ch, poseIn, o = {}) {
    const Pal = o.P || SF.palette('day');
    const f = facingInfo(o.facing || 'front');
    const view = f.view === 'back' ? 'front' : f.view; // geometry
    const isBack = f.view === 'back';
    const pose = constrain(Object.assign({}, DEFAULT_POSE, poseIn), view, ch.id);
    if (f.turn && !poseIn.turn) pose.turn = f.turn;
    const J = solve(ch, pose, view); J.turn = pose.turn;
    const C = ch.resolveColors(Pal);
    const st = ch.style;
    const rimA = st === 'silhouette' ? (o.rimA === undefined ? 0.85 : o.rimA) : 1;
    C.rimS = st === 'shadow' ? null : rgba(C.rim, rimA);
    const rimFn = C.rimS ? () => C.rimS : null;
    const s = o.s || 1;
    const B = ch.body;
    const t = o.t || 0;

    g.save();
    g.translate(o.x || 0, o.y || 0);
    if (pose.rot) g.rotate(pose.rot * D2R);
    g.scale(s * (view === 'side' ? f.dir : 1), s);
    if (o.alpha !== undefined) g.globalAlpha *= o.alpha;
    if (st === 'shadow') { g.globalAlpha *= o.shadowA || 0.72; }

    const fills = {
      body: st === 'toon' ? C.top : C.body,
      leg: st === 'toon' ? C.bottom : C.body,
      skin: st === 'toon' ? C.skin : C.body,
      head: st === 'toon' ? C.skin : C.body,
      foot: st === 'toon' ? '#2a2a2e' : C.body,
    };
    const W = new Set(ch.wear);
    const coat = W.has('raincoat') || W.has('hoodie') || W.has('coat') ? (ch.wearColors.raincoat || ch.wearColors.hoodie || ch.wearColors.coat || (W.has('raincoat') ? '#e7c14a' : '#5b6d86')) : null;
    if (coat) { fills.body = coat; }
    const armFill = coat || (st === 'toon' ? C.top : C.body);

    const limb = (pts, w, fill) => {
      g.lineCap = 'round'; g.lineJoin = 'round';
      g.beginPath(); g.moveTo(pts[0][0], pts[0][1]); for (let i = 1; i < pts.length; i++) g.lineTo(pts[i][0], pts[i][1]);
      if (C.rimS) { g.strokeStyle = C.rimS; g.lineWidth = w + ch.rimW * 2; g.stroke(); }
      g.strokeStyle = fill; g.lineWidth = w; g.stroke();
    };
    const drawArm = (sd) => {
      const pts = [J['sh' + sd], J['el' + sd], J['wr' + sd]];
      limb(pts, B.armW, armFill);
      if (st === 'toon' && !coat) { /* sleeves: upper arm shirt, forearm skin */ limb([J['el' + sd], J['wr' + sd]], B.armW * 0.92, C.skin); }
      const handKind = pose['hand' + sd] || 'mitten';
      const hc = drawHand(g, ch, J, sd, handKind, st === 'toon' ? C.skin : C.body, rimFn);
      const hold = o.hold && o.hold[sd];
      if (hold) {
        const d = J['armDir' + sd];
        const ang = Math.atan2(d[1], d[0]);
        if (typeof hold === 'function') hold(g, hc[0], hc[1], ang, B.hand / 10.5, view, C);
        else if (SF.held && SF.held[hold.type || hold]) SF.held[hold.type || hold](g, hc[0], hc[1], ang, B.hand / 10.5, Object.assign({ view, t, P: Pal, C }, hold));
      }
    };
    const drawLeg = (sd) => {
      const hp = J['hp' + sd], kn = J['kn' + sd], an = J['an' + sd];
      limb([hp, kn, an], B.legW, fills.leg);
      // foot
      g.save(); g.translate(an[0], an[1]);
      const sneaker = W.has('sneakers');
      if (view === 'side') {
        const fa = (pose['an' + sd] || 0) * D2R;
        g.rotate(-fa);
        const fw = B.foot, fh = B.legW * 0.62;
        P.rrPath(g, -fw * 0.3, -fh * 0.55, fw, fh, fh * 0.48);
        if (C.rimS) { g.strokeStyle = C.rimS; g.lineWidth = ch.rimW * 2; g.stroke(); }
        g.fillStyle = fills.foot; g.fill();
        if (sneaker) P.rr(g, -fw * 0.3, fh * 0.12, fw, fh * 0.34, fh * 0.17, ch.wearColors.sneakers || C.shoe);
      } else {
        const sg = J['sg' + sd];
        const fw = B.legW * 1.22, fh = B.legW * 0.62;
        P.ell(g, sg * B.legW * 0.12, fh * 0.15, fw / 2 + (C.rimS ? ch.rimW : 0), fh / 2 + (C.rimS ? ch.rimW : 0), C.rimS || fills.foot);
        P.ell(g, sg * B.legW * 0.12, fh * 0.15, fw / 2, fh / 2, fills.foot);
        if (sneaker) P.ell(g, sg * B.legW * 0.12, fh * 0.42, fw / 2, fh * 0.2, ch.wearColors.sneakers || C.shoe);
      }
      g.restore();
    };
    const drawTorso = () => {
      const { pel, up, rt } = J;
      const tH = J.tH;
      const w1 = view === 'side' ? B.shW * 0.8 : B.shW, w2 = view === 'side' ? B.hipW * 0.84 : B.hipW;
      g.save(); g.translate(pel[0], pel[1]); g.rotate(Math.atan2(up[0], -up[1]));
      const top = -tH, bot = 7, r1 = w1 * 0.42, r2 = w2 * 0.28;
      g.beginPath();
      g.moveTo(-w1 / 2 + r1, top); g.lineTo(w1 / 2 - r1, top); g.quadraticCurveTo(w1 / 2, top, w1 / 2, top + r1);
      g.lineTo(w2 / 2, bot - r2); g.quadraticCurveTo(w2 / 2, bot, w2 / 2 - r2, bot);
      g.lineTo(-w2 / 2 + r2, bot); g.quadraticCurveTo(-w2 / 2, bot, -w2 / 2, bot - r2);
      g.lineTo(-w1 / 2, top + r1); g.quadraticCurveTo(-w1 / 2, top, -w1 / 2 + r1, top); g.closePath();
      if (C.rimS) { g.strokeStyle = C.rimS; g.lineWidth = ch.rimW * 2; g.stroke(); }
      g.fillStyle = fills.body; g.fill();
      // clothing details
      if (W.has('apron') && view !== 'side' && !isBack) P.rr(g, -w2 * 0.36, top + tH * 0.38, w2 * 0.72, tH * 0.62, 6, ch.wearColors.apron || 'rgba(235,235,230,0.9)');
      if (W.has('tie') && view !== 'side' && !isBack) { P.poly(g, [[-4, top + 6], [4, top + 6], [7, top + tH * 0.55], [0, top + tH * 0.62], [-7, top + tH * 0.55]], ch.wearColors.tie || '#9b2f2f'); }
      if (coat && W.has('raincoat')) { P.rect(g, -w2 / 2 + 2, top + tH * 0.66, w2 - 4, 5, rgba('#ffffff', 0.55)); if (view !== 'side' && !isBack) P.line(g, 0, top + 10, 0, bot - 4, shade(coat, -0.18), 2); }
      if (W.has('skirt')) { P.poly(g, [[-w2 / 2 - 2, bot - 18], [w2 / 2 + 2, bot - 18], [w2 / 2 + 16, bot + 26], [-w2 / 2 - 16, bot + 26]], ch.wearColors.skirt || fills.body, C.rimS, ch.rimW * 2); }
      if (W.has('scarf')) P.rr(g, -w1 / 2 + 2, top - 2, w1 - 4, 14, 7, ch.wearColors.scarf || '#b54a3c');
      if (st === 'toon' && W.has('hood')) { /* nothing extra */ }
      g.restore();
      if (W.has('backpack') && (view === 'side' || isBack)) {
        const bx = view === 'side' ? -w1 * 0.62 : -w1 * 0.36, bw = view === 'side' ? w1 * 0.36 : w1 * 0.72;
        g.save(); g.translate(pel[0], pel[1]); g.rotate(Math.atan2(up[0], -up[1]));
        P.rr(g, bx, -tH * 0.9, bw, tH * 0.68, 10, ch.wearColors.backpack || (st === 'silhouette' ? C.body : '#7a5a3a'), C.rimS, ch.rimW * 2);
        g.restore();
      }
    };
    const drawHead = () => {
      const [hx, hy] = J.head; const R = B.R;
      const hairFill = st === 'toon' ? C.hairCol : C.body;
      drawHairBack(g, ch, J, isBack ? 'back' : view, hairFill, C.rimS, t, (o.vel || 0) * (view === 'side' ? f.dir : 1));
      const hood = W.has('raincoat') || W.has('hood');
      if (hood) { P.circle(g, hx, hy, R * 1.12 + (C.rimS ? ch.rimW : 0), C.rimS || coat); P.circle(g, hx, hy, R * 1.12, coat || fills.body); }
      if (C.rimS) P.circle(g, hx, hy, R + ch.rimW, C.rimS);
      P.circle(g, hx, hy, R, fills.head);
      if (hood) { // face opening
        g.save(); g.beginPath(); g.arc(hx, hy, R * 1.12, 0, Math.PI * 2); g.clip();
        if (!isBack) P.ell(g, hx + (view === 'side' ? R * 0.55 : (pose.turn || 0) * R * 0.3), hy + R * 0.12, R * (view === 'side' ? 0.55 : 0.78), R * 0.82, st === 'toon' ? C.skin : C.body);
        else P.ell(g, hx, hy, R * 0.9, R * 0.9, shade(coat, -0.08));
        g.restore();
      }
      if (!isBack) drawFace(g, ch, pose, J, view, Pal, { t, turn: 0, C });
      if (!hood) drawHairFront(g, ch, J, view, hairFill, C.rimS);
      drawWear(g, ch, J, view, C, Pal, t, 'head');
      if (st === 'shadow' && !isBack) { /* glowing eyes already via face 'glow' */ }
    };

    // draw order
    if (view === 'side') {
      const near = 'R', far = 'L';
      drawArm(far); drawLeg(far); drawTorso(); drawLeg(near); drawHead(); drawArm(near);
    } else if (isBack) {
      drawLeg('L'); drawLeg('R'); drawTorso(); drawArm('L'); drawArm('R'); drawHead();
    } else {
      drawLeg('L'); drawLeg('R'); drawTorso();
      // seated, seen from the front: thighs come toward the camera — draw the lap so the pose reads as sitting
      if ((pose.fsL || 1) < 0.6 || (pose.fsR || 1) < 0.6) {
        const [px, py] = J.pel, lw = B.hipW * 1.04, lh = B.thigh * Math.max(0.3, Math.min(pose.fsL || 1, pose.fsR || 1)) + B.legW * 0.35;
        P.rrPath(g, px - lw / 2, py - 10, lw, lh + 10, B.legW * 0.55);
        if (C.rimS) { g.strokeStyle = C.rimS; g.lineWidth = ch.rimW * 2; g.stroke(); }
        g.fillStyle = fills.leg; g.fill();
        P.line(g, px, py + lh * 0.25, px, py + lh, C.rimS || 'rgba(255,255,255,0.3)', ch.rimW * 1.2);
      }
      // arms that cross in front of the body draw after the torso; arms hanging at sides are fine either way
      drawArm('L'); drawArm('R'); drawHead();
      // re-draw hands that are raised in front of the face so they read
      for (const sd of ['L', 'R']) if (J['wr' + sd][1] < J.head[1] + B.R * 0.6 && Math.abs(J['wr' + sd][0] - J.head[0]) < B.R) drawArm(sd);
    }
    g.restore();
    return J;
  }

  /** contact shadow under a character at world (x,y) */
  function drawShadow(g, ch, o) {
    const s = o.s || 1, Pal = o.P || SF.palette('day');
    P.shadow(g, o.x, (o.y || 0) + 2 * s, ch.body.shW * 0.85 * s, 9 * s, (Pal.shadowA || 0.25) * (o.alpha === undefined ? 1 : o.alpha));
  }

  SF.rig = { BUILDS, LIMITS, DEFAULT_POSE, EXPR, JOINT_KEYS, facingInfo, sideOf, constrain, solve, ik2, character, drawCharacter, drawShadow, v };
  SF.character = character;
})();
