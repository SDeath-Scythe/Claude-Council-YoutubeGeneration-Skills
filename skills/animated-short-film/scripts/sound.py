#!/usr/bin/env python3
"""
sound.py — score, sound effects, ambience and the final mix for a film, driven by build/film.json.

  python3 sound.py <filmDir> all                 # score + sfx + ambience + mix + mux onto the video
  python3 sound.py <filmDir> score|sfx|mix|mux   # one stage
  options:
    --music track.(wav|mp3|m4a)  use a supplied/licensed track instead of the generated score
    --voice <dir>                 voice lines: <dir>/<n>.wav where n = caption number (1-based) or caption shot id
    --video build/video.mp4       picture to mux (default: video.mp4, else preview.mp4)
    --target -14                  integrated loudness (LUFS); YouTube normalises to about -14

The score is composed from the film's chapters: each chapter's `mood` picks a progression and texture, its
`energy` (0..1) picks how many instruments play, a recurring motif opens the film and returns fuller at the end,
shots flagged music.silence drop the score to near-silence, music.hit lands the loudest chord of the film.
Needs only numpy + scipy. Everything is deterministic (seeded) so re-runs match.
"""
import json, math, os, subprocess, sys, wave
import numpy as np
from scipy import signal

SR = 48000
RNG = np.random.default_rng(1234)

# ---------------------------------------------------------------- utils
def db(x): return 10 ** (x / 20.0)
def silence(sec): return np.zeros((int(sec * SR), 2), np.float32)
def place(buf, snd, t, gain=1.0, pan=0.0):
    """mix mono/stereo snd into stereo buf at time t (s) with equal-power pan"""
    i = int(round(t * SR))
    if snd.ndim == 1:
        l, r = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
        snd = np.stack([snd * l * 1.414, snd * r * 1.414], 1)
    if i >= len(buf) or i + len(snd) <= 0: return
    a0 = max(0, i); b0 = min(len(buf), i + len(snd))
    buf[a0:b0] += snd[a0 - i:b0 - i] * gain
def env_adsr(n, a, d, s, r, sustain_len=None):
    a, d, r = int(a * SR), int(d * SR), int(r * SR)
    e = np.ones(n, np.float32) * s
    a = min(a, n); e[:a] = np.linspace(0, 1, a, endpoint=False) if a else e[:a]
    d2 = min(d, n - a)
    if d2 > 0: e[a:a + d2] = np.linspace(1, s, d2, endpoint=False)
    if r > 0 and n > r: e[n - r:] *= np.linspace(1, 0, r) ** 1.5
    return e
def lowpass(x, fc, order=2):
    b, a = signal.butter(order, min(0.99, fc / (SR / 2)), 'low'); return signal.lfilter(b, a, x, axis=0).astype(np.float32)
def highpass(x, fc, order=2):
    b, a = signal.butter(order, min(0.99, fc / (SR / 2)), 'high'); return signal.lfilter(b, a, x, axis=0).astype(np.float32)
def bandpass(x, f1, f2, order=2):
    b, a = signal.butter(order, [max(1e-4, f1 / (SR / 2)), min(0.99, f2 / (SR / 2))], 'band'); return signal.lfilter(b, a, x, axis=0).astype(np.float32)
def noise(sec, seed=None):
    r = np.random.default_rng(seed) if seed is not None else RNG
    return r.standard_normal(int(sec * SR)).astype(np.float32)
def mtof(m): return 440.0 * 2 ** ((m - 69) / 12.0)
def write_wav(path, x):
    x = np.clip(x, -1, 1)
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype('<i2').tobytes())
def read_audio(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 's16le', '-ac', '2', '-ar', str(SR), '-'], capture_output=True, check=True).stdout
    return (np.frombuffer(raw, '<i2').reshape(-1, 2).astype(np.float32) / 32768.0)

# ---------------------------------------------------------------- loudness (ITU-R BS.1770-4)
def lufs(x):
    if x.ndim == 1: x = np.stack([x, x], 1)
    b1, a1 = [1.53512485958697, -2.69169618940638, 1.19839281085285], [1.0, -1.69065929318241, 0.73248077421585]
    b2, a2 = [1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621]
    y = signal.lfilter(b2, a2, signal.lfilter(b1, a1, x, axis=0), axis=0)
    blk, hop = int(0.4 * SR), int(0.1 * SR)
    if len(y) < blk: return -70.0
    p = np.cumsum(np.concatenate([np.zeros((1, 2)), y ** 2]), 0)
    idx = np.arange(0, len(y) - blk, hop)
    ms = ((p[idx + blk] - p[idx]) / blk).sum(1)
    l = -0.691 + 10 * np.log10(ms + 1e-12)
    g = ms[l > -70]
    if not len(g): return -70.0
    rel = -0.691 + 10 * np.log10(g.mean()) - 10
    g2 = ms[(l > -70) & (l > rel)]
    return float(-0.691 + 10 * np.log10(g2.mean() + 1e-12))
def true_peak(x):
    up = signal.resample_poly(x[: SR * 600], 4, 1, axis=0)
    return float(20 * np.log10(np.abs(up).max() + 1e-12))
