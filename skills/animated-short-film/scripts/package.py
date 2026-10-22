#!/usr/bin/env python3
"""
package.py — assemble the upload package from the film: output/<slug>/ with
  final.mp4, thumbnail.png, description.txt, chapters.txt, captions.srt, metadata.json, pinned_comment.txt, upload_checklist.md

  python3 package.py <filmDir> [--out <dir>]

Text comes from the film's SF.film({ package: {...} }) block, written during the story step:
  package: { title, titles:[alternatives], hook, summary, question, hashtags:[...], tags:[...], pinned, language:'en' }
Chapters come from the timeline, so they always match the cut. The script validates YouTube's limits and prints problems.
"""
import json, os, re, shutil, subprocess, sys

FILM = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else sys.exit(__doc__)
B = os.path.join(FILM, 'build')
info = json.load(open(os.path.join(B, 'film.json')))
pk = info.get('package') or {}
title = pk.get('title') or f"{info['title']} | An Animated Short Film"
slug = re.sub(r'[^a-z0-9]+', '-', info['title'].lower()).strip('-') or 'film'
OUT = os.path.abspath(sys.argv[sys.argv.index('--out') + 1]) if '--out' in sys.argv else os.path.join(FILM, 'output')
os.makedirs(OUT, exist_ok=True)
problems = []
def mmss(t): t = int(round(t)); return f"{t // 60}:{t % 60:02d}"

# chapters (YouTube: first 0:00, >=3 chapters, each >=10s)
chs = info['chapters']
chap_lines = [f"{mmss(c['start'] if i else 0)} {c['title']}" for i, c in enumerate(chs)]
if len(chs) < 3: problems.append('fewer than 3 chapters: YouTube will not show chapters')
if any(c['end'] - c['start'] < 10 for c in chs): problems.append('a chapter is shorter than 10s: YouTube will drop chapters')

tags = [t.strip() for t in pk.get('tags', []) if t.strip()]
hashtags = ['#' + h.lstrip('#') for h in pk.get('hashtags', ['AnimatedShortFilm', '2DAnimation', 'ShortFilm'])]
desc = []
if pk.get('hook'): desc.append(pk['hook'].strip())
if pk.get('summary'): desc.append(pk['summary'].strip())
if pk.get('question'): desc.append('💬 ' + pk['question'].strip())
desc.append('Chapters:\n' + '\n'.join(chap_lines))
if pk.get('credits'): desc.append(pk['credits'].strip())
desc.append(' '.join(hashtags[:15]))
description = '\n\n'.join(desc)

if len(title) > 100: problems.append(f'title is {len(title)} chars (max 100)')
elif len(title) > 70: problems.append(f'title is {len(title)} chars — it truncates on phones after ~70')
if '<' in description or '>' in description: problems.append('description contains < or > (YouTube rejects them)')
if len(description) > 5000: problems.append('description over 5000 chars')
if sum(len(t) + 1 for t in tags) > 500: problems.append('tags exceed 500 characters')
if len(hashtags) > 15: problems.append('more than 15 hashtags: YouTube ignores all of them')
if not pk.get('hook'): problems.append('no package.hook — the first 2 lines of the description show under the video; write a hook')

# SRT captions from the timeline (dialogue lines)
def ts(t):
    h, rem = divmod(t, 3600); m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}"
srt = '\n'.join(f"{i + 1}\n{ts(c['t0'])} --> {ts(c['t1'])}\n{c['text']}\n" for i, c in enumerate(info['captions']))
open(os.path.join(OUT, 'captions.srt'), 'w').write(srt)
open(os.path.join(OUT, 'description.txt'), 'w').write(description + '\n')
open(os.path.join(OUT, 'chapters.txt'), 'w').write('\n'.join(chap_lines) + '\n')
open(os.path.join(OUT, 'pinned_comment.txt'), 'w').write((pk.get('pinned') or pk.get('question') or '').strip() + '\n')
meta = dict(title=title, alt_titles=pk.get('titles', []), description=description, tags=tags, hashtags=hashtags, chapters=chap_lines,
            category='Film & Animation', made_for_kids=False, language=pk.get('language', 'en'), duration=info['duration'],
            altered_or_synthetic_content='Animation made with code; disclose per YouTube policy if any realistic AI voice/footage is added.')
json.dump(meta, open(os.path.join(OUT, 'metadata.json'), 'w'), indent=1, ensure_ascii=False)

for src, dst in (('final.mp4', 'final.mp4'), ('thumbnail.png', 'thumbnail.png')):
    p = os.path.join(B, src)
    if os.path.exists(p): shutil.copy(p, os.path.join(OUT, dst))
    else: problems.append(f'missing build/{src} ' + ('(render.mjs --final then sound.py all)' if src == 'final.mp4' else '(render.mjs --thumb)'))
if os.path.exists(os.path.join(OUT, 'thumbnail.png')):
    try:
        from PIL import Image
        im = Image.open(os.path.join(OUT, 'thumbnail.png'))
        if im.size != (1280, 720): problems.append(f'thumbnail is {im.size}, YouTube wants 1280x720')
        if os.path.getsize(os.path.join(OUT, 'thumbnail.png')) > 2_000_000:
            im.convert('RGB').save(os.path.join(OUT, 'thumbnail.jpg'), quality=90); os.remove(os.path.join(OUT, 'thumbnail.png'))
    except Exception as e: problems.append(f'could not inspect thumbnail: {e}')

checklist = f"""# Upload checklist — {title}

- [ ] Watch final.mp4 once start to end with sound (the QA report measures it, but nobody has *listened* yet)
- [ ] Title: {title}
- [ ] Thumbnail: thumbnail.png (readable at 160px wide? one face, one object, <=3 words)
- [ ] Description: paste description.txt (first two lines are the hook)
- [ ] Chapters are already in the description ({len(chs)} chapters)
- [ ] Upload captions.srt as English subtitles (helps search and silent viewers)
- [ ] Category: Film & Animation · Not made for kids · Language: {meta['language']}
- [ ] Altered/synthetic content: only needed if realistic AI voice/footage was added
- [ ] Pin pinned_comment.txt, reply to early comments in the first hour
- [ ] Note publish time; check retention at 30s and the chapter-2 drop after 48h
"""
open(os.path.join(OUT, 'upload_checklist.md'), 'w').write(checklist)
print(f"package -> {OUT}")
print(f"title: {title}  ({len(title)} chars)")
for p in problems: print('  ! ' + p)
if not problems: print('  all YouTube limits OK')
