# Look and sound

## The look (what separates it from "AI slop")
Measured from the reference frames: flat-vector sets with real lighting, ink silhouettes with a thin light rim, depth-of-field, muted palettes with one warm accent, and almost no on-screen text.

- **Characters**: ink silhouettes (big round head ~27% of height, bean torso, short thick legs, mitten hands), white dot eyes + thin brows carry all the emotion. One saturated wardrobe item can mark a character (the yellow raincoat). Keep every character in the same style; never mix styles within a film except the `shadow` inner-voice double.
- **Light first**: every shot has a key light you can point to — window patch, lamp cone, street-lamp glow, phone glow on a face, spotlight. Night = deep blue + warm practicals. If QA says a shot is "very dark", light the subject, don't brighten the world.
- **Depth**: put something in front (an OTS shoulder, a plant, a counter edge with `z` < 0) and let it blur. Rack focus between two characters for a reveal.
- **Colour means one thing**: reserve the accent (amber/yellow) for the hopeful thread — the lamp that's on when he succeeds, the raincoat, the sunrise.
- **Camera**: slow push-ins on emotion, locked frames on comedy and on routine (so changes read), a pan to reveal, `shake` only on impacts. Hold the frame steady during a callback so the difference reads.
- **Text in the world**: phone UIs, calendars, notes, signs. Captions only for spoken lines. A time card ("2:14 AM", "DAY 30") at most a few times.
- **Banned defaults**: centred title on a gradient as an opening; every element fading in; floating particles with no source; glows on everything; a character standing still in the middle of an empty room for 6 seconds; the same medium shot five times in a row; random camera shake.
- **Phone check**: look at `review/phone_01.jpg` — faces, props and captions must read at 180px wide.

## Sound
The generated score (`scripts/sound.py score`) is composed from the chapter list: each chapter's mood picks a progression and piano texture, energy adds pad → bass → strings → soft drums, the `music.motif` plays early and returns with bells in the last chapter, `music.silence` shots drop the score to near-silence and `music.hit` lands a chord stab + boom with a riser before it. It is deterministic, royalty-free and always in sync with the cut — good enough to ship, but you cannot hear it: say so and suggest the user listens.

Better music when the user wants it (always respect licences; never use commercial songs):
- **Suno / ElevenLabs Music** (paid plans grant commercial use): prompt with "solo felt piano, slow 70 BPM, melancholic then hopeful, swells at 2:30, warm strings at 4:30, ends quietly at 6:00". Download, then `python3 scripts/sound.py <film> all --music track.mp3` — the mix fades the tail and still ducks the silence shots.
- **vidIQ connector** (`vidiq_generate_music`) if the user has credits — ask before spending them.
- A track the user owns. Put the turn on its biggest change: move the `music.hit` shot to that time.

Sound effects are synthesised and level-calibrated per kind (footsteps quiet, UI sounds medium, impacts high); footsteps are generated automatically from walk cycles. Every shot gets an ambience bed from its set (inserts keep the room they cut from), so there's never dead air. Voice: these films are wordless; if the user wants a narrator or real dialogue, record or generate one file per caption (`voice/1.wav`, `voice/2.wav`, …) and run `sound.py <film> all --voice <film>/voice` — the mix ducks the music under each line. ElevenLabs connector or the user's own voice; never clone a voice without consent.

Targets checked by qa.py: −14 LUFS integrated (±1.5), true peak ≤ −1 dBTP, no dead air > 2s outside silence beats, the hit ≥ 8 dB louder than the 2s before it. Read `review/audio_arc.png`: the curve should follow the chapters, dip in the grey silence band and spike on the red hit line.
