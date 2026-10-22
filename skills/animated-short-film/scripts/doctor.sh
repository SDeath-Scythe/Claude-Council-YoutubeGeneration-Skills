#!/usr/bin/env bash
# doctor.sh — check everything the film pipeline needs; prints what to install if something is missing.
ok=1
say() { printf '%-10s %s\n' "$1" "$2"; }
command -v node >/dev/null && say node "$(node --version)" || { say node "MISSING — install Node 18+"; ok=0; }
command -v ffmpeg >/dev/null && say ffmpeg "$(ffmpeg -version | head -1 | cut -d' ' -f3)" || { say ffmpeg "MISSING — install ffmpeg (with libx264)"; ok=0; }
ffmpeg -hide_banner -encoders 2>/dev/null | grep -q libx264 || { say x264 "MISSING — ffmpeg build lacks libx264"; ok=0; }
command -v python3 >/dev/null && say python3 "$(python3 --version | cut -d' ' -f2)" || { say python3 "MISSING"; ok=0; }
python3 - <<'EOF' || ok=0
import importlib, sys
need = {'numpy': True, 'scipy': True, 'PIL': False, 'matplotlib': False}
bad = False
for m, req in need.items():
    try: importlib.import_module(m); print(f"{m:10} ok")
    except Exception: print(f"{m:10} {'MISSING — pip install ' + ('pillow' if m == 'PIL' else m) if req else 'missing (optional: contact sheets/charts degrade)'}"); bad = bad or req
sys.exit(1 if bad else 0)
EOF
NODE_PATH="${NODE_PATH:-$(npm root -g 2>/dev/null)}" node -e "
const p=(()=>{try{return require('playwright')}catch(e){}try{return require('playwright-core')}catch(e){}return null})();
if(!p){console.log('playwright MISSING — npm i -g playwright && npx playwright install chromium');process.exit(1)}
p.chromium.launch().then(b=>{console.log('chromium   ok ('+b.version()+')');return b.close()}).catch(e=>{console.log('chromium   MISSING — npx playwright install chromium ('+e.message.split('\n')[0]+')');process.exit(1)})
" || ok=0
fc-list 2>/dev/null | grep -qi "inter" && say fonts "Inter found (UI text)" || say fonts "Inter not found — UI text falls back to Helvetica/Arial (fine)"
[ $ok = 1 ] && echo "READY" || { echo "NOT READY — fix the lines above"; exit 1; }