def limiter(x, ceiling_db=-1.2, look=0.005, release=0.08):
    c = db(ceiling_db)
    a = np.abs(x).max(1)
    w = max(1, int(look * SR))
    from scipy.ndimage import maximum_filter1d
    pk = maximum_filter1d(a, size=2 * w + 1)
    gr = np.minimum(1.0, c / np.maximum(pk, 1e-9))
    # smooth: instant attack (already looked ahead), exponential release
    coef = math.exp(-1.0 / (release * SR))
    g = signal.lfilter([1 - coef], [1, -coef], gr)
    g = np.minimum(g, gr)
    return (x * g[:, None]).astype(np.float32)

# ---------------------------------------------------------------- instruments
_tables = {}
def saw_table(maxh):
    if maxh not in _tables:
        n = 4096; ph = np.arange(n) / n
        t = np.zeros(n)
        for k in range(1, maxh + 1): t += np.sin(2 * np.pi * k * ph) / k
        _tables[maxh] = (t / np.abs(t).max()).astype(np.float32)
    return _tables[maxh]
def osc_saw(f, n, vib=0.0, vib_rate=5.0, seed=0):
    maxh = int(max(1, min(60, (SR * 0.42) / f)))
    tab = saw_table(maxh)
    t = np.arange(n) / SR
    fr = f * (1 + vib * np.sin(2 * np.pi * vib_rate * t + seed))
    ph = (np.cumsum(fr) / SR + (seed * 0.137) % 1.0) % 1.0
    return tab[(ph * len(tab)).astype(np.int32)]

def piano(f, dur, vel=0.7, felt=0.6):
    tail = 1.6
    n = int((dur + tail) * SR); t = np.arange(n, dtype=np.float32) / SR
    out = np.zeros(n, np.float32)
    B = 0.00032
    for k in range(1, 11):
        fk = f * k * math.sqrt(1 + B * k * k)
        if fk > SR * 0.4: break
        amp = (vel ** (0.6 + 0.35 * k * (1 + felt))) / (k ** (1.25 + felt * 0.5))
        d1 = (1.8 + 1.4 * k) * (f / 330) ** 0.35
        d2 = (0.35 + 0.18 * k) * (f / 330) ** 0.5
        e = 0.55 * np.exp(-t * d1) + 0.45 * np.exp(-t * d2)
        out += amp * e * np.sin(2 * np.pi * fk * t + k * 0.7)
    a = int(0.004 * SR + felt * 0.006 * SR); out[:a] *= np.linspace(0, 1, a)
    i = int(dur * SR); out[i:] *= np.exp(-(t[i:] - dur) * 7.0)
    h = int(0.02 * SR); out[:h] += lowpass(noise(0.02, int(f)), 1800 - 900 * felt)[:h] * 0.05 * vel * np.linspace(1, 0, h)
    return out * 0.32

def pad(freqs, dur, attack=1.6, release=2.2, cutoff=1400, detune=0.006, seed=0):
    n = int((dur + release) * SR); out = np.zeros(n, np.float32)
    for j, f in enumerate(freqs):
        for d in (-detune, 0, detune):
            out += osc_saw(f * (1 + d), n, vib=0.0015, vib_rate=0.25 + 0.1 * j, seed=seed + j * 3 + int(d * 1000))
    out /= max(1, len(freqs) * 3)
    out = lowpass(out, cutoff)
    return out * env_adsr(n, attack, 0.5, 0.85, release) * 0.5

def strings(freqs, dur, attack=0.9, release=1.6, cutoff=2600, seed=0):
    n = int((dur + release) * SR); out = np.zeros(n, np.float32)
    for j, f in enumerate(freqs):
        for d in (-0.004, 0.0035):
            out += osc_saw(f * (1 + d), n, vib=0.004, vib_rate=5.2 + 0.3 * j, seed=seed + j * 5)
    out /= max(1, len(freqs) * 2)
    out = lowpass(highpass(out, 140), cutoff)
    return out * env_adsr(n, attack, 0.3, 0.9, release) * 0.45

def bass(f, dur, vel=0.7):
    n = int((dur + 0.6) * SR); t = np.arange(n) / SR
    x = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t) + 0.08 * np.sin(6 * np.pi * f * t)
    return (x * env_adsr(n, 0.02, 0.3, 0.7, 0.6) * vel * 0.4).astype(np.float32)

def bell(f, dur=2.5, vel=0.6):
    n = int(dur * SR); t = np.arange(n) / SR
    idx = 2.2 * np.exp(-t * 3)
    x = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * 3.5 * t)) * np.exp(-t * 1.6)
    return (x * vel * 0.22).astype(np.float32)

def kick(vel=0.8):
    n = int(0.45 * SR); t = np.arange(n) / SR
    f = 48 + 90 * np.exp(-t * 30)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)
    return (x * vel * 0.8).astype(np.float32)
def shaker(vel=0.4, seed=0):
    x = highpass(noise(0.09, seed), 5000) * np.exp(-np.arange(int(0.09 * SR)) / SR * 45)
    return x * vel * 0.25
def boom(vel=1.0):
    n = int(3.0 * SR); t = np.arange(n) / SR
    f = 30 + 40 * np.exp(-t * 4)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.4)
    x += lowpass(noise(3.0, 9), 200) * np.exp(-t * 3) * 0.6
    return (x * vel * 0.9).astype(np.float32)
def swell(dur=1.6, vel=0.5, seed=4):
    n = int(dur * SR); t = np.arange(n) / SR
    x = noise(dur, seed); x = bandpass(x, 600, 9000)
    return (x * (t / dur) ** 2.5 * vel * 0.35).astype(np.float32)

