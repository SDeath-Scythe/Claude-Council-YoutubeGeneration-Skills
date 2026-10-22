/* Film runtime: shot list -> frames. Camera (framing shorthands, handheld, shake), 2.5D layers with parallax and
   depth-of-field blur (static layers cached per shot), lights, grade, vignette, grain, captions, titles, transitions.
   Also exports the timeline (chapters, captions, sfx cues incl. automatic footsteps) for sound, QA and packaging. */
(function () {
  const SF = window.SF;
  const { clamp, lerp, ev, rgba, shade, mixColor, noise2, rnd, track, isTrack } = SF;
  const P = SF.paint;

  const FILM = (SF.FILM = { cfg: null, shots: [], cast: {}, prepared: false });
  const DEFAULT_LOOK = { dof: 1.7, parallax: 0.12, vignette: 0.55, grain: 0.03, grainStep: 3, rim: true, captions: { size: 54, color: '#ffffff', stroke: '#15171c', band: 0.5, font: null } };

  SF.film = (cfg) => {
    FILM.cfg = Object.assign({ title: 'Untitled', fps: 30, size: [1920, 1080], palette: 'day', chapters: [], music: {}, fadeIn: 1.0, fadeOut: 2.0 }, cfg);
    FILM.cfg.look = Object.assign({}, DEFAULT_LOOK, cfg.look || {});
    FILM.cfg.look.captions = Object.assign({}, DEFAULT_LOOK.captions, (cfg.look && cfg.look.captions) || {});
    if (cfg.cast) for (const k in cfg.cast) FILM.cast[k] = cfg.cast[k].body ? cfg.cast[k] : SF.character(Object.assign({ id: k }, cfg.cast[k]));
    return FILM.cfg;
  };
  /** add shots; defaults (e.g. {ch: 2, set: 'kitchen', setOpts:{time:'night'}}) merge into each */
  SF.add = (defaults, list) => {
    if (Array.isArray(defaults)) { list = defaults; defaults = {}; }
    const src = (document.currentScript && document.currentScript.getAttribute('src')) || '';
    for (const s of list) FILM.shots.push(Object.assign({}, defaults, s, { src, setOpts: Object.assign({}, defaults.setOpts || {}, s.setOpts || {}) }));
  };

  const TOD_PAL = { day: 'day', morning: 'day', overcast: 'overcast', dusk: 'dusk', evening: 'warm', warm: 'warm', night: 'night', sunrise: 'sunrise', sunset: 'sunrise', void: 'void', cold: 'cold' };

  // ---------- preparation ----------
  function prepare() {
    const cfg = FILM.cfg; if (!cfg) throw new Error('SF.film({...}) was never called');
    const fps = cfg.fps;
    let tAcc = 0;
    FILM.shots.forEach((s, i) => {
      s.index = i; s.id = s.id || 'shot' + (i + 1); s.dur = Math.max(0.2, +s.dur || 3);
      s.start = tAcc; s.end = tAcc + s.dur; s.f0 = Math.round(s.start * fps); s.f1 = Math.round(s.end * fps); tAcc = s.end;
      s.ch = s.ch || 1;
      s.capList = normCaps(s);
    });
    FILM.duration = tAcc; FILM.frames = Math.round(tAcc * fps);
    FILM.rt = new Map();
    FILM.prepared = true;
  }
  function normCaps(s) {
    const out = [];
    for (const c of s.caps || []) {
      const o = Array.isArray(c) ? { t: c[0], who: c[1], text: c[2], ...(c[3] || {}) } : Object.assign({}, c);
      o.dur = o.dur || SF.acting.autoDur(o.text);
      out.push(o);
    }
    // actor 'say' actions become captions too
    for (const who in s.cast || {}) for (const a of (s.cast[who].act || [])) {
      const e = Array.isArray(a) ? { t: a[0], verb: a[1], a: a[2], b: a[3] } : a;
      if (e.verb === 'say') out.push({ t: e.t, who, text: e.a, dur: (e.b && e.b.dur) || SF.acting.autoDur(e.a), pos: e.b && e.b.pos });
    }
    return out.sort((a, b) => a.t - b.t);
  }
  function shotAtFrame(f) {
    const S = FILM.shots; let lo = 0, hi = S.length - 1;
    while (lo < hi) { const mid = (lo + hi + 1) >> 1; if (S[mid].f0 <= f) lo = mid; else hi = mid - 1; }
    return S[lo];
  }

  // ---------- per-shot runtime (set instance, palette, actor specs) ----------
  function runtime(shot) {
    let R = FILM.rt.get(shot.index);
    if (R) return R;
    const cfg = FILM.cfg;
    const time = shot.time || (shot.setOpts && shot.setOpts.time);
    let palName = shot.palette || TOD_PAL[time] || cfg.palette;
    let Pa = typeof palName === 'object' && !Array.isArray(palName) ? palName : Array.isArray(palName) ? SF.palette(palName[0], palName[1], palName[2]) : SF.palette(palName);
    let set = null;
    if (!shot.insert) {
      const opts = Object.assign({ time }, shot.setOpts || {});
      if (typeof shot.set === 'function') set = shot.set(opts, Pa);
      else if (typeof shot.set === 'string' && SF.sets[shot.set]) set = SF.sets[shot.set](opts);
      else if (shot.set && typeof shot.set === 'object') set = shot.set;
      else { if (shot.set) SF.warn('set', 'unknown set "' + shot.set + '" in shot ' + shot.id); set = SF.sets.blank({}); }
    } else set = { name: 'insert', layers: [], marks: {}, scaleAt: () => 1, zAt: () => 0, floorY: 900, amb: shot.amb || null };
    const actors = [];
    for (const id in shot.cast || {}) {
      const spec = Object.assign({}, shot.cast[id]);
      spec.char = spec.char || FILM.cast[id];
      if (!spec.char) { SF.warn('cast', 'no cast member "' + id + '" (shot ' + shot.id + ')'); continue; }
      actors.push({ id, spec });
    }
    const scene = { marks: Object.assign({}, set.marks || {}, shot.marks || {}), scaleAt: set.scaleAt, floorY: set.floorY, actorsAt: {} };
    for (const a of actors) { const p = SF.acting.resolveX(a.spec.at !== undefined ? a.spec.at : 960, scene); scene.actorsAt[a.id] = { x: p.x, y: p.y !== undefined ? p.y : set.floorY }; }
    R = { set, Pa, actors, scene, cache: new Map() };
    FILM.rt.set(shot.index, R);
    if (FILM.rt.size > 6) { const k = FILM.rt.keys().next().value; if (k !== shot.index) FILM.rt.delete(k); }
    return R;
  }

  // ---------- camera ----------
  const CHAR_H = 300;
  function frameOn(a, kind, o = {}) {
    const H = CHAR_H * a.s;
    const T = { wide: [0.5, 1.6], full: [0.5, 1.3], knees: [0.62, 0.95], medium: [0.68, 0.78], close: [0.83, 0.46], ecu: [0.87, 0.24], feet: [0.06, 0.4], hands: [0.45, 0.42] }[kind] || [0.68, 0.78];
    const zoom = clamp(1080 / (H * T[1]), 1, 9) * (o.zoomMul || 1);
    let x = a.x, y = a.y - H * T[0];
    if (o.side === 'left') x += (1920 / zoom) * 0.17; else if (o.side === 'right') x -= (1920 / zoom) * 0.17;
    return { x: x + (o.dx || 0), y: y + (o.dy || 0), zoom, rot: o.rot || 0 };
  }
  function camSpec(spec, t, R, shot) {
    if (spec === undefined || spec === null || spec === 'wide') return { x: 960, y: 540, zoom: 1, rot: 0 };
    if (typeof spec === 'string') {
      const [kind, who, side] = spec.split(':');
      if (kind === 'mark') { const m = R.scene.marks[who]; return m ? { x: m.x, y: m.y - 300, zoom: 1.6, rot: 0 } : { x: 960, y: 540, zoom: 1, rot: 0 }; }
      if (kind === 'two') { const [aa, bb] = who.split('+').map((id) => actorState(R, id, t, shot)); if (!aa || !bb) return { x: 960, y: 540, zoom: 1, rot: 0 }; const H = CHAR_H * Math.max(aa.s, bb.s); const span = Math.abs(aa.x - bb.x) + H * 0.9; const zoom = clamp(Math.min(1920 / span, 1080 / (H * 1.25)), 1, 6); return { x: (aa.x + bb.x) / 2, y: (aa.y + bb.y) / 2 - H * 0.55, zoom, rot: 0 }; }
      const a = actorState(R, who, t, shot);
      if (!a) { SF.warn('cam', 'camera target "' + who + '" not in shot ' + shot.id); return { x: 960, y: 540, zoom: 1, rot: 0 }; }
      return frameOn(a, kind, { side });
    }
    if (spec.frame || spec.on) {
      const a = actorState(R, spec.on, spec.lock ? 0 : t, shot);
      if (a) return Object.assign(frameOn(a, spec.frame || 'medium', spec), spec.zoom ? { zoom: spec.zoom } : {});
    }
    return { x: spec.x === undefined ? 960 : spec.x, y: spec.y === undefined ? 540 : spec.y, zoom: spec.zoom === undefined ? 1 : spec.zoom, rot: spec.rot || 0 };
  }
  function cameraAt(shot, t, R) {
    let c;
    const cs = shot.cam;
    if (Array.isArray(cs) && cs.length && Array.isArray(cs[0])) {
      let i = 0; while (i < cs.length - 1 && cs[i + 1][0] <= t) i++;
      const a = cs[i], b = cs[Math.min(i + 1, cs.length - 1)];
      const A = camSpec(a[1], t, R, shot);
      if (b === a || t <= a[0]) c = A;
      else { const B2 = camSpec(b[1], t, R, shot); const k = SF.E(b[2] || 'inOut')(clamp((t - a[0]) / Math.max(1e-6, b[0] - a[0]))); c = { x: lerp(A.x, B2.x, k), y: lerp(A.y, B2.y, k), zoom: Math.exp(lerp(Math.log(A.zoom), Math.log(B2.zoom), k)), rot: lerp(A.rot, B2.rot, k) }; }
    } else c = camSpec(cs, t, R, shot);
    // gentle drift keeps held shots alive; handheld adds more
    const hh = shot.handheld === undefined ? (FILM.cfg.look.handheld === undefined ? 0.35 : FILM.cfg.look.handheld) : shot.handheld;
    if (hh > 0) { const sd = shot.index * 13.1; c.x += noise2(t * 0.45, sd) * 7 * hh / c.zoom; c.y += noise2(t * 0.41, sd + 3) * 5 * hh / c.zoom; c.rot += noise2(t * 0.3, sd + 9) * 0.25 * hh; }
    for (const sk of shot.shake || []) { const u = t - sk.t; if (u >= 0 && u < (sk.dur || 0.5)) { const a = (sk.amp || 12) * (1 - u / (sk.dur || 0.5)); c.x += Math.sin(u * 61) * a / c.zoom; c.y += Math.cos(u * 47) * a / c.zoom; } }
    return c;
  }
  function actorState(R, id, t, shot) {
    const a = R.actors.find((x) => x.id === id);
    if (!a) return null;
    const key = id + '@' + t.toFixed(4);
    R._ac = R._ac || new Map();
    if (R._ac.has(key)) return R._ac.get(key);
    const st = SF.acting.actorAt(a.spec, t, R.scene, id);
    if (R._ac.size > 64) R._ac.clear();
    R._ac.set(key, st);
    return st;
  }

  // ---------- layer transforms ----------
  function layerXf(cam, z, par, sc, W, H) {
    const pz = 1 / Math.max(0.2, 1 + z * par);
    const zEff = Math.max(0.05, 1 + (cam.zoom - 1) * pz);
    const cx = cam.x * pz + 960 * (1 - pz), cy = cam.y * pz + 540 * (1 - pz);
    return { pz, zEff, cx, cy, s: sc * zEff, rot: (cam.rot || 0) * Math.PI / 180, W, H };
  }
  function applyXf(g, X) {
    g.setTransform(1, 0, 0, 1, 0, 0);
    g.translate(X.W / 2, X.H / 2); if (X.rot) g.rotate(X.rot); g.scale(X.s, X.s); g.translate(-X.cx, -X.cy);
  }
  function xfInto(x, X, k) { // like applyXf but for a scratch canvas scaled by k relative to the frame
    x.setTransform(k, 0, 0, k, 0, 0);
    x.translate(X.W / 2, X.H / 2); if (X.rot) x.rotate(X.rot); x.scale(X.s, X.s); x.translate(-X.cx, -X.cy);
  }
  function visRect(X) { const hw = X.W / 2 / X.s, hh = X.H / 2 / X.s, m = X.rot ? 1.25 : 1.02; return { x0: X.cx - hw * m, x1: X.cx + hw * m, y0: X.cy - hh * m, y1: X.cy + hh * m }; }

  // ---------- one shot at local time t into ctx ----------
  function drawShot(g, shot, t, opt = {}) {
    const cfg = FILM.cfg, look = cfg.look;
    const W = g.canvas.width, H = g.canvas.height, sc = W / 1920;
    const R = runtime(shot);
    const Pa = R.Pa, set = R.set;
    SF.ctx = { shot: shot.id, t };
    const cam = cameraAt(shot, t, R);
    const par = shot.parallax === undefined ? look.parallax : shot.parallax;
    const actors = R.actors.map((a) => ({ id: a.id, spec: a.spec, st: actorState(R, a.id, t, shot) }));
    const zAt = set.zAt || (() => 0);
    // focus
    let focus = shot.focus;
    if (typeof focus === 'string') { const fa = actors.find((a) => a.id === focus); focus = fa ? (fa.spec.z !== undefined ? fa.spec.z : zAt(fa.st.y)) : 0; }
    else if (isTrack(focus)) focus = track(focus, t);
    const focal = actors.filter((a) => !a.spec.ots);
    if (focus === undefined) focus = focal.length ? (focal[0].spec.z !== undefined ? focal[0].spec.z : focal[0].st.z !== undefined ? focal[0].st.z : zAt(focal[0].st.y)) : (shot.insert ? 0 : 1.2);
    const dof = shot.dof === undefined ? look.dof : shot.dof;
    const S = { t, shot, set, P: Pa, cam, actors, W, H, sc, film: cfg, ctx: g };

    const layers = [];
    for (const L of set.layers || []) layers.push({ z: L.z, sortZ: L.sortZ, key: 'set:' + L.id, static: !!L.static && !shot.noCache, draw: (x, v) => L.draw(x, t, Pa, v, S) });
    for (const pr of shot.props || []) {
      const z = pr.z !== undefined ? pr.z : zAt(pr.at ? pr.at[1] : 900);
      layers.push({ z, key: 'prop', draw: (x) => { const at = pr.at || [960, 900]; const st = SF.resolveState(pr.state || {}, t); const fn = SF.props[pr.type]; if (fn) fn(x, at[0], at[1], pr.s || 1, st, Pa, t); else SF.warn('prop', 'unknown prop "' + pr.type + '"'); } });
    }
    for (const a of actors) {
      const st = a.st; if (!st || st.alpha <= 0.001) continue;
      const ots = a.spec.ots; // over-the-shoulder foreground figure placed in screen space
      if (ots) { const left = ots !== 'right'; st.x = a.spec.screenX !== undefined ? a.spec.screenX : left ? 300 : 1620; st.y = a.spec.screenY || 1250; st.s = a.spec.s || 3.3; if (!a.spec.facing) st.facing = left ? 'back-right' : 'back-left'; }
      const z = (a.spec.z !== undefined ? a.spec.z : ots ? -3.2 : st.z !== undefined ? st.z : zAt(st.y)) + (a.spec.dz || 0);
      layers.push({ z, key: 'actor', ord: 1, screen: !!ots, draw: (x) => {
        if (a.spec.shadow !== false && !(st.pose && st.pose.rot)) SF.rig.drawShadow(x, a.spec.char, { x: st.x, y: st.y, s: st.s, P: Pa, alpha: st.alpha });
        a.spec.char.draw(x, st.pose, { x: st.x, y: st.y, s: st.s, facing: st.facing, P: Pa, t, vel: st.vel, alpha: st.alpha, hold: st.hold, rimA: a.spec.rimA });
      } });
    }
    for (const f of shot.fx || []) { if (!SF.fx[f.type]) { SF.warn('fx', 'unknown fx "' + f.type + '"'); continue; } layers.push({ z: f.z === undefined ? -0.6 : f.z, key: 'fx', ord: 2, draw: (x, v) => SF.fx[f.type](x, t, v, f) }); }
    for (const L of shot.layers || []) layers.push({ z: L.z || 0, key: 'custom', ord: 3, draw: (x, v) => L.draw(x, t, S, v) });
    if (shot.insert) { const ins = shot.insert; const fn = SF.inserts[ins.type]; layers.push({ z: 0, key: 'insert', draw: (x) => fn ? fn(x, t, S, Object.assign(SF.resolveState(Object.assign({}, ins, { state: undefined }), t), ins.state ? SF.resolveState(ins.state, t) : {}, ins.prop ? { state: ins.state } : {})) : SF.warn('insert', 'unknown insert "' + ins.type + '"') }); }
    if (shot.draw) layers.push({ z: shot.drawZ === undefined ? -0.05 : shot.drawZ, key: 'draw', ord: 4, draw: (x, v) => shot.draw(x, t, S, v) });
    // draw order: sortZ (ground planes that span every depth sit behind everything) else z; z drives parallax + blur
    layers.sort((a, b) => (b.sortZ === undefined ? b.z : b.sortZ) - (a.sortZ === undefined ? a.z : a.sortZ) || (a.ord || 0) - (b.ord || 0));

    g.save(); g.setTransform(1, 0, 0, 1, 0, 0); g.fillStyle = Pa.dark || '#000'; g.fillRect(0, 0, W, H); g.restore();
    // consecutive dynamic layers with similar blur share one low-res blur pass (lamps/trees/fx rows)
    let batch = null;
    const flush = () => {
      if (!batch) return;
      const items = batch.items, b = batch.blur;
      P.layer(g, (x) => { const k = x.getTransform().a; for (const it of items) { x.save(); xfInto(x, it.X, k); it.L.draw(x, it.v); x.restore(); } }, { blur: b, key: 'blur', raw: true });
      batch = null;
    };
    for (const L of layers) {
      const X = L.screen ? { pz: 1, zEff: 1, cx: 960, cy: 540, s: sc, rot: 0, W, H } : layerXf(cam, L.z, par, sc, W, H);
      const blur = dof * Math.abs(L.z - focus) * Math.pow(cam.zoom, 0.6) * sc;
      const v = visRect(X);
      if (L.static && !opt.noCache) { flush(); drawCached(g, R, L, X, v, blur, shot, t); }
      else if (blur > 0.6) {
        if (batch && Math.abs(blur - batch.blur) <= Math.max(1.5, batch.blur * 0.3)) batch.items.push({ L, X, v });
        else { flush(); batch = { blur, items: [{ L, X, v }] }; }
      } else { flush(); g.save(); applyXf(g, X); L.draw(g, v); g.restore(); }
    }
    flush();
    // lights (world space at mid depth)
    const lights = (set.lights ? set.lights(t, Pa, visRect(layerXf(cam, 1.5, par, sc, W, H))) : []).concat(shot.lights || []);
    if (lights.length) {
      g.save(); applyXf(g, layerXf(cam, 1.5, par, sc, W, H));
      for (const L of lights) drawLight(g, L, Pa, t);
      g.restore();
    }
    // grade, flashes, vignette, grain
    g.save(); g.setTransform(1, 0, 0, 1, 0, 0);
    const grades = [Pa.ambient, shot.grade, look.grade].filter(Boolean);
    for (const gr of grades) { const gg = SF.val(gr, t); if (!gg) continue; g.globalCompositeOperation = gg.mode || 'multiply'; g.globalAlpha = gg.a === undefined ? 0.2 : gg.a; g.fillStyle = gg.color; g.fillRect(0, 0, W, H); }
    g.globalCompositeOperation = 'source-over'; g.globalAlpha = 1;
    for (const fl of shot.flashes || []) { const k = fl.type === 'lightning' ? SF.fx.lightningAmount(t, fl.t) : clamp(1 - Math.abs(t - fl.t) / (fl.dur || 0.25)); if (k > 0) { g.globalAlpha = k * (fl.a || 0.7); g.fillStyle = fl.color || '#ffffff'; g.fillRect(0, 0, W, H); g.globalAlpha = 1; } }
    const vig = shot.vignette === undefined ? look.vignette : shot.vignette;
    if (vig > 0) { g.globalCompositeOperation = 'multiply'; g.drawImage(vignetteCanvas(W, H, vig), 0, 0, W, H); g.globalCompositeOperation = 'source-over'; }
    g.restore();
    if (!opt.noCaptions) drawCaptions(g, shot, t, S, cam, par);
    if (shot.title) drawTitle(g, shot.title, t, shot, S);
    if (shot.overlay) { g.save(); g.setTransform(sc, 0, 0, sc, 0, 0); shot.overlay(g, t, S); g.restore(); }
  }

  function drawCached(g, R, L, X, v, blur, shot, t) {
    // cache covers the union of visible rects over the shot (sampled), at the max zoom, with blur baked in
    const bq = Math.round(blur * 2) / 2;
    let C = R.cache.get(L.key + ':' + L.z);
    if (!C || Math.abs(C.blur - bq) > Math.max(1, C.blur * 0.25)) {
      const cfg = FILM.cfg; const par = shot.parallax === undefined ? cfg.look.parallax : shot.parallax;
      let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9, zmax = 0;
      for (let i = 0; i <= 10; i++) {
        const tt = (shot.dur * i) / 10;
        const cam = cameraAt(shot, tt, R);
        const Xi = layerXf(cam, L.z, par, X.s / X.zEff, X.W, X.H);
        const vi = visRect(Xi);
        x0 = Math.min(x0, vi.x0); y0 = Math.min(y0, vi.y0); x1 = Math.max(x1, vi.x1); y1 = Math.max(y1, vi.y1); zmax = Math.max(zmax, Xi.s);
      }
      const pad = 40 + bq * 3 / Math.max(0.2, zmax); x0 -= pad; y0 -= pad; x1 += pad; y1 += pad;
      let cs = Math.min(zmax, bq > 4 ? 0.6 : bq > 1.5 ? 1.0 : 1.6); // blurred caches need few pixels
      const maxPx = 3600;
      cs = Math.min(cs, maxPx / (x1 - x0), maxPx / (y1 - y0));
      const cw = Math.ceil((x1 - x0) * cs), chh = Math.ceil((y1 - y0) * cs);
      const cnv = C && C.canvas.width >= cw && C.canvas.height >= chh ? C.canvas : SF.makeCanvas(cw, chh);
      const x = cnv.getContext('2d');
      x.setTransform(1, 0, 0, 1, 0, 0); x.clearRect(0, 0, cnv.width, cnv.height);
      if (bq > 0.6) {
        const tmp = SF.scratch(cw, chh, 'cachetmp'); const tx = tmp.getContext('2d');
        tx.setTransform(1, 0, 0, 1, 0, 0); tx.clearRect(0, 0, cw, chh); tx.setTransform(cs, 0, 0, cs, -x0 * cs, -y0 * cs);
        L.draw(tx, { x0, y0, x1, y1 });
        x.filter = `blur(${(bq * cs / Math.max(0.2, X.s)).toFixed(2)}px)`; x.drawImage(tmp, 0, 0); x.filter = 'none';
      } else { x.setTransform(cs, 0, 0, cs, -x0 * cs, -y0 * cs); L.draw(x, { x0, y0, x1, y1 }); }
      C = { canvas: cnv, x0, y0, cs, blur: bq };
      R.cache.set(L.key + ':' + L.z, C);
    }
    g.save(); applyXf(g, X);
    g.drawImage(C.canvas, 0, 0, C.canvas.width, C.canvas.height, C.x0, C.y0, C.canvas.width / C.cs, C.canvas.height / C.cs);
    g.restore();
  }

  function drawLight(g, L, Pa, t) {
    const a = SF.val(L.a === undefined ? 1 : L.a, t);
    const col = L.color || Pa.light;
    if (L.type === 'glow') P.glow(g, L.x, L.y, L.r || 300, col, a, L.mode || 'lighter');
    else if (L.type === 'cone') P.cone(g, L.x, L.y, L.dir || 90, L.spread || 30, L.len || 800, col, a);
    else if (L.type === 'patch') P.lightPatch(g, L.pts, col, a);
    else if (L.type === 'lamp') SF.build.lampGlow(g, Pa, L.x, L.y, L.s || 1, a);
    else if (L.type === 'pendant') { P.glow(g, L.x, L.y, 380, col, 0.7 * a); P.cone(g, L.x, L.y, 90, 70, 760, col, 0.12 * a); }
    else if (L.type === 'screen') P.glow(g, L.x, L.y, L.r || 200, L.color || '#a8c6ff', a);
  }

  // ---------- captions & titles ----------
  function drawCaptions(g, shot, t, S, cam, par) {
    const look = FILM.cfg.look.captions; const W = g.canvas.width, sc = W / 1920;
    for (const c of shot.capList) {
      const u = t - c.t; if (u < 0 || u > c.dur) continue;
      const fade = Math.min(ev(u, 0, 0.14, 'out'), 1 - ev(u, c.dur - 0.16, 0.16, 'in'));
      let x = 960, y = c.pos === 'bottom' ? 960 : 118;
      const a = S.actors.find((q) => q.id === c.who);
      if (a && c.pos !== 'bottom' && c.pos !== 'top') {
        const z = a.spec.z !== undefined ? a.spec.z : (S.set.zAt ? S.set.zAt(a.st.y) : 0);
        const X = layerXf(cam, z, par, 1, 1920, 1080);
        const anc = a.spec.char.anchors(a.st.pose, { x: a.st.x, y: a.st.y, s: a.st.s, facing: a.st.facing });
        const sx = (anc.top[0] - X.cx) * X.s + 960, sy = (anc.top[1] - X.cy) * X.s + 540;
        x = clamp(sx, 420, 1500); y = clamp(sy - 70, 105, 420);
      }
      if (c.x !== undefined) x = c.x; if (c.y !== undefined) y = c.y;
      const size = (c.size || look.size);
      g.save(); g.setTransform(sc, 0, 0, sc, 0, 0); g.globalAlpha = fade;
      const font = look.font || SF.FONTS.caption;
      const lines = P.wrap(g, c.text, 1100, size, 600, font);
      const lh = size * 1.18, h = lines.length * lh;
      const tw = Math.max(...lines.map((l) => P.measure(g, l, size, 600, font)));
      if (look.band > 0) { g.save(); g.translate(x, y + h / 2 - lh / 2); g.scale(1, (h + 70) / (tw + 260)); g.fillStyle = P.rad(g, 0, 0, 0, (tw + 260) / 2, [[0, rgba('#000000', 0.55 * look.band)], [0.6, rgba('#000000', 0.32 * look.band)], [1, rgba('#000000', 0)]]); g.beginPath(); g.arc(0, 0, (tw + 260) / 2, 0, Math.PI * 2); g.fill(); g.restore(); }
      lines.forEach((l, i) => P.text(g, l, x, y + i * lh + (1 - fade) * 6, { size, weight: 600, font, color: c.color || look.color, stroke: look.stroke, sw: size * 0.17 }));
      g.restore();
    }
  }
  function drawTitle(g, ti, t, shot, S) {
    const W = g.canvas.width, sc = W / 1920;
    const T = typeof ti === 'string' ? { text: ti } : ti;
    const t0 = T.t || 0, d = T.dur || shot.dur - t0;
    const u = t - t0; if (u < 0 || u > d) return;
    const k = Math.min(ev(u, 0, 0.8, 'out'), 1 - ev(u, d - 0.6, 0.6, 'in'));
    g.save(); g.setTransform(sc, 0, 0, sc, 0, 0); g.globalAlpha = k;
    P.text(g, T.text, T.x || 960, (T.y || 520) + (1 - k) * 10, { size: T.size || 120, weight: T.weight || 700, font: T.font || SF.FONTS.ui, color: T.color || '#f4f1ea', spacing: T.spacing === undefined ? 14 : T.spacing });
    if (T.sub) P.text(g, T.sub, T.x || 960, (T.y || 520) + (T.size || 120) * 0.75, { size: T.subSize || 34, weight: 500, font: SF.FONTS.ui, color: rgba('#f4f1ea', 0.75), spacing: 6 });
    g.restore();
  }

  const vigCache = new Map();
  function vignetteCanvas(W, H, vig) {
    const key = W + 'x' + H + ':' + vig.toFixed(2);
    if (vigCache.has(key)) return vigCache.get(key);
    const w = Math.ceil(W / 4), h = Math.ceil(H / 4), c = SF.makeCanvas(w, h), x = c.getContext('2d');
    x.fillStyle = '#ffffff'; x.fillRect(0, 0, w, h);
    x.fillStyle = P.rad(x, w / 2, h / 2, h * 0.32, h * 1.0, [[0, 'rgba(255,255,255,0)'], [0.55, rgba('#3a3d48', vig * 0.35)], [1, rgba('#1e2028', vig)]]); x.fillRect(0, 0, w, h);
    vigCache.set(key, c); return c;
  }
  // ---------- grain ----------
  let grainTile = null;
  function drawGrain(g, frame, amt) {
    if (amt <= 0) return;
    if (!grainTile) { grainTile = SF.makeCanvas(256, 256); const x = grainTile.getContext('2d'); const im = x.createImageData(256, 256); const r = SF.RNG(77); for (let i = 0; i < im.data.length; i += 4) { const v = 128 + (r() - 0.5) * 255; im.data[i] = im.data[i + 1] = im.data[i + 2] = v; im.data[i + 3] = 255; } x.putImageData(im, 0, 0); }
    const W = g.canvas.width, H = g.canvas.height;
    g.save(); g.setTransform(1, 0, 0, 1, 0, 0); g.globalCompositeOperation = 'overlay'; g.globalAlpha = amt;
    const step = FILM.cfg.look.grainStep || 3, gf = Math.floor(frame / step); // grain holds for a few frames: same texture, far smaller files
    const ox = Math.floor(rnd(gf, 1) * 256), oy = Math.floor(rnd(gf, 2) * 256);
    g.translate(-ox, -oy); g.fillStyle = g.createPattern(grainTile, 'repeat'); g.fillRect(0, 0, W + 256, H + 256);
    g.restore();
  }

  // ---------- frame entry point ----------
  /** render global frame f into canvas ctx g */
  function renderFrame(g, f, opt = {}) {
    if (!FILM.prepared) prepare();
    const cfg = FILM.cfg, fps = cfg.fps;
    const shot = shotAtFrame(f);
    const t = (f - shot.f0) / fps;
    drawShot(g, shot, t, opt);
    // crossfade from previous shot
    const trans = shot.trans || 'cut', td = shot.transDur || (trans === 'cross' ? 0.8 : 0.6);
    const W = g.canvas.width, H = g.canvas.height;
    if (trans === 'cross' && shot.index > 0 && t < td) {
      const prev = FILM.shots[shot.index - 1];
      const tmp = SF.scratch(W, H, 'xfade'); const x = tmp.getContext('2d');
      x.setTransform(1, 0, 0, 1, 0, 0);
      drawShot(x, prev, prev.dur + t, Object.assign({}, opt, { noCaptions: true }));
      g.save(); g.setTransform(1, 0, 0, 1, 0, 0); g.globalAlpha = 1 - ev(t, 0, td, 'inOut'); g.drawImage(tmp, 0, 0); g.restore();
    }
    let black = 0;
    if (trans === 'fade' || trans === 'dip') black = Math.max(black, 1 - ev(t, 0, td, 'out'));
    const out = shot.out || 'cut', od = shot.outDur || 0.6;
    if (out === 'fade' || out === 'dip') black = Math.max(black, ev(t, shot.dur - od, od, 'in'));
    const T = f / fps;
    if (cfg.fadeIn) black = Math.max(black, 1 - ev(T, 0, cfg.fadeIn, 'out'));
    if (cfg.fadeOut) black = Math.max(black, ev(T, FILM.duration - cfg.fadeOut, cfg.fadeOut, 'in'));
    if (trans === 'flash' && t < 0.35) { g.save(); g.setTransform(1, 0, 0, 1, 0, 0); g.globalAlpha = 1 - t / 0.35; g.fillStyle = '#fff'; g.fillRect(0, 0, W, H); g.restore(); }
    drawGrain(g, f, cfg.look.grain);
    if (black > 0.001) { g.save(); g.setTransform(1, 0, 0, 1, 0, 0); g.globalAlpha = clamp(black); g.fillStyle = '#000'; g.fillRect(0, 0, W, H); g.restore(); }
  }

  // ---------- timeline export (sound, QA, packaging read this) ----------
  function timeline() {
    if (!FILM.prepared) prepare();
    const cfg = FILM.cfg, fps = cfg.fps;
    const chapters = [];
    for (const s of FILM.shots) {
      const ci = s.ch;
      let c = chapters.find((x) => x.index === ci);
      if (!c) { const meta = cfg.chapters[ci - 1] || {}; c = { index: ci, title: meta.title || 'Chapter ' + ci, mood: meta.mood || 'neutral', energy: meta.energy === undefined ? 0.4 : meta.energy, start: s.start, end: s.end }; chapters.push(c); }
      c.start = Math.min(c.start, s.start); c.end = Math.max(c.end, s.end);
    }
    chapters.sort((a, b) => a.start - b.start);
    const sfx = [], captions = [], amb = [], shots = [];
    for (const s of FILM.shots) {
      const R = runtime(s);
      for (const e of s.sfx || []) { const o = Array.isArray(e) ? Object.assign({ t: e[0], name: e[1] }, e[2] || {}) : Object.assign({}, e); o.t = s.start + o.t; o.shot = s.id; sfx.push(o); }
      for (const c of s.capList) captions.push({ t0: +(s.start + c.t).toFixed(3), t1: +(s.start + c.t + c.dur).toFixed(3), who: c.who, text: c.text, shot: s.id });
      let ambName = s.amb === undefined ? R.set.amb : s.amb;
      if (!ambName && s.insert && amb.length) ambName = amb[amb.length - 1].name; // inserts keep the room they cut away from
      if (ambName) amb.push({ t0: s.start, t1: s.end, name: ambName, gain: s.ambGain === undefined ? 1 : s.ambGain });
      // automatic footsteps from walk cycles
      if (s.footsteps !== false) for (const a of R.actors) {
        let lastStep = null;
        for (let f = 0; f <= Math.round(s.dur * fps); f++) {
          const st = SF.acting.actorAt(a.spec, f / fps, R.scene, a.id);
          if (st.step !== undefined && st.step !== null) { if (lastStep !== null && st.step !== lastStep && st.alpha > 0.2) sfx.push({ t: +(s.start + f / fps).toFixed(3), name: st.gait === 'run' || st.gait === 'jog' ? 'footstep_run' : 'footstep', surface: R.set.surface || (R.set.name.startsWith('street') || R.set.name === 'park' ? 'street' : 'floor'), gain: 0.55 * Math.min(1.2, st.s / 1.85 + 0.2), auto: true, shot: s.id }); lastStep = st.step; }
          else lastStep = null;
        }
      }
      const ck = cameraAt(s, s.key === undefined ? s.dur * 0.5 : s.key, R), c0 = cameraAt(s, 0, R), c1 = cameraAt(s, s.dur, R);
      shots.push({ camZoom: +ck.zoom.toFixed(2), camMove: +(Math.hypot(c1.x - c0.x, c1.y - c0.y) + Math.abs(Math.log(c1.zoom / c0.zoom)) * 400).toFixed(1), palette: typeof s.palette === 'string' ? s.palette : null, index: s.index, id: s.id, ch: s.ch, start: +s.start.toFixed(3), end: +s.end.toFixed(3), dur: s.dur, f0: s.f0, f1: s.f1, beat: s.beat || '', set: R.set.name, time: s.time || (s.setOpts && s.setOpts.time) || null, trans: s.trans || 'cut', insert: !!s.insert, music: s.music || null, silence: !!(s.music && s.music.silence), hit: !!(s.music && s.music.hit), key: s.key === undefined ? s.dur * 0.5 : s.key, actors: R.actors.map((a) => a.id), hold: !!s.hold });
    }
    sfx.sort((a, b) => a.t - b.t);
    return { target: cfg.target || [300, 420], title: cfg.title, fps, size: cfg.size, duration: +FILM.duration.toFixed(3), frames: FILM.frames, chapters, shots, captions, sfx, amb, music: cfg.music, package: cfg.package || null, thumbnail: cfg.thumbnail ? Object.assign({}, cfg.thumbnail, { draw: undefined }) : null, warnings: SF.log.warnings, violations: SF.log.violations.length };
  }

  /** a stable fingerprint of each shot's definition (for segment caching) */
  function shotHash(i) {
    const s = FILM.shots[i];
    const seen = new WeakSet();
    const str = JSON.stringify(s, (k, v) => { if (typeof v === 'function') return v.toString(); if (v && typeof v === 'object') { if (seen.has(v)) return '[circ]'; seen.add(v); } if (k === 'char') return v && v.spec ? v.spec : v; return v; });
    return SF.hashStr(str + '|' + i).toString(16);
  }


  /** model sheet for one cast member: turnaround, key poses, expressions, joint-limit check (for the character gate) */
  function castSheet(g, id, o = {}) {
    if (!FILM.prepared) prepare();
    const ch = FILM.cast[id]; if (!ch) throw new Error('no cast member ' + id);
    const W = g.canvas.width, sc = W / 1920;
    const Pa = SF.palette(o.palette || (FILM.cfg.palette) || 'day');
    g.save(); g.setTransform(sc, 0, 0, sc, 0, 0);
    g.fillStyle = P.lin(g, 0, 0, 0, 1080, [[0, shade(Pa.wall, 0.05)], [1, shade(Pa.wall, -0.12)]]); g.fillRect(0, 0, 1920, 1080);
    P.rect(g, 0, 600, 1920, 3, rgba('#000000', 0.15));
    P.text(g, (ch.name || id).toUpperCase() + '  —  model sheet', 40, 46, { size: 34, weight: 800, align: 'left', color: shade(Pa.dark, 0.1) });
    P.text(g, `build: ${ch.build} · style: ${ch.style}${ch.hair ? ' · hair: ' + ch.hair : ''}${ch.wear.length ? ' · wears: ' + ch.wear.join(', ') : ''}`, 40, 84, { size: 20, weight: 500, align: 'left', color: rgba(Pa.dark, 0.8) });
    const views = [['front', 'stand'], ['front-right', 'stand'], ['right', 'stand'], ['back', 'stand'], ['front', 'slump'], ['front', 'armsCrossed'], ['front', 'fingerUp'], ['right', 'holdPhone'], ['front', 'celebrate']];
    const before = SF.log.violations.length;
    views.forEach(([facing, pose], i) => {
      const x = 130 + i * 207, y = 560;
      const view = SF.rig.facingInfo(facing).view;
      const p = Object.assign({}, SF.acting.poseFor('stand', view), SF.acting.poseFor(pose, view));
      SF.rig.drawShadow(g, ch, { x, y, s: 1.45, P: Pa });
      ch.draw(g, p, { x, y, s: 1.45, facing, P: Pa, t: 0, hold: pose === 'holdPhone' ? { R: 'phone' } : null });
      P.text(g, facing + (pose !== 'stand' ? ' · ' + pose : ''), x, y + 30, { size: 17, weight: 600, color: rgba(Pa.dark, 0.85) });
    });
    const exprs = ['neutral', 'happy', 'sad', 'worried', 'surprised', 'determined', 'tired', 'angry', 'cry', 'hopeful'];
    exprs.forEach((e, i) => {
      const x = 110 + i * 190, y = 1010;
      g.save(); g.beginPath(); g.rect(x - 92, 640, 184, 400); g.clip();
      ch.draw(g, { face: e, blink: 0 }, { x, y: y + 420, s: 2.5, facing: 'front', P: Pa, t: 0.4 });
      g.restore();
      P.text(g, e, x, 1050, { size: 18, weight: 600, color: rgba(Pa.dark, 0.85) });
    });
    const v = SF.log.violations.length - before;
    P.text(g, v ? `joint-limit clamps on this sheet: ${v}` : 'joint limits: all poses inside anatomical range', 1880, 46, { size: 18, weight: 600, align: 'right', color: v ? '#b3261e' : '#2f6b3a' });
    g.restore();
  }
  SF.castSheet = castSheet;


  /** debugging: state of an actor in a shot at local time t (position, scale, depth, facing, key pose numbers) */
  SF.debugActor = (shotId, id, t) => {
    if (!FILM.prepared) prepare();
    const s = FILM.shots.find((x) => x.id === shotId || x.index === shotId); if (!s) return 'no shot ' + shotId;
    const R = runtime(s); const st = actorState(R, id, t, s); if (!st) return 'no actor ' + id;
    const cam = cameraAt(s, t, R);
    return { x: +st.x.toFixed(1), y: +st.y.toFixed(1), s: +st.s.toFixed(2), z: R.set.zAt ? +R.set.zAt(st.y).toFixed(2) : 0, facing: st.facing, alpha: st.alpha, view: st.view, cam: { x: +cam.x.toFixed(1), y: +cam.y.toFixed(1), zoom: +cam.zoom.toFixed(2) }, pose: Object.fromEntries(Object.entries(st.pose).filter(([k, v]) => typeof v !== 'number' || Math.abs(v) > 0.01).map(([k, v]) => [k, typeof v === 'number' ? +v.toFixed(1) : v])) };
  };
  SF.prepare = prepare;
  SF.renderFrame = renderFrame;
  SF.drawShot = drawShot;
  SF.timeline = timeline;
  SF.shotHash = shotHash;
  SF.cameraAt = (i, t) => cameraAt(FILM.shots[i], t, runtime(FILM.shots[i]));
})();
