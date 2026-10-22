// Chapter 4 — the climb: a montage of small repetitions; the progress device fills up.
SF.add({ ch: 4 }, [
  { id: 'calendar', dur: 3, beat: 'days tick by', insert: { type: 'calendar', title: 'ONE GLASS A DAY', check: true, checked: [[0, 1], [3, 21]], crossed: 0, surface: 'fridge' },
    cam: [[0, { zoom: 1.0 }], [3, { zoom: 1.08 }]], sfx: [[0.5, 'marker'], [1.3, 'marker'], [2.1, 'marker']] },
  { id: 'morning-walk', dur: 4, set: 'street', time: 'day', beat: 'walks to work, lighter', setOpts: { leavesOnGround: false },
    cast: { sam: { at: [420, 1000], face: 'calm', act: [[0, 'walk', { to: [700, 760] }]] } }, cam: [[0, { x: 760, y: 640, zoom: 1.4 }], [4, { x: 800, y: 600, zoom: 1.6 }]] },
]);
