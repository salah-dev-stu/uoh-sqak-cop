import test from 'node:test';
import assert from 'node:assert/strict';
import { frameKey, mergeFrames, spectateToViz } from '../js/live.js';

const belief = argmaxAt => {
  const g = Array.from({ length: 7 }, () => Array(7).fill(0.01));
  g[argmaxAt[0]][argmaxAt[1]] = 1;
  return g;
};
const sf = (over = {}) => ({ spectate_schema: 1, turn: 1, role: 'police', phase: 'sent',
  me: [0, 0], belief: belief([3, 3]), known_barriers: [], last_hint: 'hi', last_intent: null,
  claims: {}, commit8: 'abcd1234', sub_game: 1, outcome: null, ...over });

test('mergeFrames appends only unseen (sub_game,turn,phase) keys, order kept', () => {
  const a = sf(), b = sf({ phase: 'received' }), c = sf({ turn: 2 });
  let seen = mergeFrames([], [a, b]);
  assert.equal(seen.length, 2);
  seen = mergeFrames(seen, [b, c]);                 // b is a duplicate
  assert.deepEqual(seen.map(frameKey), ['1:1:sent', '1:1:received', '1:2:sent']);
});

test('spectateToViz puts own token solid and the opponent as a belief-peak ghost', () => {
  const g = spectateToViz([sf()]);
  assert.equal(g.viz_schema, 2);
  const f = g.frames[0];
  assert.deepEqual(f.cop, [0, 0]);                  // police stream → me is the cop
  assert.deepEqual(f.thief, [3, 3]);                // opponent = argmax(belief), never invented
  assert.equal(f.belief[3][3], 1);
});

test('spectateToViz mirrors slots for a thief stream', () => {
  const f = spectateToViz([sf({ role: 'thief', me: [6, 6] })]).frames[0];
  assert.deepEqual(f.thief, [6, 6]);                // own token
  assert.deepEqual(f.cop, [3, 3]);                  // ghost opponent at belief peak
  assert.equal(f.thief_belief[3][3], 1);            // own belief on the thief floor
});

test('spectateToViz surfaces the final outcome result', () => {
  const g = spectateToViz([sf(), sf({ turn: 2, outcome: { result: 'capture', winner: 'police' } })]);
  assert.equal(g.outcome, 'capture');
});
