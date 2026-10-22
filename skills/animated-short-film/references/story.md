# Story: 5–7 minute wordless animated shorts

## What the format is (measured, Oct 2026)
- **Last Soul** (@lastsoulorigin, created Oct 4 2026): 4 uploads, ~5K subs and 340K views in 15 days. Top video "1 MINUTE | An Animated Short Film" (5:00, 342K views in 9 days). Transcripts are almost entirely `[music]`, sighs, panting — dialogue appears as on-screen captions only. Descriptions retell the setup in 2–3 sentences, list 3–5 chapters, end with a comment question and hashtags (#AnimatedShortFilm #2DAnimation #ShortFilm). Titles: "1 MINUTE", "Kids Don't Listen. They Copy.", "He Was Always Connected. Just Not to Her.", "Just 5 More Minutes… It's 2:14 AM" — all suffixed "| An Animated Short Film".
- **Day One Films**: "DISCIPLINE | An Animated Short Film" (2.9M views) — near-silent, a shadow "inner voice" character, a subtitle that says the opposite of what's spoken, a quotable line ("Day one, or one day"), timed to a self-improvement trend.
- What they share: one relatable inner struggle, one protagonist, almost no words, one physical device that tracks the struggle (a plan on the fridge, an alarm, a phone), a turn delivered by a short question or line, a montage of small repetitions, and an ending that returns to the opening image changed.

## The spine (5 chapters ≈ 60–80s each)
| ch | name | job | typical shots |
|---|---|---|---|
| 1 | **The promise / the trap** | Show normal life and the problem through repetition, not explanation. Plant the device and the opening image. | alarm/phone insert, wide of the room, the plan pinned up, first small failure |
| 2 | **The fall** | The failure compounds; show cost (missed moment, crossed-out calendar, someone waiting). End on rock bottom: a still image, near-silence. | calendar insert (X's fill), slump, empty chair, rain, `music.silence` |
| 3 | **The turn** | A person/object reframes it in ≤ 8 words ("Can you run one minute?"). The loudest musical moment lands here. | OTS dialogue, close-up reaction, `music.hit` |
| 4 | **The climb** | Montage of tiny repetitions; the device fills up the other way; time visibly passes (seasons, light, calendar). One setback, recovered. | day-by-day cuts, same framing changed, title card "DAY 12" |
| 5 | **The payoff** | The opening image returns, changed (alarm → he gets up; X's → ticks). A quiet final beat, then the title. | callback shot, wide with warm light, title card |

Timing for a 6:00 film: ch1 0:00–1:10 · ch2 1:10–2:20 · ch3 2:20–3:10 · ch4 3:10–5:00 · ch5 5:00–6:00. Expect 55–80 shots (average 4.5–6s; montage shots 2–3s; holds up to ~10s).

## Rules that make it work
- **Show, don't say.** Total dialogue under ~10 short lines. If a line explains the feeling, cut it and show the feeling.
- **One device you can say in a sentence**: "every day he crosses a box out — later he ticks them." The device must be visible at phone size.
- **The reframe line is the film's thesis** and probably its title. ≤ 8 words. Shown once, maybe echoed at the end.
- **Something changes every 2–4 seconds**: a cut, a move, a gesture, a prop changing. Blinks and breathing don't count.
- **Silence before the payoff, loudest on the payoff** (`music.silence` on the shot before, `music.hit` on the turn).
- **Callback ending**: reuse the exact framing of an early shot with the difference the story made.
- **Time passes visibly**: calendar pages, light from night to sunrise, seasons (leaves → snow → green), a "3 WEEKS LATER" card at most once.
- **Colour script**: grey/cold palettes (`cold`, `night`, `overcast`) for the trap, warm (`warm`, `sunrise`, `day`) for the climb and payoff.
- **One universal truth, no lecture.** End on an image, not a moral. The description can ask the question.
- **Original**: use the reference channels' *structure*, never their stories, characters or titles. No real people, brands or copyrighted music.

## Idea generation and scoring
Generate 8–10 candidates, then score each 1–5 on:
| criterion | question |
|---|---|
| Relatable pain | Would 1 in 3 viewers say "that's me"? (procrastination, phone, sleep, comparison, burnout, loneliness, parenting, regret, quitting, self-worth) |
| Visual device | Is there a prop that can track the struggle and flip at the end? |
| Reframe line | Can the turn be one short question/sentence? |
| Wordless | Can it be understood with the sound off and ≤ 10 lines? |
| Callback | Does the opening image come back changed? |
| Title hook | Does a 1–4 word title or a sharp hook statement exist? |
| Producible | Do the needed sets/props exist in the engine (or are cheap to add)? |
| Fresh | Not a reskin of a recent viral video? |
Pick the highest total; break ties toward the stronger device. Present the top 3 with logline, device, reframe line and title.

Trend timing helps (new year, back to school, "winter arc", exam season, Ramadan, summer break) — check with vidIQ/Apify if available (see research.md).

## Story sheet (story.md in the film folder) — the gate before any animation
1. Logline (1 sentence), the trap, the device, the reframe line, the callback, 3 title options.
2. The beat table: `# | ch | time | beat (what we SEE) | shot ideas | sound` — 25–40 beats with running times that sum to the target length.
3. Dialogue list (every caption, ≤ 8 words each).
4. Cast list with builds/wear, set list with times of day (the colour script).
5. **Decisions** — what you chose and why when the user wasn't there to ask.

## Shot list craft
- Scale variety: establish wide → act in medium/close → cut to an insert for every important object. At least one extreme close-up (eyes, hand on the alarm).
- Over-the-shoulder pairs for conversations (`ots: 'left'` foreground + `cam: 'medium:<other>'`), reverse with the other side.
- Montage = same framing repeated with one thing changed (calendar fills, light shifts, outfit changes).
- Insert shots carry the plot: phone screens, calendars, clocks, notes. Give each one a camera push and a sound.
- End chapters on a held image + `out: 'fade'`; open the next with a fresh place or time of day.

## Packaging (written now, assembled by package.py)
- Title: "WORD | An Animated Short Film" or a hook statement ("You're Not Lazy. You're Too Comfortable."). ≤ 70 characters before the suffix gets cut.
- Hook (first 2 description lines): the setup in plain words, ending on the turn ("Then she asked him something else instead.").
- Question for comments; 3–5 hashtags; 10–15 tags.
- Thumbnail: one character + one object, ≤ 3 words, high contrast, readable at 160px wide. Use the payoff or the most iconic insert.
