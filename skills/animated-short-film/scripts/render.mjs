#!/usr/bin/env node
/*
  render.mjs — renders a film project with headless Chromium + ffmpeg.

  node render.mjs <filmDir> [mode] [options]
    modes (pick one; default --preview):
      --timeline          write build/film.json only (fast)
      --board             storyboard: every shot's key frame on numbered sheets -> build/board/*.png
      --stills a,b,...    PNG stills at seconds or shot:<id>@<sec> -> build/stills/
      --preview           960x540 @15fps draft video -> build/preview.mp4
      --final             1920x1080 @film fps master -> build/video.mp4 (no audio)
      --sheet [sec]       contact sheet of the film every N s (default 3) -> build/review/sheet_*.png
      --thumb             YouTube thumbnail from film.thumbnail -> build/thumbnail.png
      --eval "js"           print the value of a JS expression inside the film page (debugging), e.g.
                          --eval "SF.debugActor('shot-id','actor',1.5)"
      --cast              model sheet per cast member (turnaround, poses, expressions) -> build/cast/*.png
    options:
      --shots 3-9 | id,id  limit to shots (preview/final/board)
      --jobs N            parallel browser pages (default: min(2, cpus))
      --size WxH --fps N  override output size / fps
      --quality 0.92      JPEG quality of the frame transport
  Segments are cached per shot (build/segments/...), keyed on the shot's code, its source file, the film's
  shared files and the engine — re-rendering after an edit only redoes the shots that changed.
*/
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
import { spawn, execSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const SKILL = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(import.meta.url);
const ENGINE = ['core', 'paint', 'rig', 'acting', 'props', 'sets', 'fx', 'film'];

// ---------- args ----------
const argv = process.argv.slice(2);
if (!argv.length || argv[0].startsWith('--')) { console.error('usage: node render.mjs <filmDir> [--board|--preview|--final|--stills ...|--sheet N|--thumb|--timeline] [--shots a-b]'); process.exit(2); }
const FILM_DIR = path.resolve(argv[0]);
const opt = (k, d) => { const i = argv.indexOf(k); return i < 0 ? d : argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[i + 1] : true; };
const has = (k) => argv.includes(k);
const MODE = ['--eval', '--timeline', '--cast', '--board', '--stills', '--final', '--sheet', '--thumb', '--preview'].find(has) || '--preview';
const BUILD = path.join(FILM_DIR, 'build');
fs.mkdirSync(BUILD, { recursive: true });
const QUALITY = +opt('--quality', 0.92);

// ---------- playwright ----------
function loadPlaywright() {
  const tries = [() => require('playwright'), () => require(path.join(execSync('npm root -g').toString().trim(), 'playwright')), () => require('playwright-core')];
  for (const t of tries) { try { return t(); } catch { /* next */ } }
  console.error('Playwright is not installed. Install it with:  npm i -g playwright && npx playwright install chromium');
  process.exit(3);
}
const { chromium } = loadPlaywright();

// ---------- files ----------
const listJs = (dir) => (fs.existsSync(dir) ? fs.readdirSync(dir).filter((f) => f.endsWith('.js')).sort().map((f) => path.join(dir, f)) : []);
if (!fs.existsSync(path.join(FILM_DIR, 'film.js'))) { console.error('No film.js in ' + FILM_DIR + ' (start from templates/film)'); process.exit(2); }
const libFiles = listJs(path.join(FILM_DIR, 'lib'));
const shotFiles = listJs(path.join(FILM_DIR, 'shots'));
const filmScripts = [...libFiles, path.join(FILM_DIR, 'film.js'), ...shotFiles].map((f) => '/film/' + path.relative(FILM_DIR, f).split(path.sep).join('/'));
const sha = (s) => crypto.createHash('sha1').update(s).digest('hex').slice(0, 10);
const fileHash = (p) => sha(fs.readFileSync(p));
const globalHash = sha([...ENGINE.map((e) => fileHash(path.join(SKILL, 'engine', e + '.js'))), ...libFiles.map(fileHash), fileHash(path.join(FILM_DIR, 'film.js'))].join(':'));

// ---------- server ----------
const MIME = { '.js': 'text/javascript', '.html': 'text/html', '.ttf': 'font/ttf', '.otf': 'font/otf', '.woff2': 'font/woff2', '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml', '.json': 'application/json' };
function pageHtml(w, h) {
  return `<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{font-family:"Fredoka";src:url("/assets/fonts/Fredoka.ttf") format("truetype");font-weight:300 700;font-stretch:75% 125%;}
html,body{margin:0;background:#111}canvas{display:block}</style></head><body>
<canvas id="c" width="${w}" height="${h}"></canvas>
<script>window.SF_ERRORS=[];window.addEventListener('error',e=>SF_ERRORS.push(String(e.message)+' @ '+(e.filename||'').replace(location.origin,'')+':'+e.lineno));</script>
${ENGINE.map((e) => `<script src="/engine/${e}.js"></script>`).join('\n')}
${filmScripts.map((s) => `<script src="${s}"></script>`).join('\n')}
<script>
(async()=>{try{await document.fonts.load('600 40px Fredoka');await document.fonts.load('600 40px Inter');}catch(e){}
 try{SF.prepare();}catch(e){SF_ERRORS.push('prepare: '+e.message);} window.SF_READY=true;})();
window.grab=(f,q,type)=>{const c=document.getElementById('c');const g=c.getContext('2d');g.setTransform(1,0,0,1,0,0);SF.renderFrame(g,f);return c.toDataURL(type||'image/jpeg',q);};
</script></body></html>`;
}
function serve() {
  return new Promise((res) => {
    const srv = http.createServer((req, rsp) => {
      const u = decodeURIComponent(new URL(req.url, 'http://x').pathname);
      if (u.startsWith('/page.html')) { const q = new URL(req.url, 'http://x').searchParams; rsp.writeHead(200, { 'content-type': 'text/html' }); return rsp.end(pageHtml(+q.get('w') || 1920, +q.get('h') || 1080)); }
      let file = null;
      if (u.startsWith('/engine/') || u.startsWith('/assets/')) file = path.join(SKILL, u);
      else if (u.startsWith('/film/')) file = path.join(FILM_DIR, u.slice(6));
      if (!file || !fs.existsSync(file)) { rsp.writeHead(404); return rsp.end('not found'); }
      rsp.writeHead(200, { 'content-type': MIME[path.extname(file)] || 'application/octet-stream', 'cache-control': 'no-store' });
      fs.createReadStream(file).pipe(rsp);
    });
    srv.listen(0, '127.0.0.1', () => res(srv));
  });
}

async function openPage(browser, port, w, h) {
  const page = await browser.newPage({ viewport: { width: Math.min(w, 1920), height: Math.min(h, 1080) } });
  const logs = [];
  page.on('console', (m) => { if (m.type() === 'error') logs.push(m.text()); });
  page.on('pageerror', (e) => logs.push(String(e.message)));
  await page.goto(`http://127.0.0.1:${port}/page.html?w=${w}&h=${h}`);
  await page.waitForFunction(() => window.SF_READY === true, null, { timeout: 60000 });
  const errs = await page.evaluate(() => window.SF_ERRORS);
  if (errs.length || logs.length) { console.error('Film failed to load:\n  ' + [...errs, ...logs].join('\n  ')); process.exit(1); }
  return page;
}

// ---------- ffmpeg ----------
function ffmpegWriter(out, fps, crf, preset) {
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-', '-c:v', 'libx264', '-preset', preset, '-crf', String(crf), '-pix_fmt', 'yuv420p', '-r', String(fps), out], { stdio: ['pipe', 'inherit', 'inherit'] });
  const done = new Promise((res, rej) => ff.on('close', (c) => (c === 0 ? res() : rej(new Error('ffmpeg exited ' + c)))));
  return {
    write: (buf) => new Promise((res) => { if (ff.stdin.write(buf)) res(); else ff.stdin.once('drain', res); }),
    end: async () => { ff.stdin.end(); await done; },
  };
}
const b64 = (d) => Buffer.from(d.slice(d.indexOf(',') + 1), 'base64');

function parseShots(spec, info) {
  if (!spec || spec === true) return info.shots.map((s) => s.index);
  const out = new Set();
  for (const part of String(spec).split(',')) {
    const m = part.match(/^(\d+)-(\d+)$/);
    if (m) for (let i = +m[1]; i <= +m[2]; i++) out.add(i - 1);
    else if (/^\d+$/.test(part)) out.add(+part - 1);
    else { const s = info.shots.find((x) => x.id === part); if (s) out.add(s.index); else console.warn('unknown shot ' + part); }
  }
  return [...out].filter((i) => i >= 0 && i < info.shots.length).sort((a, b) => a - b);
}

async function main() {
  const t0 = Date.now();
  const srv = await serve(); const port = srv.address().port;
  const browser = await chromium.launch({ headless: true, args: ['--disable-gpu-vsync', '--force-color-profile=srgb'] });
  const finalMode = MODE === '--final';
  let [W, H] = finalMode || MODE === '--cast' ? [1920, 1080] : MODE === '--thumb' ? [1280, 720] : [960, 540];
  if (opt('--size')) [W, H] = String(opt('--size')).split('x').map(Number);
  const page = await openPage(browser, port, W, H);
  const info = await page.evaluate(() => SF.timeline());
  fs.writeFileSync(path.join(BUILD, 'film.json'), JSON.stringify(info, null, 1));
  const report = { mode: MODE, warnings: info.warnings, shots: info.shots.length, duration: info.duration };
  console.log(`film: "${info.title}" ${info.shots.length} shots, ${info.duration.toFixed(1)}s, ${info.chapters.length} chapters`);
  if (info.warnings.length) console.log('warnings:\n  ' + info.warnings.map((w) => w.kind + ': ' + w.msg).join('\n  '));

  if (MODE === '--timeline') { await finish(); return; }
  if (MODE === '--eval') { // debugging aid: evaluate an expression in the film page, e.g. --eval "SF.debugActor('rain','kid',2)"
    const res = await page.evaluate((expr) => { try { return JSON.stringify(eval(expr), null, 1); } catch (e) { return 'ERROR ' + e.message; } }, String(opt('--eval')));
    console.log(res); await finish(); return;
  }

  if (MODE === '--cast') {
    const dir = path.join(BUILD, 'cast'); fs.mkdirSync(dir, { recursive: true });
    const ids = await page.evaluate(() => Object.keys(SF.FILM.cast));
    for (const id of ids) {
      const d = await page.evaluate(([id]) => { const c = document.getElementById('c'); const g = c.getContext('2d'); g.setTransform(1, 0, 0, 1, 0, 0); SF.castSheet(g, id); return c.toDataURL('image/png'); }, [id]);
      const out = path.join(dir, `${id}.png`); fs.writeFileSync(out, b64(d)); console.log('wrote ' + out);
    }
    await finish(); return;
  }

  if (MODE === '--stills') {
    const dir = path.join(BUILD, 'stills'); fs.mkdirSync(dir, { recursive: true });
    for (const s of String(opt('--stills')).split(',')) {
      let f;
      const m = s.match(/^shot:([^@]+)@([\d.]+)$/);
      if (m) { const sh = info.shots.find((x) => x.id === m[1] || String(x.index + 1) === m[1]); if (!sh) { console.warn('no shot ' + m[1]); continue; } f = sh.f0 + Math.round(+m[2] * info.fps); }
      else f = Math.round(+s * info.fps);
      const d = await page.evaluate(([f]) => grab(f, 1, 'image/png'), [f]);
      const out = path.join(dir, `still_${String(f).padStart(5, '0')}.png`); fs.writeFileSync(out, b64(d)); console.log('wrote ' + out);
    }
    await finish(); return;
  }

  if (MODE === '--board' || MODE === '--sheet') {
    const isBoard = MODE === '--board';
    const dir = path.join(BUILD, isBoard ? 'board' : 'review'); fs.mkdirSync(dir, { recursive: true });
    for (const f of fs.readdirSync(dir)) if (f.endsWith('.png')) fs.unlinkSync(path.join(dir, f));
    let items;
    if (isBoard) items = parseShots(opt('--shots'), info).map((i) => { const s = info.shots[i]; const cap = info.captions.filter((c) => c.shot === s.id).map((c) => '“' + c.text + '”').join(' '); return { f: s.f0 + Math.min(s.f1 - s.f0 - 1, Math.round(s.key * info.fps)), label: `#${i + 1}  ${s.id}  ·  ch${s.ch}  ·  ${s.dur.toFixed(1)}s${s.trans !== 'cut' ? '  ·  ' + s.trans : ''}`, sub: (s.beat || '') + (cap ? '  ' + cap : '') }; });
    else { const step = +(opt('--sheet') === true ? 3 : opt('--sheet')); items = []; for (let t = 0.5; t < info.duration; t += step) { const f = Math.round(t * info.fps); const s = info.shots.find((x) => f >= x.f0 && f < x.f1); items.push({ f, label: `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, '0')}  #${s.index + 1} ${s.id}`, sub: '' }); } }
    const cols = isBoard ? 4 : 5, rows = isBoard ? 4 : 6, per = cols * rows;
    for (let p = 0; p * per < items.length; p++) {
      const chunk = items.slice(p * per, (p + 1) * per);
      const png = await page.evaluate(([chunk, cols, isBoard, title, pn]) => {
        const pw = isBoard ? 480 : 384, ph = isBoard ? 270 : 216, lab = isBoard ? 70 : 34, gap = 14, head = 70;
        const rows = Math.ceil(chunk.length / cols);
        const sheet = document.createElement('canvas'); sheet.width = cols * pw + (cols + 1) * gap; sheet.height = head + rows * (ph + lab) + (rows + 1) * gap;
        const x = sheet.getContext('2d'); x.fillStyle = '#16181c'; x.fillRect(0, 0, sheet.width, sheet.height);
        x.fillStyle = '#e9e9e4'; x.font = '700 30px Inter, sans-serif'; x.fillText((isBoard ? 'STORYBOARD — ' : 'CONTACT SHEET — ') + title + '  (page ' + pn + ')', gap, 46);
        const c = document.getElementById('c'); const g = c.getContext('2d');
        chunk.forEach((it, i) => {
          g.setTransform(1, 0, 0, 1, 0, 0); SF.renderFrame(g, it.f);
          const cx = gap + (i % cols) * (pw + gap), cy = head + gap + Math.floor(i / cols) * (ph + lab + gap);
          x.drawImage(c, cx, cy, pw, ph);
          x.fillStyle = '#f2f1ec'; x.font = '700 17px Inter, sans-serif'; x.fillText(it.label, cx, cy + ph + 22);
          if (it.sub) { x.fillStyle = '#a9adb5'; x.font = '500 14px Inter, sans-serif'; const words = it.sub.split(' '); let line = '', ly = cy + ph + 42; for (const w of words) { const t = line ? line + ' ' + w : w; if (x.measureText(t).width > pw && line) { x.fillText(line, cx, ly); line = w; ly += 17; if (ly > cy + ph + lab - 2) { line = ''; break; } } else line = t; } if (line) x.fillText(line, cx, ly); }
        });
        return sheet.toDataURL('image/png');
      }, [chunk, cols, isBoard, info.title, p + 1]);
      const out = path.join(dir, `${isBoard ? 'board' : 'sheet'}_${String(p + 1).padStart(2, '0')}.png`); fs.writeFileSync(out, b64(png)); console.log('wrote ' + out);
    }
    await finish(); return;
  }

  if (MODE === '--thumb') {
    const th = info.thumbnail || {};
    const sh = info.shots.find((x) => x.id === th.shot) || info.shots[Math.floor(info.shots.length * 0.7)];
    const f = sh.f0 + Math.round((th.t === undefined ? sh.key : th.t) * info.fps);
    const d = await page.evaluate(([f]) => { const c = document.getElementById('c'); const g = c.getContext('2d'); g.setTransform(1, 0, 0, 1, 0, 0); SF.renderFrame(g, f, { noCaptions: true }); const T = SF.FILM.cfg.thumbnail || {}; if (T.draw) { g.save(); g.setTransform(c.width / 1920, 0, 0, c.width / 1920, 0, 0); T.draw(g, SF); g.restore(); } else if (T.text) { g.save(); g.setTransform(c.width / 1920, 0, 0, c.width / 1920, 0, 0); SF.paint.text(g, T.text, T.x || 1380, T.y || 300, { size: T.size || 190, weight: 800, font: SF.FONTS.ui, color: T.color || '#ffffff', stroke: '#0c0d10', sw: 26, maxW: 1000 }); g.restore(); } return c.toDataURL('image/png'); }, [f]);
    fs.writeFileSync(path.join(BUILD, 'thumbnail.png'), b64(d)); console.log('wrote ' + path.join(BUILD, 'thumbnail.png'));
    await finish(); return;
  }

  // ---------- video (preview / final) ----------
  const fps = +(opt('--fps') || (finalMode ? info.fps : 15));
  const crf = finalMode ? 18 : 24, preset = finalMode ? 'superfast' : 'ultrafast';
  const tag = `${W}x${H}_${fps}`;
  const segDir = path.join(BUILD, 'segments', tag); fs.mkdirSync(segDir, { recursive: true });
  const wanted = parseShots(opt('--shots'), info);
  const hashes = await page.evaluate((n) => Array.from({ length: n }, (_, i) => SF.shotHash(i)), info.shots.length);
  const srcHash = {}; for (const s of shotFiles) srcHash['/film/' + path.relative(FILM_DIR, s).split(path.sep).join('/')] = fileHash(s);
  const shotSrc = await page.evaluate(() => SF.FILM.shots.map((s) => s.src || ''));
  const jobs = [];
  for (const i of wanted) {
    const s = info.shots[i];
    const key = sha([globalHash, hashes[i], srcHash[shotSrc[i]] || '', (i > 0 && s.trans === 'cross') ? hashes[i - 1] : ''].join('|'));
    const file = path.join(segDir, `${String(i + 1).padStart(3, '0')}_${s.id.replace(/[^\w-]/g, '_')}_${key}.mp4`);
    for (const old of fs.readdirSync(segDir)) if (old.startsWith(String(i + 1).padStart(3, '0') + '_') && path.join(segDir, old) !== file) fs.unlinkSync(path.join(segDir, old));
    if (!fs.existsSync(file)) jobs.push({ i, file, s });
  }
  console.log(`${tag}: ${wanted.length} shots, ${jobs.length} to render (${wanted.length - jobs.length} cached)`);
  const nJobs = Math.max(1, Math.min(+(opt('--jobs') || Math.min(2, os.cpus().length)), jobs.length || 1));
  // one browser per job: pages of one browser share a single renderer process, so only separate browsers render in parallel
  const extra = [];
  const pages = [page]; for (let k = 1; k < nJobs; k++) { const b = await chromium.launch({ headless: true, args: ['--disable-gpu-vsync', '--force-color-profile=srgb'] }); extra.push(b); pages.push(await openPage(b, port, W, H)); }
  let next = 0, framesDone = 0;
  const totalFrames = jobs.reduce((a, j) => a + Math.round(j.s.dur * fps), 0);
  const tStart = Date.now();
  async function worker(pg) {
    while (next < jobs.length) {
      const j = jobs[next++];
      const n = Math.round(j.s.dur * fps);
      const tmp = j.file + '.part.mp4';
      const wr = ffmpegWriter(tmp, fps, crf, preset);
      for (let k = 0; k < n; k += 6) {
        const frames = await pg.evaluate(([a, b, start, fps, filmFps, q]) => { const out = []; for (let k = a; k < b; k++) out.push(grab(Math.round(start + (k / fps) * filmFps), q)); return out; }, [k, Math.min(n, k + 6), j.s.f0, fps, info.fps, QUALITY]);
        for (const d of frames) await wr.write(b64(d));
        framesDone += frames.length;
      }
      await wr.end();
      fs.renameSync(tmp, j.file);
      const el = (Date.now() - tStart) / 1000;
      console.log(`  shot ${j.i + 1}/${info.shots.length} ${j.s.id} (${n}f)  ${framesDone}/${totalFrames} frames, ${(framesDone / el).toFixed(1)} fps`);
    }
  }
  await Promise.all(pages.map(worker));
  for (const b of extra) await b.close();
  const list = path.join(segDir, 'concat.txt');
  const segs = wanted.map((i) => fs.readdirSync(segDir).find((f) => f.startsWith(String(i + 1).padStart(3, '0') + '_') && f.endsWith('.mp4') && !f.includes('.part'))).filter(Boolean);
  fs.writeFileSync(list, segs.map((f) => `file '${path.join(segDir, f)}'`).join('\n'));
  const outName = finalMode ? (wanted.length === info.shots.length ? 'video.mp4' : 'video_partial.mp4') : (wanted.length === info.shots.length ? 'preview.mp4' : 'preview_partial.mp4');
  execSync(`ffmpeg -y -loglevel error -f concat -safe 0 -i "${list}" -c copy -movflags +faststart "${path.join(BUILD, outName)}"`);
  console.log('wrote ' + path.join(BUILD, outName));
  report.rendered = jobs.length; report.output = outName;
  await finish();

  async function finish() {
    const log = await page.evaluate(() => ({ warnings: SF.log.warnings, violations: SF.log.violations.slice(0, 300), violationCount: SF.log.violations.length }));
    Object.assign(report, log, { seconds: +((Date.now() - t0) / 1000).toFixed(1) });
    fs.writeFileSync(path.join(BUILD, 'render_log.json'), JSON.stringify(report, null, 1));
    if (log.violationCount) console.log(`joint-limit clamps: ${log.violationCount} (see build/render_log.json) — fix the poses that cause them`);
    await browser.close(); srv.close();
    console.log(`done in ${report.seconds}s`);
  }
}
main().catch((e) => { console.error(e); process.exit(1); });
