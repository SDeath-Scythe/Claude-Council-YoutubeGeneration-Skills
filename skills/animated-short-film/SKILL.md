---
name: animated-short-film
description: Make a complete 5–7 minute animated short film for YouTube in the wordless silhouette style of Last Soul / Day One Films — idea, story, characters, sets, storyboard, animation, score, sound effects, render, QA and upload package — all drawn in JavaScript, no AI video. Use for any animated short film, story video or channel episode request, even "make a video like this channel". For explainers or reels under ~90s, the animate skill fits better.
---

# Animated short film

You produce a finished, upload-ready animated short (default 5–7 min, 1080p, scored and mixed) with a code engine in this skill: a character rig with anatomical joint limits and a pose/gesture/walk library, lit flat-vector sets with depth-of-field, props and close-up inserts, a renderer (headless Chromium → ffmpeg, cached per shot), a score/SFX/mix generator, a measured QA pass and a packager. You write the story and the shots; the engine keeps every frame consistent.

`$SKILL` below = this skill's directory. Films live in the user's working directory as `films/<slug>/`.

## Requirements
Run `bash $SKILL/scripts/doctor.sh` first. It needs Node 18+, Playwright with Chromium, ffmpeg with libx264, Python 3 with numpy + scipy (Pillow + matplotlib for review sheets). If it isn't READY, tell the user the exact install line it printed and stop.

