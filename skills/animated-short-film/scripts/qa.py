#!/usr/bin/env python3
"""
qa.py — measured review of a rendered film. Prints PASS/WARN/FAIL lines and writes build/review/qa_report.md,
contact sheets (one frame every N s), a phone-size strip, and an audio-arc chart.

  python3 qa.py <filmDir> [--video build/final.mp4] [--every 4] [--min 300 --max 420]

Exit code 1 if anything FAILs. WARN items are judgment calls: look at the sheet/chart before deciding.
"""
import json, os, subprocess, sys, math, wave
import numpy as np

def arg(k, d=None):
    return sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d

FILM = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else sys.exit(__doc__)
B = os.path.join(FILM, 'build'); R = os.path.join(B, 'review'); os.makedirs(R, exist_ok=True)
info = json.load(open(os.path.join(B, 'film.json')))
rlog = json.load(open(os.path.join(B, 'render_log.json'))) if os.path.exists(os.path.join(B, 'render_log.json')) else {}
_cands = [os.path.join(B, f) for f in ('final.mp4', 'preview_av.mp4') if os.path.exists(os.path.join(B, f))] or [os.path.join(B, f) for f in ('video.mp4', 'preview.mp4') if os.path.exists(os.path.join(B, f))]
video = arg('--video') or (max(_cands, key=os.path.getmtime) if _cands else None)  # newest muxed render
lines, fails, warns = [], 0, 0
def out(status, area, msg, fix=''):
    global fails, warns
    if status == 'FAIL': fails += 1
    if status == 'WARN': warns += 1
    lines.append(f"{status:4}  {area:10} {msg}" + (f"\n            -> {fix}" if fix else ''))
def mmss(t): return f"{int(t // 60)}:{int(t % 60):02d}"

dur = info['duration']; shots = info['shots']; chs = info['chapters']; caps = info['captions']
lo, hi = float(arg('--min', info.get('target', [300, 420])[0])), float(arg('--max', info.get('target', [300, 420])[1]))

# ---------------- structure ----------------
out('PASS' if lo <= dur <= hi else 'FAIL', 'length', f"{mmss(dur)} ({dur:.1f}s); target {mmss(lo)}–{mmss(hi)}", '' if lo <= dur <= hi else 'add/remove beats in story.md, then retime shots (do not just stretch holds)')
okch = len(chs) >= 3 and all(c['end'] - c['start'] >= 10 for c in chs) and abs(chs[0]['start']) < 0.01
out('PASS' if okch else 'FAIL', 'chapters', f"{len(chs)} chapters: " + ', '.join(f"{mmss(c['start'])} {c['title']}" for c in chs), '' if okch else 'YouTube needs >=3 chapters, first at 0:00, each >=10s')
short = [c for c in chs if c['end'] - c['start'] < 25]
if short: out('WARN', 'chapters', 'very short chapters: ' + ', '.join(c['title'] for c in short))
sl = [s['dur'] for s in shots]; asl = sum(sl) / len(sl)
out('PASS' if 2.5 <= asl <= 9 else 'WARN', 'pacing', f"{len(shots)} shots, average {asl:.1f}s, longest {max(sl):.1f}s ({shots[sl.index(max(sl))]['id']})")
longs = [s for s in shots if s['dur'] > 14 and not s.get('hold')]
if longs: out('WARN', 'pacing', 'long shots without hold:true: ' + ', '.join(f"{s['id']} {s['dur']:.0f}s" for s in longs), 'split them, add a camera move, or mark hold:true if the stillness is the point')
# shot scale variety
def scale(s):
    if s['insert']: return 'insert'
    z = s.get('camZoom', 1)
    return 'wide' if z < 1.35 else 'full' if z < 2.0 else 'medium' if z < 3.2 else 'close'
