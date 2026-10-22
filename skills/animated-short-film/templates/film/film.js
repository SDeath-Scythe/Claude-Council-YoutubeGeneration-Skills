// film.js — config, chapters (mood + energy drive the score), cast, look, thumbnail and YouTube package.
// This template is a ~40s demo ("THE PLANT"). Copy the folder, then replace EVERYTHING with your own story.
SF.film({
  title: 'THE PLANT',
  target: [30, 70],                 // seconds the QA expects; a real episode is [300, 420]
  fps: 30,
  palette: 'day',                   // default; shots override with time:'night' etc.
  chapters: [                       // shots point at these with ch: 1..5
    { title: 'Neglect', mood: 'melancholy', energy: 0.25 },
    { title: 'Wilting', mood: 'lonely', energy: 0.18 },
    { title: 'One Glass', mood: 'tender', energy: 0.35 },
    { title: 'Every Morning', mood: 'determined', energy: 0.68 },
    { title: 'Bloom', mood: 'uplifting', energy: 0.8 },
  ],
  music: { key: 'D', bpm: 70, motif: [3, 2, 1, 2, 3, 5, 3] },   // motif = scale degrees, returns in the last chapter
  cast: {
    sam: { name: 'Sam', build: 'adult', wear: ['sneakers'] },
  },
  look: { vignette: 0.55, dof: 1.7 },
  thumbnail: { shot: 'bloom-close', t: 2.0, text: 'ONE GLASS' },
  package: {
    title: 'THE PLANT | An Animated Short Film',
    hook: 'Sam never had time for the plant on the windowsill. Then one morning he gave it one glass of water.',
    summary: 'A short film about tiny habits and the things that wait for us.',
    question: 'What is your "one glass" this week?',
    hashtags: ['AnimatedShortFilm', '2DAnimation', 'ShortFilm'],
    tags: ['animated short film', 'habits', 'motivation', 'self improvement', '2d animation'],
  },
});
