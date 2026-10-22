// Chapter 2 — consequence. A silence beat right before the turn makes the next hit land.
SF.add({ ch: 2 }, [
  { id: 'plant-close', dur: 3.5, beat: 'a leaf falls', music: { silence: true },
    insert: { type: 'prop', prop: 'houseplant', state: { health: [[0, 0.3], [3.5, 0.12]] }, s: 3.4, y: 980 },
    cam: [[0, { zoom: 1.0 }], [3.5, { zoom: 1.12, y: 600 }]], sfx: [[2.6, 'paper', { gain: 0.6 }]] },
]);
