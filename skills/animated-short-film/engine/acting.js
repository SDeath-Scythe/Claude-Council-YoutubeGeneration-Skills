/* Acting: named poses, locomotion cycles with planted feet, gestures, and the per-actor action timeline.
   Everything is a pure function of time, so any frame renders on its own (parallel/segment renders stay identical). */
(function () {
  const SF = window.SF;
  const { clamp, lerp, ev, bump, rnd, noise } = SF;
  const RIG = SF.rig;
  const D2R = Math.PI / 180;

  // ---------- pose library ----------
  // front view: sh = outward angle, el = forearm turn (+ outward/up, - inward/across body)
  // side view : sh = forward angle, el = forward flex (0..150), hp = forward, kn = backward flex
  const POSES = {
    stand: { front: { shL: 7, elL: -8, shR: 7, elR: -8 }, side: { shL: -4, elL: 10, shR: 4, elR: 12 } },
    relaxed: { front: { shL: 5, elL: -4, shR: 9, elR: -14, lean: 2 }, side: { shL: -6, elL: 8, shR: 2, elR: 8, lean: 2 } },
    slump: { front: { shL: 2, elL: 0, shR: 2, elR: 0, nod: 0.8, squash: 0.975, face: 'sad' }, side: { lean: 16, neck: 22, shL: 6, elL: 4, shR: 10, elR: 4, squash: 0.98, face: 'sad' } },
    defeated: { front: { shL: 1, elL: 0, shR: 1, elR: 0, nod: 1, squash: 0.96, face: 'sad' }, side: { lean: 26, neck: 30, shL: 12, elL: 2, shR: 16, elR: 2, squash: 0.96, face: 'sad' } },
    proud: { front: { shL: 12, elL: -10, shR: 12, elR: -10, lean: -2, nod: -0.3, face: 'proud' }, side: { lean: -6, neck: -10, shL: -8, elL: 14, shR: 0, elR: 14, face: 'proud' } },
    armsCrossed: { front: { shL: 18, elL: -140, shR: 22, elR: -136 }, side: { shL: 18, elL: 120, shR: 22, elR: 120 } },
    handsOnHips: { front: { shL: 40, elL: -98, shR: 40, elR: -98, handL: 'fist', handR: 'fist' }, side: { shL: -30, elL: 95, shR: -28, elR: 95 } },
    thinking: { front: { shL: 22, elL: -120, shR: 14, elR: -152, handR: 'fist', face: 'thinking', nod: -0.2 }, side: { shR: 30, elR: 140, shL: 20, elL: 110, neck: -6, face: 'thinking' } },
    raiseHand: { front: { shR: 168, elR: 8, handR: 'open' }, side: { shR: 165, elR: 10, handR: 'open' } },
    fingerUp: { front: { shR: 32, elR: 128, handR: 'up' }, side: { shR: 20, elR: 140, handR: 'up' } },
    point: { front: { shR: 82, elR: 2, handR: 'point' }, side: { shR: 84, elR: 4, handR: 'point' } },
    shrug: { front: { shL: 32, elL: 96, shR: 32, elR: 96, handL: 'open', handR: 'open', neck: 10, face: 'worried' }, side: { shL: 22, elL: 85, shR: 26, elR: 85, handR: 'open', neck: 8 } },
    holdPhone: { front: { shR: 14, elR: -108, handR: 'fist', nod: 0.55, lookY: 0.9 }, side: { shR: 24, elR: 96, handR: 'fist', neck: 22, lookY: 0.6 } },
    holdPhoneUp: { front: { shR: 22, elR: -140, handR: 'fist', nod: 0.1 }, side: { shR: 50, elR: 100, handR: 'fist', neck: 6 } },
    carry: { front: { shL: 18, elL: -95, shR: 18, elR: -95 }, side: { shL: 34, elL: 70, shR: 38, elR: 70 } },
    reachForward: { front: { shR: 70, elR: 0 }, side: { shR: 80, elR: 6 } },
    celebrate: { front: { shL: 160, elL: 18, shR: 160, elR: 18, handL: 'fist', handR: 'fist', nod: -0.4, face: 'grin' }, side: { shL: 165, elL: 15, shR: 170, elR: 15, handR: 'fist', neck: -12, face: 'grin' } },
    facepalm: { front: { shR: 20, elR: -150, nod: 0.5, face: 'tired' }, side: { shR: 40, elR: 150, neck: 24, face: 'tired' } },
    headInHands: { front: { shL: 20, elL: -150, shR: 20, elR: -150, nod: 0.8, face: 'cry' }, side: { shL: 46, elL: 150, shR: 50, elR: 150, lean: 22, neck: 30, face: 'cry' } },
    hug: { front: { shL: 60, elL: -100, shR: 60, elR: -100, face: 'content' }, side: { shL: 80, elL: 70, shR: 85, elR: 70 } },
    lookUp: { front: { nod: -0.7, lookY: -1 }, side: { neck: -28, lookY: -1 } },
    lookDown: { front: { nod: 0.8, lookY: 1 }, side: { neck: 28, lookY: 1 } },
    tense: { front: { shL: 10, elL: -20, shR: 10, elR: -20, handL: 'fist', handR: 'fist', squash: 0.985, face: 'determined' }, side: { lean: 8, shL: -10, elL: 40, shR: 10, elR: 50, handR: 'fist', face: 'determined' } },
    ready: { side: { lean: 14, shL: -30, elL: 80, shR: 40, elR: 80, hpL: 30, knL: 25, hpR: -14, knR: 10, handR: 'fist', handL: 'fist', face: 'determined' }, front: { shL: 16, elL: -40, shR: 16, elR: -40, handL: 'fist', handR: 'fist', face: 'determined' } },
  };
  SF.POSES = POSES;

  /** resolve a pose name/object for a view into a flat partial pose */
  function poseFor(p, view) {
    if (!p) return {};
    if (typeof p === 'string') {
      const lib = POSES[p];
      if (!lib) { SF.warn('pose', 'unknown pose "' + p + '"'); return {}; }
      return Object.assign({}, lib[view === 'side' ? 'side' : 'front'] || lib.front || lib.side);
    }
    if (p.front || p.side) return Object.assign({}, p[view === 'side' ? 'side' : 'front'] || p.front || p.side);
    return Object.assign({}, p);
  }
  const NUMERIC = ['fsL', 'fsR', 'ssL', 'ssR', 'x', 'y', 'rot', 'lean', 'neck', 'turn', 'nod', 'squash', 'shL', 'elL', 'shR', 'elR', 'hpL', 'knL', 'hpR', 'knR', 'anL', 'anR', 'foreL', 'foreR', 'lookX', 'lookY', 'mouth', 'tears', 'blink'];
  function blendPose(a, b, k) {
    if (k <= 0) return Object.assign({}, a);
    if (k >= 1) return Object.assign({}, a, b);
    const o = Object.assign({}, a);
    for (const key in b) {
      if (NUMERIC.includes(key)) o[key] = lerp(a[key] === undefined ? RIG.DEFAULT_POSE[key] || 0 : a[key], b[key], k);
      else o[key] = k > 0.5 ? b[key] : a[key] === undefined ? b[key] : a[key];
    }
    return o;
  }

  // ---------- locomotion ----------
  const GAITS = {
    walk: { stride: 0.95, lift: 0.3, bob: 4.5, duty: 0.56, arm: 20, elbow: 14, lean: 3, speed: 155 },
    stroll: { stride: 0.75, lift: 0.22, bob: 3, duty: 0.6, arm: 13, elbow: 10, lean: 1, speed: 105 },
    sad: { stride: 0.6, lift: 0.14, bob: 2.5, duty: 0.62, arm: 6, elbow: 6, lean: 12, speed: 80, neck: 18, face: 'sad' },
    jog: { stride: 1.25, lift: 0.5, bob: 7, duty: 0.42, arm: 32, elbow: 75, lean: 8, speed: 300 },
    run: { stride: 1.6, lift: 0.75, bob: 9, duty: 0.36, arm: 48, elbow: 88, lean: 14, speed: 470 },
    sneak: { stride: 0.7, lift: 0.4, bob: 2, duty: 0.6, arm: 10, elbow: 70, lean: 18, speed: 70 },
  };
  SF.GAITS = GAITS;
  /** side-view cycle pose at distance d (local units travelled) for a body; feet stay planted by construction */
  function cyclePose(ch, gaitName, d) {
    const G = GAITS[gaitName] || GAITS.walk; const B = ch.body;
    const S = B.thigh * G.stride * 1.8; // stride length (one step)
    const phase = (d / S) * Math.PI; // half cycle per step
    const legLen = B.thigh + B.shin;
    const hipH = legLen * 0.985 + B.ankle;
    const lift = B.thigh * G.lift;
    // pelvis lowest at double support (phase multiple of pi)
    const dropNeeded = hipH - Math.sqrt(Math.max(1, legLen * legLen - (S * 0.5) * (S * 0.5))) - B.ankle + 2;
    const bob = Math.max(0, dropNeeded) + G.bob * (0.5 + 0.5 * Math.cos(2 * phase)) - (G.duty < 0.5 ? G.bob * 0.6 * Math.max(0, Math.sin(2 * phase)) : 0);
    const pose = { y: bob, lean: G.lean, neck: G.neck || 0 };
    const pelY = -hipH + bob;
    for (const [s, off] of [['L', 0], ['R', Math.PI]]) {
      let ph = (phase + off) % (2 * Math.PI); if (ph < 0) ph += 2 * Math.PI;
      const stanceEnd = 2 * Math.PI * G.duty;
      let fx, fy;
      if (ph < stanceEnd) { const k = ph / stanceEnd; fx = S / 2 - S * k; fy = 0; }
      else { const k = (ph - stanceEnd) / (2 * Math.PI - stanceEnd); const e = k * k * (3 - 2 * k); fx = -S / 2 + S * e; fy = -lift * Math.sin(Math.PI * k); }
      const hx = (s === 'L' ? -2.5 : 2.5), hy = pelY - 3;
      const tx = fx, ty = fy - B.ankle;
      const r = RIG.ik2(hx, hy, tx, ty, B.thigh, B.shin, +1);
      const tilt = pose.lean * 0.15;
      pose['hp' + s] = r.a1 - tilt;
      pose['kn' + s] = Math.max(0, r.a1 - r.a2);
      pose['an' + s] = ph < stanceEnd ? 0 : 12 * Math.sin(Math.PI * ((ph - stanceEnd) / (2 * Math.PI - stanceEnd)));
    }
    // arms swing opposite to legs (L leg forward at phase 0 -> R arm forward)
    const sw = Math.cos(phase);
    pose.shR = G.arm * sw; pose.shL = -G.arm * sw;
    pose.elR = G.elbow + (G.elbow > 40 ? 10 : 8) * Math.max(0, sw);
    pose.elL = G.elbow + (G.elbow > 40 ? 10 : 8) * Math.max(0, -sw);
    if (G.elbow > 40) { pose.handL = 'fist'; pose.handR = 'fist'; }
    if (G.face) pose.face = G.face;
    return pose;
  }
  /** front/back walk in depth: legs alternate lifting, small sway */
  function cycleFront(ch, gaitName, d) {
    const G = GAITS[gaitName] || GAITS.walk; const B = ch.body;
    const S = B.thigh * G.stride * 1.8;
    const phase = (d / S) * Math.PI;
    const liftL = Math.max(0, Math.sin(phase)), liftR = Math.max(0, -Math.sin(phase));
    return {
      y: G.bob * 0.6 * Math.abs(Math.cos(phase)), lean: Math.sin(phase) * 1.2,
      hpL: 2 + liftL * 3, knL: -liftL * 6, hpR: 2 + liftR * 3, knR: liftR * 6,
      fsL: 1 - liftL * 0.12 * G.stride, fsR: 1 - liftR * 0.12 * G.stride,
      shL: 7 + liftR * G.arm * 0.25, shR: 7 + liftL * G.arm * 0.25,
      elL: -8 - liftR * 10, elR: -8 - liftL * 10,
      neck: G.neck ? G.neck * 0.3 : 0, nod: G.neck ? 0.5 : 0,
    };
  }

  // ---------- gestures (temporary overlays) ----------
  // each returns a partial pose for local time u (s) within duration d; envelope applied by caller
  const GESTURES = {
    wave: (u, d, view, A) => { const w = Math.sin(u * 2 * Math.PI * 2.4); return view === 'side' ? { shR: 150, elR: 20 + 25 * w, handR: 'open' } : { shR: 135, elR: 28 + 26 * w, handR: 'open' }; },
    nod: (u) => ({ nod: 0.45 * Math.max(0, Math.sin(u * 2 * Math.PI * 2.2)), neck: 8 * Math.max(0, Math.sin(u * 2 * Math.PI * 2.2)) }),
    shake: (u) => ({ turn: 0.32 * Math.sin(u * 2 * Math.PI * 2.4), neck: 0 }),
    shrug: (u, d, view) => Object.assign(poseFor('shrug', view), { squash: 1 + 0.02 * bump(u, 0, d) }),
    sigh: (u, d) => { const k = u / d; const inh = k < 0.4 ? Math.sin((k / 0.4) * Math.PI / 2) : 1 - ev(k, 0.4, 0.6, 'out'); return { squash: 1 + 0.025 * inh - 0.02 * (k > 0.4 ? ev(k, 0.4, 0.4) : 0), nod: -0.2 * inh + 0.45 * (k > 0.45 ? ev(k, 0.45, 0.3) : 0), neck: 8 * (k > 0.45 ? 1 : 0) * ev(k, 0.45, 0.3) }; },
    point: (u, d, view) => poseFor('point', view),
    fingerUp: (u, d, view) => poseFor('fingerUp', view),
    raiseHand: (u, d, view) => poseFor('raiseHand', view),
    reach: (u, d, view) => poseFor('reachForward', view),
    hug: (u, d, view) => poseFor('hug', view),
    facepalm: (u, d, view) => poseFor('facepalm', view),
    scratchHead: (u, d, view) => (view === 'side' ? { shR: 150, elR: 120, neck: 8 } : { shR: 125, elR: -150 + 6 * Math.sin(u * 30), neck: 10, face: 'worried' }),
    clap: (u, d, view) => { const k = 0.5 + 0.5 * Math.sin(u * 2 * Math.PI * 3); return view === 'side' ? { shL: 60, elL: 70, shR: 64, elR: 70 + 10 * k } : { shL: 22, elL: -95 - 20 * k, shR: 22, elR: -95 - 20 * k, face: 'happy' }; },
    fistPump: (u, d, view) => { const k = Math.abs(Math.sin(u * Math.PI * 2.5)); return view === 'side' ? { shR: 120 + 40 * k, elR: 60 - 40 * k, handR: 'fist', face: 'grin' } : { shR: 120 + 40 * k, elR: 50 - 35 * k, handR: 'fist', face: 'grin' }; },
    stretch: (u, d, view) => poseFor('celebrate', view),
    yawn: (u, d, view) => (view === 'side' ? { shR: 60, elR: 140, neck: -12, face: 'tired', mouth: 0.9 } : { shR: 18, elR: -150, nod: -0.3, face: 'tired' }),
    wipeEyes: (u, d, view) => (view === 'side' ? { shR: 50, elR: 145, neck: 18, face: 'cry' } : { shR: 18 + 4 * Math.sin(u * 12), elR: -150, nod: 0.4, face: 'cry' }),
    tap: (u, d, view) => ({ shR: (view === 'side' ? 45 : 30), elR: (view === 'side' ? 70 : -90) + 10 * Math.abs(Math.sin(u * 12)), handR: 'point' }),
    jumpJoy: (u, d) => ({ y: -60 * Math.max(0, Math.sin((u / d) * Math.PI)), shL: 150, shR: 150, elL: 20, elR: 20, face: 'grin', handL: 'fist', handR: 'fist' }),
    flinch: (u, d) => ({ squash: 0.95, lean: -6, shL: 30, elL: -120, shR: 30, elR: -120, face: 'shock' }),
    shiver: (u) => ({ lean: Math.sin(u * 60) * 1.5, squash: 0.985, shL: 18, elL: -125, shR: 18, elR: -125 }),
    laugh: (u) => ({ y: -3 * Math.abs(Math.sin(u * 14)), nod: -0.3 + 0.2 * Math.sin(u * 14), face: 'grin' }),
    cry: (u) => ({ squash: 0.985 + 0.01 * Math.sin(u * 16), nod: 0.6, face: 'cry' }),
    breathe: (u) => ({ squash: 1 + 0.03 * Math.sin(u * 2.8), y: 2 * Math.sin(u * 5.6) }), // heavy breathing / panting
    typing: (u, d, view) => ({ shL: 34, elL: 62 + 6 * Math.sin(u * 23), shR: 38, elR: 60 + 6 * Math.sin(u * 19 + 1), neck: 10 }),
    scroll: (u, d, view) => Object.assign(poseFor('holdPhone', view), { elR: (view === 'side' ? 96 : -108) + 3 * Math.sin(u * 7) }),
  };
  SF.GESTURES = GESTURES;

  // ---------- helpers ----------
  /** normalise an action entry: [t, verb, a, b] -> {t, verb, a, b} */
  const norm = (e) => (Array.isArray(e) ? { t: e[0], verb: e[1], a: e[2], b: e[3] } : e);
  function resolveX(target, scene) {
    if (typeof target === 'number') return { x: target };
    if (Array.isArray(target)) return { x: target[0], y: target[1] };
    if (typeof target === 'string' && scene && scene.marks && scene.marks[target]) return scene.marks[target];
    if (typeof target === 'string' && scene && scene.actorsAt && scene.actorsAt[target]) return scene.actorsAt[target];
    if (target && typeof target === 'object' && 'x' in target) return target;
    SF.warn('mark', 'unknown mark/target ' + JSON.stringify(target));
    return { x: 960 };
  }

  /**
   * Evaluate an actor at shot time t. Pure function of t.
   * spec: { char, at, facing, s, z, pose, face, act:[[t, verb, arg, opts]], hold:{R:'phone'} }
   * scene: { marks, scaleAt(y), floorY, actorsAt }
   * returns { x, y, s, facing, pose, alpha, hold, vel, view }
   */
  function actorAt(spec, t, scene, name) {
    const ch = spec.char, B = ch.body;
    const start = resolveX(spec.at !== undefined ? spec.at : 960, scene);
    let x = start.x + (spec.dx || 0);
    let y = (start.y !== undefined ? start.y : (scene && scene.floorY) || 900) + (spec.dy || 0);
    const markSeat = start.seat, markZ = start.z, markS = start.s;
    let facing = spec.facing || 'front';
    const acts = (spec.act || []).map(norm).sort((a, b) => a.t - b.t);
    const scaleAtY = (yy) => (spec.s !== undefined ? spec.s : markS !== undefined ? markS : scene && scene.scaleAt ? scene.scaleAt(yy) : 1);

    const bodyChanges = [{ t: -1e9, p: spec.pose || 'stand', dur: 0 }];
    let expr = spec.face || 'neutral', exprT = -1e9;
    const looks = [{ t: -1e9, v: { lookX: 0, lookY: 0, turn: 0 } }];
    let alpha = spec.hidden ? 0 : 1;
    const hold = Object.assign({}, spec.hold || {});
    let loco = null, lastLoco = null, slide = null;
    let sit = null;
    const gestures = [], talk = (spec.talk || []).slice();

    // move any running locomotion/slide forward to time T
    const advance = (T) => {
      if (loco) {
        const k = clamp((T - loco.t0) / (loco.t1 - loco.t0));
        x = lerp(loco.x0, loco.x1, k); y = lerp(loco.y0, loco.y1, k);
        loco.tNow = T;
        if (T >= loco.t1) { lastLoco = loco; loco = null; if (lastLoco.end) facing = lastLoco.end; }
      }
      if (slide) {
        const k = ev(T, slide.t0, slide.dur, slide.ease);
        x = lerp(slide.x0, slide.x1, k); y = lerp(slide.y0, slide.y1, k);
        if (T >= slide.t0 + slide.dur) slide = null;
      }
    };

    for (const a of acts) {
      if (a.verb === 'gesture') { gestures.push({ t0: a.t, name: a.a, d: (a.b && a.b.dur) || defaultGestureDur(a.a) }); continue; }
      if (a.verb === 'say') { talk.push([a.t, a.t + ((a.b && a.b.dur) || autoDur(a.a))]); continue; }
      if (a.t > t) continue;
      advance(a.t);
      switch (a.verb) {
        case 'pose': bodyChanges.push({ t: a.t, p: a.a, dur: (a.b && a.b.dur) || 0.35 }); break;
        case 'face': expr = a.a; exprT = a.t; break;
        case 'look': looks.push({ t: a.t, v: lookTarget(a.a, x, scene) }); break;
        case 'turn': case 'facing': facing = a.a; break;
        case 'show': case 'appear': alpha = clamp((t - a.t) / ((a.a && a.a.dur) || 0.4)); break;
        case 'hide': case 'disappear': alpha = 1 - clamp((t - a.t) / ((a.a && a.a.dur) || 0.4)); break;
        case 'hold': hold[a.a] = a.b; break;
        case 'drop': delete hold[a.a]; break;
        case 'walk': case 'run': case 'jog': case 'stroll': case 'sneak': case 'trudge': {
          const arg = a.a && typeof a.a === 'object' && !Array.isArray(a.a) ? a.a : { to: a.a };
          const gait = a.verb === 'trudge' ? 'sad' : arg.gait || a.verb;
          const G = GAITS[gait] || GAITS.walk;
          const tgt = resolveX(arg.to, scene);
          const sc = scaleAtY(y);
          const speed = (arg.speed || G.speed) * sc * (arg.pace || 1);
          const ty = tgt.y !== undefined ? tgt.y : y;
          const depth = Math.abs(ty - y) > 4 && Math.abs(tgt.x - x) < Math.abs(ty - y) * 2;
          const dist = depth ? Math.hypot(tgt.x - x, (ty - y) * 2.2) : Math.abs(tgt.x - x);
          const dur = arg.dur || Math.max(0.2, dist / speed);
          loco = { gait, x0: x, x1: tgt.x, y0: y, y1: ty, t0: a.t, t1: a.t + dur, depth, end: arg.end };
          facing = arg.facing || (depth ? (ty > y ? 'front' : 'back') : tgt.x >= x ? 'right' : 'left');
          break;
        }
        case 'move': {
          const arg = a.a && typeof a.a === 'object' && !Array.isArray(a.a) && !('x' in a.a) ? a.a : { to: a.a };
          const tgt = resolveX(arg.to, scene);
          slide = { x0: x, y0: y, x1: tgt.x, y1: tgt.y !== undefined ? tgt.y : y, t0: a.t, dur: arg.dur || 1, ease: arg.ease || 'inOut' };
          break;
        }
        case 'sit': sit = { t0: a.t, dur: (a.a && a.a.dur) || 0.6, seat: (a.a && a.a.seat) || null, up: false, slump: !!(a.a && a.a.slump) }; break;
        case 'stand': if (sit) sit = Object.assign({}, sit, { up: true, tu: a.t, dur: (a.a && a.a.dur) || 0.6 }); break;
        case 'lie': sit = { lie: true, dir: (a.a && a.a.dir) || 'left', t0: a.t }; break;
        default: SF.warn('verb', 'unknown action verb "' + a.verb + '" (' + name + ')');
      }
    }
    advance(t);
    const view = RIG.facingInfo(facing).view;

    // ----- body channel -----
    let cur = bodyChanges[bodyChanges.length - 1], prev = bodyChanges[bodyChanges.length - 2];
    let pose = Object.assign({}, RIG.DEFAULT_POSE, poseFor('stand', view), poseFor(prev ? prev.p : 'stand', view));
    pose = blendPose(pose, poseFor(cur.p, view), cur.dur ? ev(t, cur.t, cur.dur) : 1);
    const bodyT = cur.t;

    // ----- sitting / lying -----
    const hipH = (B.thigh + B.shin) * 0.985 + B.ankle;
    if (sit && sit.lie) {
      pose = Object.assign(pose, { rot: sit.dir === 'right' ? 90 : -90, hpL: 0, knL: 0, hpR: 0, knR: 0, lean: 0 });
      if (view !== 'side') facing = 'right';
    } else if (sit) {
      const seat = sit.seat || markSeat || (B.shin + B.ankle + 2);
      let k = ev(t, sit.t0, sit.dur);
      if (sit.up) k = 1 - ev(t, sit.tu, sit.dur);
      const sp = view === 'side'
        ? { y: hipH - seat, hpL: 86, knL: 86, hpR: 92, knR: 92, anL: 0, anR: 0, lean: sit.slump ? 16 : 4, neck: sit.slump ? 18 : pose.neck || 0 }
        : { y: hipH - seat, fsL: 0.3, fsR: 0.3, ssL: clamp((seat - B.thigh * 0.3 - B.ankle) / B.shin, 0.15, 1), ssR: clamp((seat - B.thigh * 0.3 - B.ankle) / B.shin, 0.15, 1), hpL: 10, hpR: 10, knL: -6, knR: -6 };
      pose = blendPose(pose, sp, k);
    }

    // ----- locomotion -----
    let vel = 0, stepIdx = null, gaitNow = null;
    const L = loco || lastLoco;
    if (L && t >= L.t0) {
      const sc = scaleAtY(y);
      const travelled = Math.hypot(x - L.x0, (y - L.y0) * 2.2) / Math.max(0.05, sc);
      const cyc = L.depth ? cycleFront(ch, L.gait, travelled) : cyclePose(ch, L.gait, travelled);
      if (loco) { pose = Object.assign(pose, cyc); vel = (L.x1 - L.x0) / (L.t1 - L.t0); const G = GAITS[L.gait] || GAITS.walk; stepIdx = Math.floor(travelled / (B.thigh * G.stride * 1.8)); gaitNow = L.gait; }
      else {
        const k = ev(t, L.t1, 0.3, 'out');
        if (k < 1) {
          const settle = Object.assign({}, pose);
          pose = blendPose(Object.assign({}, pose, cyc), settle, k);
        }
      }
    }
    if (slide) vel = (slide.x1 - slide.x0) / slide.dur;

    // ----- gestures -----
    let gestureFace = null;
    for (const gst of gestures) {
      if (t < gst.t0 || t > gst.t0 + gst.d) continue;
      const fn = GESTURES[gst.name];
      if (!fn) { SF.warn('gesture', 'unknown gesture "' + gst.name + '"'); continue; }
      const u = t - gst.t0;
      const inD = Math.min(0.25, gst.d * 0.25), outD = Math.min(0.3, gst.d * 0.3);
      const env = Math.min(ev(u, 0, inD, 'out'), 1 - ev(u, gst.d - outD, outD, 'in'));
      const gp = fn(u, gst.d, view, spec);
      if (gp.face && env > 0.5) gestureFace = gp.face;
      const gp2 = Object.assign({}, gp); delete gp2.face;
      pose = blendPose(pose, gp2, env);
    }

    // ----- face & look -----
    const poseFace = poseFor(cur.p, view).face;
    pose.face = gestureFace || (exprT >= bodyT || !poseFace ? expr : poseFace);
    const lc = looks[looks.length - 1], lp = looks[looks.length - 2];
    const lk = lp ? blendLook(lp.v, lc.v, ev(t, lc.t, 0.3)) : lc.v;
    pose.lookX = (pose.lookX || 0) + lk.lookX; pose.lookY = (pose.lookY || 0) + lk.lookY; pose.turn = (pose.turn || 0) + lk.turn;
    for (const [a0, a1] of talk) {
      if (t >= a0 && t <= a1) {
        const u = t - a0;
        pose.nod = (pose.nod || 0) + 0.12 * Math.sin(u * 9) * Math.sin(u * 2.3);
        if (ch.face.talkMouth) pose.mouth = 0.5 + 0.5 * Math.sin(u * 21) * Math.abs(Math.sin(u * 5.1));
      }
    }

    // ----- idle life -----
    const seed = SF.hashStr(name || ch.name);
    if (!loco && !(sit && sit.lie)) {
      pose.squash = (pose.squash || 1) * (1 + 0.006 * Math.sin(t * 2 * Math.PI * 0.27 + seed));
      pose.lean = (pose.lean || 0) + 0.7 * noise(t * 0.35, seed);
    }
    if (!(sit && sit.lie && expr === 'sleep')) pose.blink = Math.max(pose.blink || 0, blinkAt(t, seed, exprT));
    return { x, y, s: scaleAtY(y), facing, pose, alpha, hold, vel, view, char: ch, step: stepIdx, gait: gaitNow, z: markZ };
  }

  function blendLook(a, b, k) { return { lookX: lerp(a.lookX, b.lookX, k), lookY: lerp(a.lookY, b.lookY, k), turn: lerp(a.turn, b.turn, k) }; }
  function lookTarget(tg, x, scene) {
    if (tg === 'camera' || tg === 'front' || !tg) return { lookX: 0, lookY: 0, turn: 0 };
    if (tg === 'left') return { lookX: -0.9, lookY: 0, turn: -0.35 };
    if (tg === 'right') return { lookX: 0.9, lookY: 0, turn: 0.35 };
    if (tg === 'up') return { lookX: 0, lookY: -1, turn: 0 };
    if (tg === 'down') return { lookX: 0, lookY: 1, turn: 0 };
    const p = resolveX(tg, scene);
    const dx = clamp((p.x - x) / 420, -1, 1);
    return { lookX: dx, lookY: p.y !== undefined && p.y < 500 ? -0.5 : 0, turn: dx * 0.3 };
  }
  function blinkAt(t, seed, exprT) {
    // a blink every ~2.4-5s, 0.14s long, plus one at expression changes
    let b = 0;
    const per = 3.6;
    const i = Math.floor(t / per);
    for (let j = i - 1; j <= i + 1; j++) {
      const tb = j * per + rnd(j, seed) * (per - 0.4);
      const d = t - tb;
      if (d >= 0 && d < 0.16) b = Math.max(b, Math.sin((d / 0.16) * Math.PI));
    }
    const de = t - exprT + 0.05;
    if (de >= 0 && de < 0.14) b = Math.max(b, Math.sin((de / 0.14) * Math.PI));
    return b;
  }
  function defaultGestureDur(n) { return { reach: 1.4, hug: 2.0, wave: 1.6, nod: 1.0, shake: 1.1, shrug: 1.3, sigh: 1.8, point: 1.6, fingerUp: 2.0, raiseHand: 1.5, facepalm: 1.8, scratchHead: 1.6, clap: 1.4, fistPump: 1.2, stretch: 2.2, yawn: 1.8, wipeEyes: 1.6, tap: 0.8, jumpJoy: 0.9, flinch: 0.6, shiver: 1.5, laugh: 1.4, cry: 2.5, breathe: 2.0, typing: 2.5, scroll: 2.5 }[n] || 1.2; }
  const autoDur = (text) => clamp(0.6 + String(text || '').split(/\s+/).length / 2.6, 1.3, 5.5);

  SF.acting = { POSES, GAITS, GESTURES, poseFor, blendPose, cyclePose, cycleFront, actorAt, resolveX, autoDur, defaultGestureDur };
})();
