/* Short-film engine: core utilities. Everything hangs off window.SF.
   Deterministic by design: never use Math.random() or Date in films; use SF.RNG / SF.rnd / SF.noise. */
(function () {
  const SF = (window.SF = window.SF || {});

  // ---------- math ----------
  const clamp = (v, a = 0, b = 1) => (v < a ? a : v > b ? b : v);
  const lerp = (a, b, k) => a + (b - a) * k;
  const invLerp = (a, b, v) => (b === a ? 0 : (v - a) / (b - a));
  const remap = (v, a, b, c, d, cl = true) => { let k = invLerp(a, b, v); if (cl) k = clamp(k); return lerp(c, d, k); };
  const smooth = (k) => k * k * (3 - 2 * k);
  const DEG = Math.PI / 180;
  const angLerp = (a, b, k) => a + (((((b - a) % 360) + 540) % 360) - 180) * k;

  // ---------- easing ----------
  const ease = {
    linear: (k) => k,
    in: (k) => k * k,
    out: (k) => 1 - (1 - k) * (1 - k),
    inOut: (k) => (k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2),
    in3: (k) => k * k * k,
    out3: (k) => 1 - Math.pow(1 - k, 3),
    inOut3: (k) => (k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2),
    sine: (k) => -(Math.cos(Math.PI * k) - 1) / 2,
    outBack: (k) => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(k - 1, 3) + c1 * Math.pow(k - 1, 2); },
    outElastic: (k) => (k === 0 || k === 1 ? k : Math.pow(2, -10 * k) * Math.sin((k * 10 - 0.75) * ((2 * Math.PI) / 3)) + 1),
    // critically-damped-ish spring with a small overshoot; closed form so frames stay random-access
    spring: (k) => 1 - Math.exp(-7 * k) * Math.cos(2.1 * Math.PI * k * 0.9),
    step: (k) => (k < 1 ? 0 : 1),
  };
  const E = (e) => (typeof e === 'function' ? e : ease[e] || ease.inOut);
  /** 0..1 progress of an event at t0 lasting d */
  const ev = (t, t0, d, e = 'inOut') => E(e)(clamp((t - t0) / Math.max(1e-6, d)));
  /** 0 -> 1 -> 0 bump over [t0, t0+d] */
  const bump = (t, t0, d) => { const k = clamp((t - t0) / Math.max(1e-6, d)); return Math.sin(Math.PI * k); };

  // ---------- colours ----------
  const HEXRE = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i;
  function hex(c) {
    if (Array.isArray(c)) return c;
    let h = String(c).replace('#', '');
    if (h.length === 3) h = h.split('').map((x) => x + x).join('');
    const n = parseInt(h, 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }
  const toHex = (r, g, b) => '#' + [r, g, b].map((v) => clamp(Math.round(v), 0, 255).toString(16).padStart(2, '0')).join('');
  const rgba = (c, a = 1) => { const [r, g, b] = hex(c); return `rgba(${r},${g},${b},${a})`; };
  const mixColor = (c1, c2, k) => { const a = hex(c1), b = hex(c2); return toHex(lerp(a[0], b[0], k), lerp(a[1], b[1], k), lerp(a[2], b[2], k)); };
  /** k>0 lightens toward white, k<0 darkens toward black */
  const shade = (c, k) => (k >= 0 ? mixColor(c, '#ffffff', k) : mixColor(c, '#000000', -k));
  const isHex = (s) => typeof s === 'string' && HEXRE.test(s);

  // ---------- deterministic randomness ----------
  function hashStr(s) {
    let h = 2166136261 >>> 0;
    s = String(s);
    for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
    return h >>> 0;
  }
  /** seeded generator: r() in [0,1), r.range(a,b), r.int(a,b), r.pick(arr), r.sign() */
  function RNG(seed) {
    let a = (typeof seed === 'number' ? seed >>> 0 : hashStr(seed)) || 1;
    const r = () => {
      a |= 0; a = (a + 0x6d2b79f5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
    r.range = (x, y) => x + (y - x) * r();
    r.int = (x, y) => Math.floor(x + (y - x + 1) * r());
    r.pick = (arr) => arr[Math.floor(r() * arr.length)];
    r.sign = () => (r() < 0.5 ? -1 : 1);
    return r;
  }
  /** stateless hash -> [0,1) for integer i and seed */
  function rnd(i, seed = 0) {
    let h = Math.imul((i | 0) ^ 0x9e3779b9, 0x85ebca6b) ^ Math.imul((seed | 0) + 0x632be5ab, 0xc2b2ae35);
    h ^= h >>> 13; h = Math.imul(h, 0x27d4eb2f); h ^= h >>> 16;
    return (h >>> 0) / 4294967296;
  }
  /** smooth value noise in [-1,1] */
  function noise(x, seed = 0) { const i = Math.floor(x), f = x - i; return lerp(rnd(i, seed), rnd(i + 1, seed), smooth(f)) * 2 - 1; }
  /** two octaves, nice for handheld camera drift */
  const noise2 = (x, seed = 0) => noise(x, seed) * 0.7 + noise(x * 2.3 + 11.7, seed + 7) * 0.3;

  // ---------- keyframes ----------
  function mixVal(a, b, k) {
    if (typeof a === 'number' && typeof b === 'number') return lerp(a, b, k);
    if (isHex(a) && isHex(b)) return mixColor(a, b, k);
    if (Array.isArray(a) && Array.isArray(b)) return a.map((v, i) => mixVal(v, b[i] === undefined ? v : b[i], k));
    if (a && b && typeof a === 'object' && typeof b === 'object') {
      const o = {};
      for (const key of new Set([...Object.keys(a), ...Object.keys(b)])) {
        o[key] = key in a && key in b ? mixVal(a[key], b[key], k) : key in b ? b[key] : a[key];
      }
      return o;
    }
    return k < 0.5 ? a : b;
  }
  /** keys: [[t, value, easeIntoThisKey?], ...] -> value at t (numbers, colours, arrays, objects) */
  function track(keys, t) {
    if (!Array.isArray(keys) || !keys.length) return keys;
    if (!Array.isArray(keys[0])) return keys; // plain value
    if (t <= keys[0][0]) return keys[0][1];
    for (let i = 1; i < keys.length; i++) {
      const [t1, v1, e] = keys[i];
      if (t <= t1) {
        const [t0, v0] = keys[i - 1];
        return mixVal(v0, v1, E(e || 'inOut')(clamp((t - t0) / Math.max(1e-6, t1 - t0))));
      }
    }
    return keys[keys.length - 1][1];
  }
  /** true if v looks like a keyframe track */
  const isTrack = (v) => Array.isArray(v) && v.length > 0 && Array.isArray(v[0]) && typeof v[0][0] === 'number';
  /** value that may be a constant, a track, or a function of t */
  const val = (v, t) => (typeof v === 'function' ? v(t) : isTrack(v) ? track(v, t) : v);
  /** resolve every field of a state object at time t: keyframe tracks interpolate, functions of t are called
      (fields named custom/draw/onDraw stay functions). Lets any prop/insert field animate: {crossed: [[0,0],[3,28]]} */
  const KEEP_FN = new Set(['custom', 'draw', 'onDraw']);
  function resolveState(o, t) {
    if (typeof o === 'function') return o(t);
    if (!o || typeof o !== 'object' || Array.isArray(o)) return val(o, t);
    const r = {};
    for (const k in o) { const v = o[k]; r[k] = typeof v === 'function' && !KEEP_FN.has(k) ? v(t) : isTrack(v) ? track(v, t) : v; }
    return r;
  }

  // ---------- canvases ----------
  const pool = new Map();
  /** reusable scratch canvas of a given size (key distinguishes concurrent uses) */
  function scratch(w, h, key = 'a') {
    const id = key + ':' + w + 'x' + h;
    let c = pool.get(id);
    if (!c) { c = document.createElement('canvas'); c.width = w; c.height = h; pool.set(id, c); }
    return c;
  }
  function makeCanvas(w, h) { const c = document.createElement('canvas'); c.width = Math.max(1, Math.ceil(w)); c.height = Math.max(1, Math.ceil(h)); return c; }

  // ---------- warnings collected for QA ----------
  const log = { warnings: [], violations: [], counts: {} };
  function warn(kind, msg) {
    const key = kind + ':' + msg;
    log.counts[key] = (log.counts[key] || 0) + 1;
    if (log.counts[key] === 1) log.warnings.push({ kind, msg });
  }

  Object.assign(SF, {
    clamp, lerp, invLerp, remap, smooth, DEG, angLerp,
    ease, E, ev, bump,
    hex, toHex, rgba, mixColor, shade, isHex,
    hashStr, RNG, rnd, noise, noise2,
    mixVal, track, isTrack, val, resolveState,
    scratch, makeCanvas,
    log, warn,
  });
})();
