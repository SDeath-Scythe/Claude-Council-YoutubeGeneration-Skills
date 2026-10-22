// Chapter 5 — payoff + callback: the opening image returns, changed.
SF.add({ ch: 5 }, [
  { id: 'bloom-close', dur: 3.5, beat: 'it blooms',
    insert: { type: 'prop', prop: 'houseplant', state: { health: 1, bloom: [[0, 0], [3, 1]] }, s: 3.4, y: 980 },
    cam: [[0, { zoom: 1.12, y: 600 }], [3.5, { zoom: 1.0 }]], fx: [{ type: 'sparkles', z: -0.2, rect: [700, 300, 520, 500], n: 16 }] },
  { id: 'end', dur: 6, set: 'living', beat: 'Sam reads by the plant; no phone',
    props: [{ type: 'houseplant', at: [1560, 560], z: 2.3, s: 0.8, state: { health: 1, bloom: 1 } }],
    cast: { sam: { at: 'sofa', face: 'content', hold: { R: 'book' }, pose: 'carry', act: [[0, 'sit', { dur: 0.01 }]] } },
    cam: [[0, 'medium:sam'], [6, 'full:sam']], out: 'fade', outDur: 1.2,
    title: { text: 'ONE GLASS', t: 2.4, dur: 3.2, y: 150, size: 88 } },
]);
