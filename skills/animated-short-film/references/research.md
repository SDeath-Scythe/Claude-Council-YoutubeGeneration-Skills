# Researching a reference channel or trend (optional, before the idea step)

Use when the user names a channel/video to match, or asks for ideas that will perform. Skip it when the user already has a story.

## Tools that work from a web session
- **vidIQ connector** (credits: 5 per stats/videos/transcript call, 25 per `vidiq_video_watch`; check `vidiq_balance` first and tell the user what you'll spend):
  - `vidiq_channel_stats` (channelId can be the @handle, `from` date) → subscribers/views/daily growth.
  - `vidiq_channel_videos` (`videoFormat: 'long'`, `popular: true`) → top videos with views, duration, VPH.
  - `vidiq_outliers` / `vidiq_trending_videos` / `vidiq_channel_search` (`breakoutChannel: true`) → what's working in a niche right now.
- **Apify connector** (pay per use, free tier ≈ $5/month):
  - `emttn/frameskim` — real frames from a video: `{ mode: 'segment', url, every: 10, maxFrames: 30, quality: 'standard' }` ≈ $0.12/video + $0.015/frame; frames come back as key-value-store records (`frame-NNN-<ms>.jpg`) you can open with `get-key-value-store-record` and look at.
  - `supreme_coder/youtube-transcript-scraper` — `{ urls: [{url}], outputFormat: 'text' }`, ~$0.001/video (some videos have captions disabled).
  - `streamers/youtube-channel-scraper` with `sortVideosBy: 'POPULAR'` for a channel's top videos.
- Plain WebSearch for articles/interviews about the creator's process.

## What to measure (write it into the story sheet)
1. Length, number of chapters, shots per minute (frames every 10s show how often the picture changes).
2. How much is spoken (transcript: mostly `[music]` = captions-only film).
3. The structure: setup / failure / turn / climb / payoff timings.
4. The device and the reframe line.
5. Palette and lighting per act (cold → warm?), character design, how text appears.
6. Title pattern, description pattern (setup retold + chapters + question + hashtags), upload cadence.

## Turn findings into a film — structure, not reskin
Map each measured beat to a new subject with a true counterpart: their device (a plan pinned to the fridge) becomes yours (a jar of unsent letters); their reframe question becomes yours. Never reuse their story, title, character names or dialogue.

## Last measured (Oct 2026) — refresh before relying on it
Last Soul: 5:00 film, 30 frames sampled — shot changes every ~5s on average, 4 spoken caption lines total, chapters "Big Plans / Giving Up / One Minute / Day by Day / Where It Takes You", palettes grey interiors → night rain → warm daylight. Day One Films: "DISCIPLINE" 2.9M views; inner-voice shadow; catchphrase title.