def reverb(x, sec=2.6, wet=0.28, predelay=0.02, seed=7):
    n = int(sec * SR); t = np.arange(n) / SR
    r = np.random.default_rng(seed)
    ir = np.zeros((n, 2), np.float32)
    for c in range(2):
        ir[:, c] = r.standard_normal(n) * np.exp(-t * (6.9 / sec))
    ir = lowpass(ir, 6500)
    ir[: int(predelay * SR)] = 0
    ir /= np.sqrt((ir ** 2).sum(0)) + 1e-9
    y = np.stack([signal.fftconvolve(x[:, c], ir[:, c])[: len(x)] for c in range(2)], 1).astype(np.float32)
    return x * (1 - wet * 0.5) + y * wet

# ---------------------------------------------------------------- harmony
NOTE = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11}
MAJOR = [0, 2, 4, 5, 7, 9, 11]
MOODS = {  # progression (scale degrees, 1-based; 7ths allowed with suffix), base energy, arpeggio style
    'hopeful': ([1, 5, 6, 4], 'flow'), 'uplifting': ([4, 5, 6, 1], 'flow'), 'triumphant': ([4, 5, 6, 1], 'drive'),
    'melancholy': ([6, 4, 1, 5], 'slow'), 'sad': ([6, 4, 1, 5], 'slow'), 'lonely': ([6, 3, 4, 6], 'sparse'),
    'tense': ([6, 6, 4, 5], 'pulse'), 'anxious': ([6, 7, 6, 5], 'pulse'), 'tender': ([1, 3, 4, 1], 'flow'),
    'warm': ([1, 4, 1, 5], 'flow'), 'reflective': ([1, 4, 6, 4], 'sparse'), 'calm': ([1, 4, 1, 4], 'sparse'),
    'neutral': ([1, 6, 4, 5], 'slow'), 'determined': ([6, 4, 1, 5], 'drive'), 'building': ([6, 4, 1, 5], 'drive'),
    'bittersweet': ([4, 1, 5, 6], 'flow'), 'playful': ([1, 4, 5, 4], 'bounce'), 'mysterious': ([6, 2, 6, 3], 'sparse'),
}
def chord_notes(root_midi, degree, octave_shift=0, seventh=False):
    tones = []
    for k in (0, 2, 4) + ((6,) if seventh else ()):
        d = degree - 1 + k
        tones.append(root_midi + MAJOR[d % 7] + 12 * (d // 7) + 12 * octave_shift)
    return tones
def voice_lead(prev, target):
    """choose an inversion of target close to prev (lists of midi)"""
    best, bd = target, 1e9
    for inv in range(3):
        c = sorted([n + 12 * (1 if i < inv else 0) for i, n in enumerate(target)])
        for sh in (-12, 0, 12):
            cc = [n + sh for n in c]
            d = sum(abs(a - b) for a, b in zip(sorted(prev), cc)) if prev else abs(cc[0] - 60)
            if d < bd: best, bd = cc, d
    return best

# ---------------------------------------------------------------- score
def compose(info):
    dur = info['duration']; music = info.get('music') or {}
    key = NOTE.get(str(music.get('key', 'C')).replace('m', ''), 0)
    root = 48 + key  # C3-ish
    bpm = float(music.get('bpm', 72))
    motif = music.get('motif', [3, 2, 1, 2, 3, 5, 3])
    L = int((dur + 4) * SR)
    bus = {k: np.zeros((L, 2), np.float32) for k in ('piano', 'pad', 'strings', 'bass', 'perc', 'bell', 'fx')}
    shots = info['shots']
    silences = [(s['start'], s['end']) for s in shots if s.get('silence')]
    hits = [s['start'] for s in shots if s.get('hit')]
    chapters = info['chapters'] or [{'start': 0, 'end': dur, 'mood': 'neutral', 'energy': 0.4}]
    prev = None; motif_done = set(); nch = len(chapters)
    for ci, ch in enumerate(chapters):
        t0, t1 = ch['start'], ch['end']
        mood = ch.get('mood', 'neutral'); energy = float(ch.get('energy', 0.4))
        prog, style = MOODS.get(mood, MOODS['neutral'])
        bar = 4 * 60 / bpm
        nb = max(1, round((t1 - t0) / bar)); bar = (t1 - t0) / nb   # stretch bars to fit the chapter exactly
        beat = bar / 4
        for b in range(nb):
            tb = t0 + b * bar
            deg = prog[b % len(prog)]
            tri = chord_notes(root + 12, deg)  # around C4
            v = voice_lead(prev, tri); prev = v
            freqs = [mtof(m) for m in v]
            in_sil = any(a - 0.4 <= tb < z for a, z in silences)
            if in_sil: continue
            # pad (from low energy up)
            if energy > 0.12 or style == 'sparse':
                place(bus['pad'], pad(freqs, bar * 1.02, attack=min(1.8, bar * 0.45), seed=ci * 31 + b), tb, gain=0.55 + 0.4 * energy)
            # bass
            if energy > 0.28:
                place(bus['bass'], bass(mtof(chord_notes(root - 12, deg)[0]), bar * 0.95, vel=0.5 + 0.4 * energy), tb, gain=0.9)
            # strings
            if energy > 0.45:
                place(bus['strings'], strings([mtof(m) for m in voice_lead(None, chord_notes(root, deg))] + [mtof(v[-1] + 12)], bar * 1.0, seed=b), tb, gain=0.35 + 0.5 * (energy - 0.45))
            # piano patterns
            arp = [v[0] - 12, v[1], v[2], v[0] + 12, v[2], v[1]]
            if style == 'sparse':
                pts = [(0, v[0] - 12, 0.55), (2, v[2], 0.4)] if b % 2 == 0 else [(0, v[1], 0.45)]
            elif style == 'slow':
                pts = [(0, v[0] - 12, 0.6), (1, v[1], 0.42), (2, v[2], 0.45), (3, v[1], 0.38)]
            elif style == 'pulse':
                pts = [(i * 0.5, v[0], 0.32 + 0.1 * (i % 2 == 0)) for i in range(8)] + [(0, v[0] - 12, 0.55)]
            elif style == 'bounce':
                pts = [(0, v[0] - 12, 0.6), (0.5, v[2], 0.35), (1, v[1], 0.45), (1.5, v[2], 0.35), (2, v[0] - 12 + 7, 0.55), (2.5, v[2], 0.35), (3, v[1], 0.45), (3.5, v[0] + 12, 0.35)]
            else:  # flow / drive: 8ths
                pts = [(i * 0.5, arp[i % len(arp)], 0.34 + 0.12 * (i % 4 == 0)) for i in range(8)]
                if style == 'drive': pts += [(0, v[0] - 24, 0.6), (2, v[0] - 24, 0.5)]
            humanize = np.random.default_rng(ci * 100 + b)
            for (bt, m, vel) in pts:
                tt = tb + bt * beat + humanize.normal(0, 0.006)
                place(bus['piano'], piano(mtof(m), beat * (1.6 if style in ('slow', 'sparse') else 1.0), vel=min(1.0, vel * (0.7 + 0.6 * energy))), tt, gain=1.0, pan=(m - 60) / 40.0)
            # percussion for driving sections
            if energy > 0.62 and style in ('drive', 'flow', 'pulse'):
                for i in range(4):
                    if i % 2 == 0: place(bus['perc'], kick(0.5 + 0.3 * energy), tb + i * beat, gain=0.8)
                for i in range(8): place(bus['perc'], shaker(0.35, seed=b * 8 + i), tb + i * beat / 2 + 0.01, gain=0.6, pan=0.3)
        # motif: first chapter (simple), last chapter (with bells + octave)
        if ci in (0, nch - 1) and ci not in motif_done and t1 - t0 > 6:
            motif_done.add(ci)
            mt0 = t0 + (2 * 4 * 60 / bpm if ci == 0 else 0.5 * (t1 - t0) - 2)
            step = 60 / bpm
            for k, d in enumerate(motif):
                m = root + 24 + MAJOR[(d - 1) % 7] + 12 * ((d - 1) // 7)
                tt = mt0 + k * step * (1.0 if k < len(motif) - 1 else 1.0)
                if not any(a - 0.4 <= tt < z for a, z in silences):
                    place(bus['piano'], piano(mtof(m), step * 1.5, vel=0.55 if ci == 0 else 0.7), tt, gain=1.1)
                    if ci == nch - 1: place(bus['bell'], bell(mtof(m + 12), 2.4, 0.5), tt, gain=0.8, pan=0.2)
    # hits: the loudest moment — chord stab + boom, preceded by a swell
    for th in hits:
        place(bus['fx'], swell(1.5), th - 1.5, gain=0.9)
        place(bus['fx'], boom(1.0), th, gain=1.0)
        for m in chord_notes(root + 12, 1) + [root, root + 24]:
            place(bus['piano'], piano(mtof(m), 3.0, vel=0.95), th, gain=0.9)
        place(bus['strings'], strings([mtof(m) for m in chord_notes(root, 1)] + [mtof(root + 24)], 6.0, attack=0.25), th, gain=0.9)
    # ending: final tonic chord ringing out
    tend = dur - 6.0
    if tend > 0:
        for m in chord_notes(root + 12, 1) + [root]:
            place(bus['piano'], piano(mtof(m), 4.0, vel=0.6), tend, gain=0.8)
        place(bus['pad'], pad([mtof(m) for m in chord_notes(root + 12, 1)], 5.0, attack=1.0), tend, gain=0.7)
    gains = {'piano': 1.0, 'pad': 0.42, 'strings': 0.55, 'bass': 0.6, 'perc': 0.35, 'bell': 0.45, 'fx': 0.55}
    mix = sum(bus[k] * gains[k] for k in bus)
    mix = reverb(mix, sec=2.8, wet=0.32)
    # silence automation: duck to near-silence across flagged shots (with short fades)
    g = np.ones(len(mix), np.float32)
    for a, z in silences:
        i0, i1 = int((a - 0.5) * SR), int(z * SR)
        f = int(0.5 * SR)
        if i0 > 0: g[i0:i0 + f] = np.minimum(g[i0:i0 + f], np.linspace(1, db(-38), f))
        g[i0 + f:i1] = np.minimum(g[i0 + f:i1], db(-38))
    fo = int(2.5 * SR); end = int(dur * SR)
    g[max(0, end - fo):end] *= np.linspace(1, 0, min(fo, end))
    g[end:] = 0
    mix *= g[:, None]
    return mix[: int(dur * SR) + SR]

# ---------------------------------------------------------------- sound effects
def sfx_bank(name, o, seed):
    r = np.random.default_rng(seed)
    n = lambda sec: noise(sec, int(r.integers(1e9)))
    if name in ('footstep', 'footstep_run'):
        d = 0.16 if name == 'footstep' else 0.12
        surf = o.get('surface', 'floor')
        x = n(d); t = np.arange(len(x)) / SR
        lo, hi = (90, 900) if surf == 'floor' else (120, 2600) if surf == 'street' else (200, 4000)
        thump = bandpass(x, lo, hi) * np.exp(-t * (40 if name == 'footstep' else 55))
        click = highpass(n(d), 2500) * np.exp(-t * 120) * (0.35 if surf != 'floor' else 0.18)
        if surf == 'grass': click = bandpass(n(d), 1500, 7000) * np.exp(-t * 25) * 0.5
        return (thump * 1.4 + click) * (0.8 + 0.4 * r.random()) * (1.3 if name == 'footstep_run' else 1)
    if name in ('alarm', 'alarm_ring'):
        dur = o.get('dur', 2.0); x = np.zeros(int(dur * SR), np.float32)
        for k in range(int(dur / 0.5)):
            for j, f in enumerate((1318.5, 1567.98, 1318.5, 1975.5)):
                tt = k * 0.5 + j * 0.09
                seg = np.sin(2 * np.pi * f * np.arange(int(0.07 * SR)) / SR) * np.exp(-np.arange(int(0.07 * SR)) / SR * 30)
                i = int(tt * SR); x[i:i + len(seg)] += seg[: max(0, len(x) - i)] * 0.35
        return x
    if name == 'phone_buzz':
        dur = o.get('dur', 1.2); t = np.arange(int(dur * SR)) / SR
        g = ((t % 0.6) < 0.38).astype(np.float32)
        return (np.sign(np.sin(2 * np.pi * 170 * t)) * 0.25 + np.sin(2 * np.pi * 340 * t) * 0.15) * g * 0.35
    if name in ('notification', 'ding', 'message'):
        return np.concatenate([bell(1046.5, 0.25, 0.8), bell(1568, 0.9, 0.8)]) * 1.4
    if name in ('tap', 'click', 'switch'):
        x = n(0.03); return highpass(x, 2000) * np.exp(-np.arange(len(x)) / SR * 220) * 0.6
    if name in ('door_open', 'door_close', 'door'):
        t = np.arange(int(0.5 * SR)) / SR
        th = lowpass(n(0.5), 300) * np.exp(-t * 18) * 1.6
        latch = highpass(n(0.5), 1800) * np.exp(-np.maximum(0, t - (0.02 if name != 'door_open' else 0.0)) * 90) * 0.4
        return th + latch
    if name in ('paper', 'paper_pin', 'pin'):
        x = n(0.35); t = np.arange(len(x)) / SR
        return bandpass(x, 1500, 7000) * (np.exp(-t * 9) * (0.5 + 0.5 * (r.random(len(x)) > 0.92))) * 0.5
    if name in ('crumple', 'paper_crumple'):
        dur = o.get('dur', 0.9); x = np.zeros(int(dur * SR), np.float32)
        for k in range(60):
            i = int(r.random() * (len(x) - 2000)); c = bandpass(n(0.02), 1000, 8000) * np.exp(-np.arange(int(0.02 * SR)) / SR * 150)
            x[i:i + len(c)] += c * r.random()
        return x * 0.7
    if name in ('marker', 'pen', 'scribble'):
        dur = o.get('dur', 0.5); t = np.arange(int(dur * SR)) / SR
        return bandpass(n(dur), 2000, 9000) * (0.5 + 0.5 * np.sin(2 * np.pi * 9 * t)) * 0.4
    if name in ('whoosh', 'swoosh', 'swish'):
        dur = o.get('dur', 0.45); t = np.arange(int(dur * SR)) / SR
        x = n(dur); f = np.linspace(400, 3000, len(x))
        y = np.zeros_like(x)
        for a, b in ((0, 0.33), (0.33, 0.66), (0.66, 1.0)):
            i0, i1 = int(a * len(x)), int(b * len(x)); fc = f[(i0 + i1) // 2]
            y[i0:i1] = bandpass(x, fc * 0.6, fc * 1.6)[i0:i1]
        return y * np.sin(np.pi * t / dur) ** 2 * 0.8
    if name in ('thud', 'impact', 'drop'):
        t = np.arange(int(0.6 * SR)) / SR
        return (np.sin(2 * np.pi * (60 + 80 * np.exp(-t * 25)) * t) * np.exp(-t * 10) + lowpass(n(0.6), 400) * np.exp(-t * 20) * 0.7) * 0.8
    if name == 'heartbeat':
        out = np.zeros(int(0.9 * SR), np.float32)
        for tt, v in ((0, 1.0), (0.22, 0.7)):
            t = np.arange(int(0.25 * SR)) / SR
            b = np.sin(2 * np.pi * 50 * t) * np.exp(-t * 18) * v
            i = int(tt * SR); out[i:i + len(b)] += b
        return out * 0.9
    if name in ('clock_tick', 'tick'):
        dur = o.get('dur', 3.0); x = np.zeros(int(dur * SR), np.float32)
        for k in range(int(dur)):
            c = highpass(n(0.02), 3000) * np.exp(-np.arange(int(0.02 * SR)) / SR * 300); i = int(k * SR); x[i:i + len(c)] += c * (0.6 if k % 2 else 0.45)
        return x
    if name in ('typing', 'keyboard'):
        dur = o.get('dur', 2.0); x = np.zeros(int(dur * SR), np.float32); tt = 0.0
        while tt < dur - 0.05:
            c = bandpass(n(0.03), 1200, 6000) * np.exp(-np.arange(int(0.03 * SR)) / SR * 160); i = int(tt * SR); x[i:i + len(c)] += c * (0.4 + 0.4 * r.random()); tt += 0.06 + r.random() * 0.12
        return x
    if name in ('sigh', 'exhale', 'breath'):
        dur = o.get('dur', 1.4); t = np.arange(int(dur * SR)) / SR
        x = bandpass(n(dur), 350, 1800); e = np.sin(np.pi * np.minimum(1, t / dur)) ** 1.5 * np.exp(-t * 0.8)
        return x * e * 0.45
    if name in ('inhale', 'gasp'):
        dur = o.get('dur', 0.45); t = np.arange(int(dur * SR)) / SR
        return bandpass(n(dur), 900, 4000) * (t / dur) ** 1.5 * np.exp(-np.maximum(0, t - dur * 0.85) * 40) * 0.45
    if name in ('panting', 'pant'):
        dur = o.get('dur', 2.0); x = np.zeros(int(dur * SR), np.float32); tt = 0.0; k = 0
        while tt < dur - 0.3:
            d = 0.22 if k % 2 == 0 else 0.26; t = np.arange(int(d * SR)) / SR
            b = bandpass(n(d), 500 if k % 2 else 900, 2500) * np.sin(np.pi * t / d) ** 2 * (0.5 if k % 2 == 0 else 0.35)
            i = int(tt * SR); x[i:i + len(b)] += b; tt += d + 0.04; k += 1
        return x * 0.6
    if name in ('bell_door', 'shop_bell'):
        return (bell(1760, 1.6, 0.7) + bell(2349, 1.6, 0.5)) * 1.2
    if name in ('register', 'cash_register'):
        return np.concatenate([sfx_bank('tap', o, seed) * 0.8, bell(2093, 1.2, 0.6)])
    if name in ('cup', 'cup_down'):
        t = np.arange(int(0.3 * SR)) / SR
        return (bandpass(n(0.3), 600, 3000) * np.exp(-t * 35) + np.sin(2 * np.pi * 1900 * t) * np.exp(-t * 28) * 0.2) * 0.6
    if name in ('rise', 'riser', 'swell'):
        return swell(o.get('dur', 1.6), 0.8)
    if name in ('hit', 'boom'):
        return boom(1.0)
    if name in ('car_pass', 'car'):
        dur = o.get('dur', 3.0); t = np.arange(int(dur * SR)) / SR
        x = lowpass(n(dur), 900) * np.exp(-((t - dur / 2) ** 2) / 0.35) * 0.9
        return x
    if name == 'thunder':
        dur = 4.0; t = np.arange(int(dur * SR)) / SR
        return lowpass(n(dur), 180) * np.exp(-t * 0.9) * (1 + 0.6 * np.sin(2 * np.pi * 1.3 * t)) * 1.2
    print(f'  ! unknown sfx "{name}" (skipped)', file=sys.stderr)
    return np.zeros(int(0.1 * SR), np.float32)

AMB = {
    'room': dict(lp=420, lvl=-46, hum=0), 'room_night': dict(lp=300, lvl=-50, hum=55, tick=True),
    'store': dict(lp=900, lvl=-40, murmur=True), 'office': dict(lp=700, lvl=-41, hum=60, typing=True),
    'street': dict(lp=700, lvl=-36, traffic=True, birds=True), 'night_street': dict(lp=500, lvl=-40, traffic=True),
    'park': dict(lp=900, lvl=-42, birds=True, wind=True), 'night_park': dict(lp=600, lvl=-46, crickets=True),
    'rain': dict(rain=True, lvl=-30), 'wind': dict(wind=True, lvl=-38), 'void': dict(lp=180, lvl=-44, drone=True),
    'gym': dict(lp=600, lvl=-42, murmur=True), 'school': dict(lp=800, lvl=-40, murmur=True),
}
def ambience(name, dur, seed):
    spec = AMB.get(name, AMB['room'])
    r = np.random.default_rng(seed)
    n = int(dur * SR); t = np.arange(n) / SR
    out = np.zeros((n, 2), np.float32)
    def nz(): return r.standard_normal(n).astype(np.float32)
    if 'lp' in spec:
        for c in range(2): out[:, c] += lowpass(nz(), spec['lp']) * db(spec['lvl']) * 8
    if spec.get('hum'):
        h = (np.sin(2 * np.pi * spec['hum'] * t) + 0.3 * np.sin(4 * np.pi * spec['hum'] * t)) * db(-58)
        out += h[:, None]
    if spec.get('traffic'):
        tr = lowpass(nz(), 260) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.05 * t + r.random() * 6)) * db(-36) * 6
        out += tr[:, None]
    if spec.get('wind'):
        w = bandpass(nz(), 150, 900) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.08 * t + 1.3) ** 2) * db(-40) * 6
        out[:, 0] += w; out[:, 1] += np.roll(w, 2000)
    if spec.get('rain'):
        for c in range(2): out[:, c] += bandpass(nz(), 800, 9000) * db(-34) * 4 + lowpass(nz(), 400) * db(-40) * 4
    if spec.get('murmur'):
        m = bandpass(nz(), 300, 1800) * (0.6 + 0.4 * np.abs(np.sin(2 * np.pi * 0.7 * t + r.random()))) * db(-46) * 6
        out[:, 0] += m; out[:, 1] += np.roll(m, 3000)
    if spec.get('drone'):
        d = (np.sin(2 * np.pi * 55 * t) * 0.6 + np.sin(2 * np.pi * 82.4 * t + 0.4 * np.sin(2 * np.pi * 0.1 * t)) * 0.3) * db(-44)
        out += d[:, None]
    ev = []
    if spec.get('birds'):
        tt = r.random() * 2
        while tt < dur - 1:
            f0 = 2500 + r.random() * 2500; k = int(0.12 * SR); tk = np.arange(k) / SR
            chirp = np.sin(2 * np.pi * (f0 + 1500 * np.sin(2 * np.pi * 18 * tk)) * tk) * np.sin(np.pi * tk / 0.12) * db(-44)
            ev.append((tt, chirp, r.random() * 1.6 - 0.8)); tt += 0.8 + r.random() * 3.5
    if spec.get('crickets'):
        tt = 0.0
        while tt < dur - 0.5:
            k = int(0.25 * SR); tk = np.arange(k) / SR
            c = np.sin(2 * np.pi * 4300 * tk) * ((tk * 60) % 1 < 0.5) * np.sin(np.pi * tk / 0.25) * db(-50)
            ev.append((tt, c.astype(np.float32), r.random() - 0.5)); tt += 0.6 + r.random() * 0.5
    if spec.get('tick'):
        for k in range(int(dur)):
            c = highpass(r.standard_normal(int(0.015 * SR)).astype(np.float32), 3000) * np.exp(-np.arange(int(0.015 * SR)) / SR * 300) * db(-44)
            ev.append((k + 0.05, c, 0.4))
    if spec.get('typing'):
        tt = 0.0
        while tt < dur - 0.2:
            if r.random() < 0.6:
                c = bandpass(r.standard_normal(int(0.02 * SR)).astype(np.float32), 1500, 6000) * np.exp(-np.arange(int(0.02 * SR)) / SR * 200) * db(-52)
                ev.append((tt, c, -0.5))
            tt += 0.08 + r.random() * 0.5
    for tt, s, p in ev: place(out, s.astype(np.float32), tt, 1.0, p)
    fl = int(0.25 * SR)
    if n > 2 * fl: out[:fl] *= np.linspace(0, 1, fl)[:, None]; out[-fl:] *= np.linspace(1, 0, fl)[:, None]
    return out