scales = [scale(s) for s in shots]
dist = {k: scales.count(k) for k in ('wide', 'full', 'medium', 'close', 'insert')}
okv = dist['close'] >= max(1, len(shots) * 0.1) and 1 <= dist['insert'] <= len(shots) * 0.28 and max(dist.values()) <= len(shots) * 0.6
out('PASS' if okv else 'WARN', 'coverage', 'shot scales ' + ', '.join(f"{k} {v}" for k, v in dist.items()), '' if okv else 'mix scales: establish wide, act in medium/close, cut to inserts for objects (inserts ≤ ~25% — people carry the story)')
moving = sum(1 for s in shots if s.get('camMove', 0) > 25)
out('PASS' if moving >= len(shots) * 0.3 else 'WARN', 'camera', f"{moving}/{len(shots)} shots have a camera move", '' if moving >= len(shots) * 0.3 else 'add slow push-ins/pans to held shots')
sets = {}
for s in shots: sets[s['set']] = sets.get(s['set'], 0) + 1
out('PASS', 'sets', ', '.join(f"{k}×{v}" for k, v in sets.items()))
# repeated consecutive framing (same set + same scale 3+ times)
run = 1
for a, b in zip(shots, shots[1:]):
    run = run + 1 if (a['set'], scale(a)) == (b['set'], scale(b)) else 1
    if run == 3: out('WARN', 'coverage', f"3+ consecutive {scale(b)} shots in {b['set']} around {b['id']}", 'change the angle or scale on a cut')

# ---------------- engine logs ----------------
w = rlog.get('warnings', info.get('warnings', []))
out('PASS' if not w else 'FAIL', 'engine', 'no unknown sets/props/poses/verbs' if not w else '; '.join(f"{x['kind']}: {x['msg']}" for x in w[:8]), '' if not w else 'fix the names (see references/engine-api.md for valid ones)')
v = rlog.get('violationCount', 0)
if v:
    seen = {}
    for x in rlog.get('violations', []): seen.setdefault((x.get('shot'), x['who'], x['joint']), x)
    out('FAIL', 'joints', f"{v} joint-limit clamps: " + '; '.join(f"{k[0]}:{k[1]}.{k[2]}={x['value']} (limit {x['limit']})" for k, x in list(seen.items())[:6]), 'change those poses so every joint stays in range — the clamp hides the error but the pose reads wrong')
else: out('PASS', 'joints', 'every pose inside anatomical limits')

# ---------------- captions ----------------
if caps:
    words = sum(len(c['text'].split()) for c in caps)
    bad = [c for c in caps if (c['t1'] - c['t0']) < 1.2 or len(c['text'].split()) / max(0.1, c['t1'] - c['t0']) > 3.2]
    ov = [(a['text'], b['text']) for a, b in zip(caps, caps[1:]) if b['t0'] < a['t1'] - 0.05]
    longc = [c for c in caps if len(c['text']) > 60]
    out('PASS' if not bad else 'WARN', 'captions', f"{len(caps)} lines, {words} words ({words / (dur / 60):.0f} words/min)" + (f"; too fast/short: {[c['text'] for c in bad][:3]}" if bad else ''), '' if not bad else 'give each line >=1.2s and <=3 words/s')
    if ov: out('WARN', 'captions', f"overlapping lines: {ov[:2]}")
    if longc: out('WARN', 'captions', f"long lines (>60 chars): {[c['text'] for c in longc][:2]}", 'split or cut — these films speak in short lines')
else: out('PASS', 'captions', 'no dialogue (fully wordless)')

# ---------------- picture ----------------
def ffprobe(p):
    j = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', p], capture_output=True, text=True).stdout)
    return j
