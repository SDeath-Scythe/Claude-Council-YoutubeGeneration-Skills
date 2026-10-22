# Claude skills lab

Two Claude skills and the A/B tests used to check them (the same prompt run with and without each skill, in separate Claude sessions).

## Skills (`skills/`)
- **animated-short-film**: makes a 5–7 minute wordless animated short for YouTube in the Last Soul / Day One Films style. It covers the idea, story sheet, cast sheet, storyboard, a 1080p render (a JS canvas engine in headless Chromium, then ffmpeg), the procedural score, SFX and mix (−14 LUFS), a measured QA pass and the upload package. No AI video.
- **project-council**: runs a big or important project through a council of subagents with different viewpoints. Each seat writes its own proposal and test cases, the plan is debated with evidence until agreement is measured, and one builder builds it while being scored on a sealed holdout it never sees. Then comes a multi-seat review with fresh cases, verified fixes and a quality gate (`scripts/council.py`).

## A/B results so far (`ab-test/`)
**Video** (prompt: `ab-test/harness/video_prompt.txt`)
| | with skill | without skill |
|---|---|---|
| film | "Typing…" 6:16, 65 shots, 30 fps | "Later" 6:22, 24 fps |
| loudness | −13.8 LUFS (YouTube target −14) | −16.8 LUFS |
| wall time / cost | ~64 min / $12.4 | ~111 min / $16.8 |
| package | description, chapters, captions.srt, metadata, thumbnail, checklist, QA report | title/description file + thumbnail |
| look | matches the Last Soul look (grey interiors, round heads with expressions, phone inserts) | atmospheric sunset silhouettes, no faces |

The A/B exposed a defect in the with-skill film: a bench-sitting shot read as standing. That is fixed in the engine (furniture in character units, park bench seat marks, trees kept off the bench).

**Council** (prompt: `ab-test/harness/council_prompt.txt`; an Iraqi DM order parser). Scores are on hidden tests that neither run saw: A = 48 realistic cases, B = 32 harder cases, C = 600 generated cases.
| run | A | B | C | cost |
|---|---|---|---|---|
| without skill, run 1 | 98.4 | 91.9 | 99.3 | $6.3 |
| without skill, run 2 | 99.4 | 97.5 | 98.5 | $5.0 |
| council v1 | 98.0 | 96.9 | 98.0 | $40.6 |
| council v2 (sealed holdout, lighter debate) | in progress | | | |

So far, a strong single agent is already near the ceiling on a well-specified coding task. The council's measured gains were on the harder cases and on avoiding confident wrong answers, at several times the cost. v2 is meant to make the council's extra effort show up as measured generalisation.