# target RMS (dBFS) per effect before the bus gain — footsteps sit low, UI sounds medium, impacts high
SFX_LEVEL = {'footstep': -36, 'footstep_run': -33, 'marker': -36, 'pen': -36, 'scribble': -36, 'paper': -34, 'paper_pin': -34, 'pin': -34,
             'crumple': -32, 'tap': -32, 'click': -32, 'switch': -32, 'notification': -27, 'ding': -27, 'message': -27, 'alarm': -26,
             'alarm_ring': -26, 'phone_buzz': -29, 'door': -27, 'door_open': -27, 'door_close': -26, 'whoosh': -29, 'swoosh': -29,
             'swish': -30, 'thud': -24, 'impact': -24, 'drop': -26, 'heartbeat': -25, 'clock_tick': -36, 'tick': -36, 'typing': -36,
             'keyboard': -36, 'sigh': -30, 'exhale': -31, 'breath': -32, 'inhale': -32, 'gasp': -30, 'panting': -31, 'pant': -31,
             'bell_door': -28, 'shop_bell': -28, 'register': -29, 'cash_register': -29, 'cup': -31, 'cup_down': -31,
             'rise': -27, 'riser': -27, 'swell': -27, 'hit': -22, 'boom': -22, 'car_pass': -30, 'car': -30, 'thunder': -24}