if not video: out('FAIL', 'video', 'no rendered video found', 'run render.mjs --final then sound.py all')
else:
    pj = ffprobe(video); vs = [s for s in pj['streams'] if s['codec_type'] == 'video']; au = [s for s in pj['streams'] if s['codec_type'] == 'audio']
    vdur = float(pj['format']['duration'])
    final = os.path.basename(video) == 'final.mp4'
    if vs:
        v0 = vs[0]; ok = v0['codec_name'] == 'h264' and v0.get('pix_fmt') == 'yuv420p' and (not final or (v0['width'], v0['height']) == (1920, 1080))
        out('PASS' if ok else 'FAIL', 'video', f"{os.path.basename(video)}: {v0['codec_name']} {v0['width']}x{v0['height']} {v0.get('pix_fmt')} {v0['r_frame_rate']} {vdur:.1f}s")
    out('PASS' if au else 'FAIL', 'audio', f"{len(au)} audio stream(s)" + (f", {au[0]['codec_name']} {au[0].get('sample_rate')}Hz" if au else ''), '' if au else 'run sound.py <film> all to mix and mux')
    if abs(vdur - dur) > 0.6: out('WARN', 'video', f"video {vdur:.1f}s vs timeline {dur:.1f}s")
    # motion analysis at 4 fps, 160x90 grey
    fps = 4; W, H = 160, 90
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', video, '-vf', f'fps={fps},scale={W}:{H},format=gray', '-f', 'rawvideo', '-'], capture_output=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.float32)
    if len(fr) > 2:
        diff = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))
        luma = fr.mean(axis=(1, 2)) / 255
        def shot_at(t): return next((s for s in shots if s['start'] <= t < s['end']), shots[-1])
        dead, cur = [], None
        for i, d in enumerate(diff):
            t = (i + 1) / fps; s = shot_at(t)
            quiet = d < 0.35 and not s.get('hold') and not s.get('silence')
            if quiet and cur is None: cur = t
            if (not quiet or i == len(diff) - 1) and cur is not None:
                if t - cur >= 4.0: dead.append((cur, t))
                cur = None
        out('PASS' if not dead else 'WARN', 'motion', 'no still stretches over 4s' if not dead else 'near-still stretches: ' + ', '.join(f"{mmss(a)}–{mmss(b)} ({shot_at(a)['id']})" for a, b in dead[:6]), '' if not dead else 'add life: a blink/breath is not enough — move the camera, add a gesture, particles or a cut')
        blacks, cur = [], None
        for i, l in enumerate(luma):
            t = i / fps
            if l < 0.05 and cur is None: cur = t
            if (l >= 0.05 or i == len(luma) - 1) and cur is not None:
                if t - cur > 0.75 and cur > 1.5 and t < dur - 2.5: blacks.append((cur, t))
                cur = None
        if blacks: out('WARN', 'picture', 'black stretches: ' + ', '.join(f"{mmss(a)}–{mmss(b)}" for a, b in blacks[:5]), 'intended dips are fine; otherwise a shot is missing light or failed to draw')
        dark = [s for s in shots if luma[int(min(len(luma) - 1, (s['start'] + s['dur'] / 2) * fps))] < 0.11]
        if dark: out('WARN', 'picture', 'very dark shots (hard to read on phones): ' + ', '.join(s['id'] for s in dark[:6]), 'raise the light on the subject: rim, lamp glow, window light')
    # contact sheets & phone strip
    every = float(arg('--every', 4))
    for f in os.listdir(R):
        if f.startswith('contact_') or f.startswith('phone_'): os.remove(os.path.join(R, f))
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', video, '-vf', f"fps=1/{every},scale=384:216,drawtext=text='%{{pts\\:hms}}':x=6:y=6:fontsize=16:fontcolor=white:box=1:boxcolor=black@0.5,tile=5x6:padding=6:color=0x16181c", os.path.join(R, 'contact_%02d.jpg')], check=False)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', video, '-vf', 'fps=1/2,scale=180:-2,tile=12x8:padding=2', '-frames:v', '1', os.path.join(R, 'phone_01.jpg')], check=False)

