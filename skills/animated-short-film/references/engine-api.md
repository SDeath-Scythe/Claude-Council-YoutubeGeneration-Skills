# Engine API — writing a film

Everything a film needs, in the order you'll use it. A film is a folder: `film.js` (config + cast), `shots/*.js` (one file per chapter, loaded in name order), optional `lib/*.js` (your own sets/props/helpers, loaded first). Never use `Math.random()` or `Date` — use `SF.rnd(i, seed)`, `SF.RNG(seed)`, `SF.noise(x, seed)`.

## Contents
1. Film config
2. Shots (every field)
3. Camera
4. Cast and characters
5. Acting: verbs, poses, gestures, gaits, expressions
6. Sets and marks
7. Props, held items, inserts
8. Effects, lights, grade
9. Captions, titles, transitions
10. Sound cues and music flags
11. Custom drawing (draw hook, layers, your own set/prop)
12. Debugging and the render log

---

## 1. Film config — `SF.film({...})` in film.js

```js
SF.film({
  title: 'ONE MINUTE',               // used for the board, package slug, end card
  target: [300, 420],                // seconds; qa.py checks the cut against it
  fps: 30,
  palette: 'day',                    // default palette (shots override via time:/palette:)
  chapters: [                        // index = shot.ch - 1. mood + energy drive the generated score
    { title: 'Big Plans', mood: 'hopeful', energy: 0.3 },
    { title: 'Giving Up', mood: 'melancholy', energy: 0.2 }, ...
  ],
  music: { key: 'D', bpm: 70, motif: [3, 2, 1, 2, 3, 5, 3] },  // motif: scale degrees; plays early, returns fuller at the end
  cast: { greg: { name: 'Greg', build: 'adult', wear: ['sneakers'] }, ... },   // see §4
  look: { grain: 0.03, grainStep: 3, vignette: 0.55, dof: 1.7, parallax: 0.12, handheld: 0.35,
          captions: { size: 54, color: '#fff', stroke: '#15171c', band: 0.5 } },
  fadeIn: 1.0, fadeOut: 2.0,         // film-level fades (s)
  thumbnail: { shot: 'payoff', t: 2.0, text: 'ONE MINUTE' },   // or draw: (g, SF) => {...} on a 1920x1080 canvas
  package: { title, titles: [...], hook, summary, question, hashtags: [...], tags: [...], pinned, credits },
});
```
Moods: hopeful, uplifting, triumphant, melancholy, sad, lonely, tense, anxious, tender, warm, reflective, calm, neutral, determined, building, bittersweet, playful, mysterious. Energy 0–1: >0.12 pad, >0.28 bass, >0.45 strings, >0.62 soft drums.

## 2. Shots — `SF.add(defaults, [shot, ...])` in shots/NN_name.js

`defaults` merge into every shot of the call: `SF.add({ ch: 2, set: 'kitchen', time: 'night' }, [...])`.