def build_sfx(info):
    L = int((info['duration'] + 4) * SR)
    sfx = np.zeros((L, 2), np.float32); amb = np.zeros((L, 2), np.float32)
    for i, e in enumerate(info['sfx']):
        snd = sfx_bank(e['name'], e, seed=1000 + i).astype(np.float32)
        # calibrate every effect to a sensible level for its kind, so synthesis amplitudes never decide the mix
        rms = float(np.sqrt(np.mean(snd ** 2)) + 1e-9)
        tgt = SFX_LEVEL.get(e['name'], -30.0)
        place(sfx, snd * (db(tgt) / rms), e['t'], gain=db(e.get('db', 0)) * e.get('gain', 1.0), pan=float(e.get('pan', 0)))
    # ambience: merge consecutive shots with the same bed into one continuous bed
    runs = []
    for a in info['amb']:
        if runs and runs[-1]['name'] == a['name'] and abs(runs[-1]['t1'] - a['t0']) < 0.05: runs[-1]['t1'] = a['t1']
        else: runs.append(dict(a))
    for k, rn in enumerate(runs):
        bed = ambience(rn['name'], rn['t1'] - rn['t0'] + 0.5, seed=77 + k)
        place(amb, bed, max(0, rn['t0'] - 0.25), gain=rn.get('gain', 1.0))
    return sfx[: int(info['duration'] * SR) + SR], amb[: int(info['duration'] * SR) + SR]