## Non-negotiables
1. **Story before pixels.** No shot code until the story sheet passes its checks (and the user approved it, when they're around). A wrong story costs a whole render.
2. **Everything through the engine.** Characters only via the cast (one consistent design, joint limits enforced every frame); environments from `SF.sets` or built from `SF.build` pieces; props from `SF.props`. Raw canvas drawing only for one-off objects inside a shot's `draw` hook.
3. **Deterministic.** No `Math.random()` / `Date` in film code — `SF.rnd`, `SF.RNG`, `SF.noise`.
4. **Measured, not eyeballed.** `qa.py` must end with 0 FAIL; look at the board, the contact sheets, the phone strip and the audio arc yourself; report the numbers.
5. **Wordless first.** The picture tells the story; dialogue is short captions (≤ ~10 lines per film).
6. **Original and licensed.** Borrow the reference channels' structure, never their stories, titles or characters. No real people, brands or commercial music.
7. **Honest about limits.** You can't hear the mix or watch it play — say what you measured and ask the user to watch/listen once.

## Working with the user
- **User present:** ask at four cheap gates — A idea (3 options), B story sheet, C cast sheet + 2 style frames, D storyboard. Use AskUserQuestion with your recommended option first; show images with SendUserFile.
- **User away** ("just make it", a scheduled run, no reply): take your recommended option, write why under **Decisions** in `story.md`, and keep going. Never stall at a gate.
- Send drafts as they appear (cast sheet, board pages, preview) so the user can redirect early.

## Workflow — make a task for each step
1. **Set up.** `bash $SKILL/scripts/doctor.sh`; `mkdir -p films && cp -r $SKILL/templates/film films/<slug>`. The template is a 35-second demo ("THE PLANT") that shows the file layout and features — replace all of it and never reuse its story. Read [references/story.md](references/story.md).
2. **Idea (Gate A).** If the user named a channel/video or wants something trend-aware, study it first ([references/research.md](references/research.md)). Generate 8–10 ideas, score them with the rubric in story.md, present the top 3 (logline, device, reframe line, title).
3. **Story sheet (Gate B).** Write `films/<slug>/story.md`: logline, trap, device, reframe line, callback, 3 titles, a 25–40 row beat table whose times sum to the target, every caption line, cast, sets and the colour script.
4. **Cast and look (Gate C).** Fill `film.js`: title, `target`, 5 chapters with mood/energy, music key/bpm/motif, cast, `package` text, thumbnail. Run `node $SKILL/scripts/render.mjs films/<slug> --cast` and look at each model sheet. Write 2–3 key shots and check them full size with `--stills shot:<id>@<sec> --size 1920x1080` against [references/look-and-sound.md](references/look-and-sound.md).
5. **Shots and storyboard (Gate D).** Read [references/engine-api.md](references/engine-api.md), then write every shot — one file per chapter (`shots/01_<name>.js` … `05_<name>.js`), ~55–80 shots for 6 minutes. Render `--board`, open every page, run the checklist below, fix, re-render.
6. **Preview and fix.** `--preview` (540p, fast) → `python3 $SKILL/scripts/sound.py films/<slug> all` (muxes onto the preview) → `python3 $SKILL/scripts/qa.py films/<slug>`. Open `build/review/contact_*.jpg`, `phone_01.jpg`, `audio_arc.png`. Fix every FAIL and each WARN you agree with; re-render (only changed shots redo).
7. **Final.** `--final` (1080p, ~10 fps on 2 cores: a 6-minute film takes ~20 min — run it in the background and write the package meanwhile), then `sound.py films/<slug> mux`, then `qa.py` until 0 FAIL.
8. **Package.** `--thumb`, then `python3 $SKILL/scripts/package.py films/<slug>` → `films/<slug>/output/` (final.mp4, thumbnail, description, chapters, captions.srt, metadata, upload checklist). Fix anything it flags.
9. **Deliver.** Send `output/final.mp4` and `thumbnail.png` and paste the title + description. Report in a few lines: length, shot count, the QA numbers, what review caught and fixed, the weakest shot, and what you couldn't verify (listening, real-time motion). Offer the next changes: beats, music track, voice, thumbnail.

## Storyboard checklist (step 5, and again on the contact sheets in step 6)
- The story reads from the board alone, sound off; each chapter's turn is visible.
- Every chapter has a wide, a close-up and an insert; never three same-scale shots in a row in one place.
- Every frame has a light source and one clear subject; nothing that matters is under ~100px.
- The device appears ≥ 4 times and visibly flips; the callback shot repeats an opening framing, changed.
- `music.silence` on the beat before the turn, `music.hit` on the turn; ≤ ~10 caption lines, each ≤ 8 words.
- Time visibly passes during the climb (calendar, light, season, a day card).
- Something new every 2–4 seconds (a cut, a move, a gesture, a prop change).
- Inserts (phone screens, notes) ≤ ~25% of shots: people carry the story, screens only punctuate it. Sitting, lying and hugging shots get one full-size still check before the rest of the scene is written.

## Commands
| command | what you get |
|---|---|
| `node $SKILL/scripts/render.mjs F --cast` | model sheet per character (turnaround, poses, expressions, joint check) |
| `node $SKILL/scripts/render.mjs F --board [--shots 12-30]` | numbered storyboard pages, one key frame per shot |
| `node $SKILL/scripts/render.mjs F --stills shot:<id>@1.5,42.0 --size 1920x1080` | full-size stills to inspect |
| `node $SKILL/scripts/render.mjs F --preview` / `--final` | 540p15 draft / 1080p master (video only) |
| `node $SKILL/scripts/render.mjs F --sheet 3` / `--thumb` / `--timeline` | contact sheet / thumbnail / just `build/film.json` |
| `node $SKILL/scripts/render.mjs F --eval "SF.debugActor('id','greg',1.2)"` | inspect an actor's position, scale, depth, pose |
| `python3 $SKILL/scripts/sound.py F all [--music file] [--voice dir]` | score + SFX + ambience + mix (−14 LUFS) + mux |
| `python3 $SKILL/scripts/qa.py F` | PASS/WARN/FAIL report + review sheets + audio arc |
| `python3 $SKILL/scripts/package.py F` | YouTube package in `F/output/` |

(F = `films/<slug>`.) Renders are cached per shot: rerunning after a crash or an edit only redoes what changed. Run anything longer than a couple of minutes in the background and keep working.

## Files
| path | what | read when |
|---|---|---|
| [references/story.md](references/story.md) | format facts, 5-chapter spine, rules, idea rubric, story sheet, shot craft, packaging | steps 1–3 |
| [references/engine-api.md](references/engine-api.md) | every film/shot/camera/cast/acting/set/prop/insert/fx/sound field | before writing shots |
| [references/look-and-sound.md](references/look-and-sound.md) | what makes it look premium; score, external music, SFX, voice, loudness targets | steps 4, 6–7 |
| [references/research.md](references/research.md) | studying a channel/trend with vidIQ and Apify (tools, costs, what to measure) | step 2 when a reference is named |
| `templates/film/` | starter film (config, 5 chapter files, story sheet) | step 1 |
| `engine/*.js` | the engine (core, paint, rig, acting, props, sets, fx, film) | when extending sets/props |
| `scripts/` | doctor, render, sound, qa, package | as above |