| field | meaning |
|---|---|
| `id` | unique, kebab-case (`fridge-plan`). Used by board, QA, cam targets, thumbnail. |
| `ch` | chapter number (1-based). |
| `dur` | seconds. Most shots 2.5–7s; holds up to ~12s. |
| `beat` | one line: what we SEE. Shows on the storyboard. |
| `key` | time (s) of the storyboard frame (default mid-shot). |
| `set`, `setOpts`, `time` | environment, its options, time of day (`day`/`dusk`/`night`/`evening`/`sunrise`/`overcast`/`cold`/`void`) — `time` also picks the palette. |
| `palette` | override: name, palette object, or blend `['day','sunrise',0.4]`. |
| `cam` | camera (§3). `focus` (depth or actor id or keys), `dof`, `handheld`, `parallax`, `shake: [{t, amp, dur}]`. |
| `cast` | `{ id: actorSpec }` (§4–5). |
| `props` | `[{ type, at: [x, y], s, z, state }]` — state fields may be keyframes (§7). |
| `insert` | full-frame close-up instead of a set: `{ type: 'phone'|'calendar'|'clock'|'laptop'|'note'|'shoes'|'prop', ...state }` |
| `fx` | `[{ type: 'rain'|'snow'|'leaves'|'dust'|'sparkles'|'fireflies'|'fog'|'confetti'|'steam', z, ...opts }]` |
| `lights`, `grade`, `flashes`, `vignette` | §8 |
| `caps` | dialogue captions `[[t, who, 'text', {dur, pos}]]` (§9) |
| `title` | text card `{ text, sub, t, dur, x, y, size }` |
| `trans`, `transDur`, `out`, `outDur` | transition into / out of the shot (§9) |
| `sfx`, `amb`, `ambGain`, `music`, `footsteps` | sound (§10) |
| `draw`, `drawZ`, `layers`, `overlay` | custom drawing (§11) |
| `hold: true` | a deliberate still shot (QA won't flag it). |

## 3. Camera

World = 1920×1080 at camera rest; `{ x, y, zoom, rot }` puts world point (x,y) at screen centre.
- Shorthand strings: `'wide'`, `'full:greg'`, `'knees:greg'`, `'medium:greg'`, `'close:greg'`, `'ecu:greg'` (eyes), `'hands:greg'`, `'feet:greg'`, add `:left`/`:right` to place the subject on a third (`'medium:greg:left'`), `'two:greg+mia'`, `'mark:fridge'`.
- Object: `{ frame: 'medium', on: 'greg', side: 'left', dx, dy, zoomMul, lock: true }` (lock = framing from t=0, no follow).
- Moves: keys `cam: [[0, 'wide'], [4, 'medium:greg', 'inOut']]` — ease names: linear, in, out, inOut, in3, out3, inOut3, sine, outBack, spring.
- Something should move in most shots: a slow push-in (`zoom` +5–12%) is the default life. `handheld` (default 0.35) adds drift; 0 = locked tripod.
- Depth of field: everything has a depth z (characters from their floor y). Focus defaults to the first cast member; `focus: 'mia'` racks to someone else; `focus: [[0, 0], [2, 3]]` rack focus. `dof: 0` disables blur.

## 4. Cast and characters

```js
cast: { greg: { name: 'Greg', build: 'adult', style: 'silhouette', hair: null, wear: ['sneakers'], wearColors: {}, colors: {}, face: {} } }
```
- `build`: adult · slim · stocky · teen · kid · elder (stooped).
- `style`: `silhouette` (default — ink body, thin rim, white face marks) · `toon` (coloured: `colors: { skin, top, bottom, hair }`) · `shadow` (translucent double, use `face: 'glow'` for the inner-voice/shadow self).
- `hair`: ponytail · bun · short · spiky · mohawk · long · bob · curly · afro.
- `wear`: sneakers · headband · glasses · cap · beanie · beard · raincoat (yellow by default) · hoodie · coat · hood · backpack · tie · apron · skirt · scarf. Colours via `wearColors: { raincoat: '#e7c14a', tie: '#9b2f2f' }`.
- `face: { eyeSize: 1.1, talkMouth: true }` (mouth flaps on lines; off by default — these films speak through captions).
- Render the model sheet with `render.mjs <film> --cast` before animating; every pose on it is joint-checked.

## 5. Acting

Actor spec in a shot: `{ at, dx, dy, facing, s, z, pose, face, hold, hidden, ots, act: [...] }`
- `at`: a mark name (§6), `[x, y]` (y = feet on the floor) or x. Scale and depth come from the set's perspective unless `s` / `z` are given.
- `facing`: front · back · left · right · front-left · front-right · back-left · back-right.
- `ots: 'left'|'right'` — over-the-shoulder foreground figure: placed big in screen space and blurred; frame the other person with `cam: 'medium:mia'`.
- `hold: { R: 'phone' }` items in hands (§7); `pose` / `face` set the starting state.

`act` entries are `[t, verb, arg, opts]` (t = seconds into the shot):

| verb | arg / opts |
|---|---|
| `walk`, `stroll`, `trudge`, `jog`, `run`, `sneak` | target mark / x / `[x, y]`, or `{ to, speed, pace, dur, facing, end }`. Feet stay planted; facing follows the direction; moving in y walks toward/away from camera. `end: 'front'` turns at arrival. Footstep sounds are added automatically. |
| `pose` | pose name or object, `{ dur }` blend (default 0.35s) |
| `gesture` | gesture name, `{ dur }` — temporary overlay that blends in and out |
| `face` | expression name |
| `look` | `'left'|'right'|'up'|'down'|'camera'`, a mark or another actor id |
| `turn` | new facing (instant — cut on it or hide it in a blink) |
| `sit` / `stand` | `{ seat, dur, slump }` — seat height comes from marks like `sofa`, `deskChair`, `bedEdge` |
| `lie` | `{ dir: 'left'|'right' }` — use with the bedroom's `bed` mark and `setOpts: { inBed: true }` |
| `move` | `{ to, dur, ease }` slide without stepping (vehicles, nudges) |
| `hold` / `drop` | hand `'R'|'L'`, item |
| `say` | caption text, `{ dur, pos }` — adds a caption and a small talking head-bob |
| `show` / `hide` | `{ dur }` fade the actor in/out |

- **Poses** (front/side variants built in): stand, relaxed, slump, defeated, proud, armsCrossed, handsOnHips, thinking, raiseHand, fingerUp, point, shrug, holdPhone, holdPhoneUp, carry, reachForward, celebrate, facepalm, headInHands, hug, lookUp, lookDown, tense, ready. A pose object can be raw angles: `{ shR: 60, elR: 40, handR: 'point', neck: 10 }`.
- **Gestures**: wave, nod, shake, shrug, sigh, point, fingerUp, raiseHand, reach, facepalm, scratchHead, clap, fistPump, stretch, yawn, wipeEyes, tap, jumpJoy, flinch, shiver, laugh, cry, breathe (panting), typing, scroll.
- **Gaits**: walk, stroll, sad (=trudge), jog, run, sneak.
- **Expressions**: neutral, calm, happy, content, smile, grin, sad, worried, tired, bored, surprised, shock, determined, angry, cry, teary, sleep, blank, thinking, proud, hopeful, glow. Blinks and breathing are automatic.
- **Joint angles** (for raw poses; degrees from straight down): side view — `sh` forward, `el` forward flex 0..150, `hp` forward, `kn` backward flex 0..155; front view — `sh` outward, `el` −150..150 (− across the body, + outward/up), `hp` outward. Hands: mitten, fist, point, up, open, thumb, peace. Out-of-range values are clamped AND logged; qa.py fails the film until they're fixed.

## 6. Sets and marks

Interiors share one perspective: horizon y=430, back wall meets the floor at y=740, standing line y=900 (character scale 1.85, ~555px tall). Marks near furniture sit closer to the wall (smaller). Every interior also has `center`, `left`, `right`, `back`, `offLeft`, `offRight`.

| set | options (`setOpts`) | marks |
|---|---|---|
| `kitchen` | time, clock | fridge, counter, sink, door, table, counterTop |
| `bedroom` | time, inBed, lump, blanket, alarm ('2:14'), lamp, lampOn, laptopOn, doorOpen, poster, view | bed (lying), bedEdge (sit), bedside, desk, deskChair (sit), window, door |
| `living` | time, sofa (colour) | sofa, sofaL, sofaR (sit), window, door, front |
| `office` | time | desk, deskChair (sit), window, door |
| `store` | item: shoe·book·box·jar·plant·trophy, sign, sign2, poster, mat | counter, behind (clerk), front, door, shelf |
| `hallway` | endOpen | door1, door2, end |
| `classroom` | board (chalk text), clock, time | board, desk1, desk2, teacher |
| `gym` | — | rack, bench |
| `street` | time, rain, wet, variant: 'city', leaf, bare, leavesOnGround, lampStyle | near, center, mid, far, road, lamp (walk toward `far` = walking away) |
| `streetSide` | time, rain, s, trees, leaf | start, mid, end — side-scrolling; follow with `cam: 'full:greg'` |
| `park` | time, sun: [x,y], leaf, lamps | path, left, right, far, bench, benchL, benchR (seat marks) |
| `stage` | spotX, spot:false, spotA, s | spot, left, right — Day One Films black stage with one spotlight |
| `stairs` | steps, x, y, w, h, s | step0…stepN — metaphorical climb toward light |
| `vista` | time ('sunrise'), sunX, sunH, hills | ledge, left, right — payoff horizon |
| `blank` | color | — title cards |

Palettes: day · overcast · dusk · night · warm (lamp-lit evening) · cold · sunrise · void. Plan a colour script: cold/grey for the trap, warm/sunrise for the payoff.

## 7. Props, held items, inserts

- **World props** `props: [{ type, at: [x, y], s, z, state }]` (y = resting point): phone {screen, flat}, alarmClock {time, ringing}, mug {steam}, laptop {on}, lamp {on}, floorLamp, books, plant, houseplant {health 0–1, bloom 0–1}, calendar {title, crossed, check, checked, rows, mark}, clock {hours: 2.25}, poster {icon: runner|mountain, text}, shoes {color, tag}, shoebox, paperBall, trophy, trash, bottle, photo, ball, gift, dumbbell, guitar.
- **Any state field animates** with keyframes: `state: { crossed: [[0, 0], [3, 28]] }`, `health: [[0, .2], [4, 1]]`, or a function `(t) => ...`.
- **Held** (`hold: { R: 'phone' }` or `{ R: { type: 'phone', screen: 'off' } }`): phone (lights the face), mug, paper, book, box, bag, umbrella, ball, flower, bottle, pen.
- **Inserts** (`insert: { type, ... }`, all fields animatable):
  - `phone` — `screen`: lock {time, date, notes: [{app, text, color}]} · alarm {time, label, date, pressed: 'snooze', pressAt} · chat {title, msgs: [{text, me, read}], reveal, typing} · feed {scroll} · timer {seconds, total, label} · call {name, status} · stats {title, value, bars} · note {title, lines} · home · off. Plus `surface` (desk|bed|floor|wall|fridge|dark), `tilt`, `hand: { x, y, ang, tapAt }`.
  - `calendar` {title, crossed, check, checked, mark, hand} · `clock` {hours} · `laptop` {title, rows} · `note` {lines, reveal (characters), tilt} · `shoes` {color, tag} · `prop` {prop, state, s, x, y, sill}.

## 8. Effects, lights, grade

- `fx`: rain {density, angle, splashY, alpha} · snow · leaves {density, wind, colors} · dust {rect: [x,y,w,h]} (motes in a light beam) · sparkles {rect, n} · fireflies · fog {y, alpha} · confetti {t0} · steam {x, y, s}. `z` places them in depth (negative = in front of the actors, blurred).
- `lights`: `[{ type: 'glow', x, y, r, color, a }, { type: 'cone', x, y, dir: 90, spread, len }, { type: 'patch', pts }, { type: 'lamp', x, y, s }, { type: 'screen', x, y, r }]` — sets add their own (windows, lamps).
- `grade: { color, a, mode }` per shot (e.g. `{ color: '#1e2a44', a: 0.25, mode: 'multiply' }` for a colder beat); `flashes: [{ t, type: 'lightning' }]`; `vignette: 0.7`.

## 9. Captions, titles, transitions

- `caps: [[1.0, 'greg', 'Starting tomorrow.']]` — shown above the speaker (or `pos: 'top'|'bottom'`), auto duration (~2.6 words/s, 1.3–5.5s). Keep lines ≤ 8 words; most films need under 10 lines total.
- `title: { text: 'ONE MINUTE', t: 1, dur: 3, y: 520, size: 120, sub }` — end cards / time stamps ("3 WEEKS LATER": size 46, y 980).
- `trans`: cut (default) · fade (from black) · dip · cross (crossfade from the previous shot) · flash. `out: 'fade'` fades a shot to black (end of a chapter).

## 10. Sound cues and music flags

- `sfx: [[t, name, { gain, db, pan, dur }]]` — names: footstep, footstep_run, alarm, phone_buzz, notification, tap, click, door_open, door_close, paper, paper_pin, crumple, marker, whoosh, thud, heartbeat, clock_tick, typing, sigh, inhale, gasp, panting, shop_bell, register, cup_down, riser, boom, car_pass, thunder. Levels are calibrated per kind; use `db` to nudge.
- `amb`: room · room_night · store · office · street · night_street · park · night_park · rain · wind · void · gym · school. Sets supply a default; inserts inherit the previous shot's room. `amb: null` for true silence.
- `music: { silence: true }` drops the score to near-silence for the shot (the breath before the turn); `music: { hit: true }` lands the film's loudest chord + boom at the shot start. Put them on consecutive shots.
- `footsteps: false` disables automatic footsteps for a shot.

## 11. Custom drawing

- `draw(g, t, S)` — runs at depth `drawZ` (default just in front of the actors) with the camera transform; `S = { t, shot, set, P (palette), cam, actors, W, H }`. Use `SF.paint` helpers (`rr`, `ell`, `poly`, `line`, `path`, `curve`, `lin`, `rad`, `glow`, `cone`, `shadow`, `text`, `wrap`) and palette tokens (`S.P.wall`, `S.P.accent`, `S.P.ink`, ...).
- `layers: [{ z, draw(g, t, S, view) }]` — extra depth layers (foreground plants, window frames). `overlay(g, t, S)` — screen space, no camera.
- Your own set in `lib/sets.js`: `SF.sets.diner = (o) => ({ name: 'diner', horizon: 430, floorY: 900, scaleAt: SF.build.persp(), zAt: SF.build.depth(), marks: {...}, amb: 'store', layers: [{ id: 'room', z: 3, static: true, draw: (g, t, Pa) => { SF.build.room(g, Pa, { floor: 'tiles' }); ... } }] })`. Building blocks in `SF.build`: room, window, door, cabinets, counter, fridge, shelfGrid (+ items), bed, blanket, sofa, table, desk, chair, tv, rug, pendant, trackLights, sky, cityline, streetLamp, lampGlow, tree, bench, car, building, depthBands. Furniture is sized in character units (seat 50, table 100, counter 120, mattress 58) × the scale at its base. Always draw it with `s = scaleAt(y)` of its base line — a hand-picked scale makes sitters look like they stand in front of it — and give it seat marks (`SF.build.benchMarks(x, y, s)` for a bench; your own `{ x, y, seat: 50 }` for chairs/sofas). Furniture people sit on must be wider than the sitters (bench default 300 CU for two). Check one sitting still at full size before writing the rest of the scene.
- Your own prop: `SF.props.trophyShelf = (g, x, y, s, st, Pa, t) => {...}` — then use it in `props` or `insert: { type: 'prop', prop: 'trophyShelf' }`.
- Static set layers are cached per shot (with blur baked in): mark a layer `static: true` only if it doesn't change with t.

## 12. Debugging

- `node scripts/render.mjs <film> --eval "SF.debugActor('shot-id','greg',1.5)"` → position, scale, depth, facing, pose numbers, camera.
- Unknown sets/props/poses/verbs and joint clamps are collected in `build/render_log.json` and fail `qa.py`.
- A blank or wrong frame: render one still `--stills shot:<id>@<t> --size 1920x1080` and look at it before re-rendering video.
