// Chapter 1 — the trap, shown not told. Open on the object that will come back changed at the end.
SF.add({ ch: 1 }, [
  { id: 'lock', dur: 3, beat: 'phone lights up, notifications pile in',
    insert: { type: 'phone', screen: 'lock', time: '7:42', date: 'Mon, Mar 3', surface: 'bed', tilt: -5,
      notes: [{ app: 'Work', text: 'Standup moved to 8:00', color: '#e8833a' }, { app: 'Mail', text: '14 new messages' }] },
    cam: [[0, { zoom: 1.0 }], [3, { zoom: 1.07 }]], sfx: [[0.4, 'notification'], [1.5, 'notification']] },
  { id: 'sofa', dur: 4.5, set: 'living', beat: 'Sam scrolls; the plant droops behind him',
    cam: [[0, 'full:sam'], [4.5, 'medium:sam']],
    props: [{ type: 'houseplant', at: [1560, 560], z: 2.3, s: 0.8, state: { health: 0.35 } }],
    cast: { sam: { at: 'sofa', pose: 'holdPhone', hold: { R: 'phone' }, act: [[0, 'sit', { dur: 0.01 }], [1.2, 'gesture', 'scroll', { dur: 3 }]] } } },
]);
