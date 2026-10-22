// Chapter 3 — the turn: one tiny action. music.hit lands the loudest moment here.
SF.add({ ch: 3, set: 'kitchen', time: 'day' }, [
  { id: 'glass', dur: 3.5, beat: 'Sam notices — fills one glass', music: { hit: true },
    cam: [[0, 'medium:sam'], [3.5, 'close:sam']],
    cast: { sam: { at: 'sink', facing: 'right', face: 'tired', act: [[0.4, 'look', 'left'], [1.2, 'face', 'hopeful'], [1.6, 'gesture', 'reach', { dur: 1.4 }]] } },
    sfx: [[1.8, 'cup_down']] },
  { id: 'water', dur: 4, set: 'living', beat: 'he waters the plant', caps: [[0.8, 'sam', 'Just one glass.']],
    props: [{ type: 'houseplant', at: [1560, 560], z: 2.3, s: 0.8, state: { health: [[0, 0.12], [4, 0.3]] } }],
    cast: { sam: { at: [1380, 790], facing: 'right', pose: 'reachForward', hold: { R: 'bottle' } } }, cam: 'two:sam+sam' },
]);