# ---------------------------------------------------------------- mix
def mixdown(film_dir, info, args):
    A = os.path.join(film_dir, 'build', 'audio')
    rd = lambda n: read_audio(os.path.join(A, n)) if os.path.exists(os.path.join(A, n)) else None
    music = read_audio(args['music']) if args.get('music') else rd('score.wav')
    sfx, amb = rd('sfx.wav'), rd('amb.wav')
    L = int(info['duration'] * SR) + SR
    def fit(x):
        if x is None: return np.zeros((L, 2), np.float32)
        if len(x) < L: x = np.concatenate([x, np.zeros((L - len(x), 2), np.float32)])
        return x[:L]
    music, sfx, amb = fit(music), fit(sfx), fit(amb)
    if args.get('music'):  # supplied track: fade the tail to the film's end, honour silences
        end = int(info['duration'] * SR); fo = int(3 * SR)
        g = np.ones(L, np.float32); g[max(0, end - fo):end] = np.linspace(1, 0, min(fo, end)); g[end:] = 0
        for s in info['shots']:
            if s.get('silence'): i0, i1 = int((s['start'] - 0.5) * SR), int(s['end'] * SR); g[max(0, i0):i1] *= db(-30)
        music = music * g[:, None]
    voice = np.zeros((L, 2), np.float32)
    vdir = args.get('voice')
    duck = np.ones(L, np.float32)
    if vdir and os.path.isdir(vdir):
        for i, c in enumerate(info['captions']):
            for cand in (f'{i + 1}.wav', f'{i + 1:02d}.wav', f'{i + 1:03d}.wav', f"{c['shot']}.wav", f'{i + 1}.mp3'):
                p = os.path.join(vdir, cand)
                if os.path.exists(p):
                    v = read_audio(p); place(voice, v, c['t0']); a0, a1 = int(c['t0'] * SR), int((c['t0'] + len(v) / SR) * SR)
                    duck[max(0, a0 - 4800):a1 + 9600] = db(-7); break
        duck = signal.lfilter([0.002], [1, -0.998], duck).astype(np.float32) / 1.0
    mix = music * db(-1.5) * duck[:, None] + sfx * db(-3) + amb * db(-4) + voice * db(0)
    # glue: gentle bus compression, then loudness + true-peak limiting
    target = float(args.get('target', -14))
    for _ in range(2):  # push to target loudness, catch peaks with the limiter, repeat once
        mix = limiter(mix * db(target - lufs(mix)), -2.0)
    tp = true_peak(mix)
    if tp > -1.0: mix = mix * db(-1.05 - tp)  # keep inter-sample peaks under -1 dBTP
    write_wav(os.path.join(A, 'mix.wav'), mix)
    stats = dict(lufs=round(lufs(mix), 2), true_peak_db=round(true_peak(mix), 2), music_lufs=round(lufs(music), 1) if music.any() else None,
                 sfx_events=len(info['sfx']), amb_runs=len(info['amb']), duration=round(len(mix) / SR, 2), voice=bool(vdir))
    json.dump(stats, open(os.path.join(A, 'mix_stats.json'), 'w'), indent=1)
    print('mix:', stats)
    return stats

