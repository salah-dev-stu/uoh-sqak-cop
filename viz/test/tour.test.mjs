import test from 'node:test';
import assert from 'node:assert/strict';
import { tourBeats, sampleTour } from '../js/tour.js';

test('tour beats span a fixed schedule and walk the replay forward', () => {
  const b = tourBeats(35);
  assert.ok(b.length >= 5);
  assert.equal(b[0].t, 0);
  for (let i = 1; i < b.length; i++) assert.ok(b[i].t > b[i - 1].t);   // strictly timed
  assert.equal(b[0].turn, 0);
  assert.equal(b[b.length - 1].turn, 34);                              // finishes on the last frame
  for (let i = 1; i < b.length; i++) assert.ok(b[i].turn >= b[i - 1].turn); // monotone scrub
});

test('sampleTour clamps before the start and after the end', () => {
  const b = tourBeats(35);
  const before = sampleTour(b, -9);
  assert.deepEqual(before.pos, b[0].pos);
  assert.equal(before.turn, 0);
  assert.equal(before.done, false);
  const after = sampleTour(b, 9999);
  assert.deepEqual(after.pos, b[b.length - 1].pos);
  assert.equal(after.done, true);                                      // past the end → done
});

test('sampleTour eases between two beats (smoothstep, not linear)', () => {
  const b = [
    { t: 0, pos: [0, 0, 0], target: [0, 0, 0], turn: 0, caption: 'a' },
    { t: 10, pos: [10, 0, 0], target: [0, 0, 0], turn: 4, caption: 'b' },
  ];
  const mid = sampleTour(b, 5);
  assert.ok(Math.abs(mid.pos[0] - 5) < 1e-9);       // smoothstep(0.5) = 0.5 exactly
  const early = sampleTour(b, 2.5);
  assert.ok(early.pos[0] < 2.5);                    // eased-in: slower than linear early
  assert.equal(mid.caption, 'a');                   // caption is the segment we're inside
});