# ---------------- sound ----------------
mixp = os.path.join(B, 'audio', 'mix.wav')
if os.path.exists(mixp):
    sys.path.insert(0, os.path.dirname(__file__))
    import sound
    with wave.open(mixp) as wf:
        x = np.frombuffer(wf.readframes(wf.getnframes()), '<i2').reshape(-1, 2).astype(np.float32) / 32768
    L = sound.lufs(x); tp = sound.true_peak(x)
    out('PASS' if -15.5 <= L <= -12.5 else 'WARN', 'loudness', f"{L:.1f} LUFS integrated (YouTube plays at about -14)")
    out('PASS' if tp <= -0.9 else 'FAIL', 'peaks', f"true peak {tp:.1f} dBTP", '' if tp <= -0.9 else 'rerun sound.py mix')
    # short-term loudness curve (3s windows, 0.5s hop)
    SR = 48000; win, hop = SR, SR // 4
    st = []
    for i in range(0, max(1, len(x) - win), hop):
        st.append(sound.lufs(x[i:i + win]) if i + win <= len(x) else -70)
    st = np.array(st); tt = np.arange(len(st)) * 0.25 + 0.5
    gaps = []
    rms = np.sqrt((x ** 2).mean(1))
    blk = SR // 4; nb = len(rms) // blk; rb = 20 * np.log10(rms[: nb * blk].reshape(nb, blk).mean(1) + 1e-9)
    cur = None
    for i, r in enumerate(rb):
        t = i / 4; s = next((q for q in shots if q['start'] <= t < q['end']), shots[-1])
        q = r < -50 and not s.get('silence') and 1.0 < t < dur - 3
        if q and cur is None: cur = t
        if (not q or i == len(rb) - 1) and cur is not None:
            if t - cur > 2.0: gaps.append((cur, t))
            cur = None
    out('PASS' if not gaps else 'WARN', 'sound', 'no unintended silence' if not gaps else 'dead air: ' + ', '.join(f"{mmss(a)}–{mmss(b)}" for a, b in gaps[:5]), '' if not gaps else 'keep an ambience bed under every shot')
    hits = [s for s in shots if s.get('hit')]
    for h in hits:
        def lv(a, b):
            i0, i1 = int(max(0, a) * SR), int(min(dur, b) * SR)
            seg = x[i0:i1]; return 20 * np.log10(np.sqrt((seg ** 2).mean()) + 1e-9) if len(seg) else -90
        before, after = lv(h['start'] - 2.0, h['start'] - 0.2), lv(h['start'], h['start'] + 2.0)
        ok = after - before >= 8
        out('PASS' if ok else 'WARN', 'payoff', f"hit at {mmss(h['start'])} ({h['id']}): {after - before:+.1f} dB vs the 2s before", '' if ok else 'flag the shot before as music.silence so the hit lands out of quiet')
    if not hits: out('WARN', 'payoff', 'no shot has music.hit — the turn/payoff has no musical landing', 'mark the payoff shot music:{hit:true} and the beat before it music:{silence:true}')
    try:
        import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(16, 4.2), dpi=100)
        ax.plot(tt, st, color="#2b6cb0", lw=1.2, label="1s loudness (LUFS)")
        for c in chs: ax.axvline(c['start'], color='#888', ls='--', lw=0.8); ax.text(c['start'] + 0.5, max(st.max(), -20) + 1.5, c['title'], fontsize=8, color='#444')
        for s in shots:
            if s.get('silence'): ax.axvspan(s['start'], s['end'], color='#cbd5e1', alpha=0.6)
            if s.get('hit'): ax.axvline(s['start'], color='#c53030', lw=2); ax.text(s['start'] + 0.3, st.min() + 1, 'HIT', color='#c53030', fontsize=8)
        for c in caps: ax.plot([c['t0'], c['t1']], [st.min() - 1, st.min() - 1], color='#d69e2e', lw=3)
        ax.set_xlim(0, dur); ax.set_ylim(st.min() - 3, max(st.max(), -20) + 4); ax.set_xlabel('seconds'); ax.grid(alpha=0.25)
        ax.set_title('audio arc — chapters (dashed), silence beats (grey), hits (red), captions (gold)')
        fig.tight_layout(); fig.savefig(os.path.join(R, 'audio_arc.png')); plt.close(fig)
    except Exception as e:
        out('WARN', 'sound', f'could not draw audio_arc.png: {e}')
else: out('FAIL', 'sound', 'no build/audio/mix.wav', 'run sound.py <film> all')

rep = f"# QA — {info['title']}\n\nvideo: {video}\n\n```\n" + '\n'.join(lines) + f"\n```\n\n{fails} fail, {warns} warn\n\nLook at: review/contact_*.jpg (story reads at a glance?), review/phone_01.jpg (readable small?), review/audio_arc.png (silence before the hit, music follows the chapters?)\n"
open(os.path.join(R, 'qa_report.md'), 'w').write(rep)
print('\n'.join(lines)); print(f"\n{fails} fail, {warns} warn  ->  {os.path.join(R, 'qa_report.md')}")
sys.exit(1 if fails else 0)