def mux(film_dir, args):
    B = os.path.join(film_dir, 'build')
    vid = args.get('video') or (os.path.join(B, 'video.mp4') if os.path.exists(os.path.join(B, 'video.mp4')) else os.path.join(B, 'preview.mp4'))
    if not os.path.exists(vid): print('no video to mux yet (render first)'); return
    out = os.path.join(B, 'final.mp4' if os.path.basename(vid) == 'video.mp4' else 'preview_av.mp4')
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', vid, '-i', os.path.join(B, 'audio', 'mix.wav'), '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', out], check=True)
    print('wrote', out)

def main():
    if len(sys.argv) < 2: print(__doc__); sys.exit(2)
    film_dir = os.path.abspath(sys.argv[1]); stage = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else 'all'
    args = {}
    for k in ('--music', '--voice', '--video', '--target'):
        if k in sys.argv: args[k[2:]] = sys.argv[sys.argv.index(k) + 1]
    fj = os.path.join(film_dir, 'build', 'film.json')
    if not os.path.exists(fj): print('build/film.json missing — run: node render.mjs <filmDir> --timeline'); sys.exit(2)
    info = json.load(open(fj))
    A = os.path.join(film_dir, 'build', 'audio'); os.makedirs(A, exist_ok=True)
    if stage in ('score', 'all') and not args.get('music'):
        print(f"composing score for {info['duration']:.1f}s, {len(info['chapters'])} chapters...")
        write_wav(os.path.join(A, 'score.wav'), np.clip(compose(info) * db(-6), -1, 1))
    if stage in ('sfx', 'all'):
        print(f"sound effects: {len(info['sfx'])} cues, ambience: {len(info['amb'])} shots")
        s, a = build_sfx(info)
        write_wav(os.path.join(A, 'sfx.wav'), np.clip(s, -1, 1)); write_wav(os.path.join(A, 'amb.wav'), np.clip(a, -1, 1))
    if stage in ('mix', 'all'): mixdown(film_dir, info, args)
    if stage in ('mux', 'all'): mux(film_dir, args)

if __name__ == '__main__':
    main()
