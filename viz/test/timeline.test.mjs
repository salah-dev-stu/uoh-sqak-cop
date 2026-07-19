import test from 'node:test';
import assert from 'node:assert/strict';
import { clampTurn, frameIndex, frameFrac, markers, stepTurn, visibleChips }
  from '../js/timeline.js';

test('turn math clamps and splits fractional turns', () => {
  assert.equal(clampTurn(-3, 35), 0);
  assert.equal(clampTurn(99, 35), 34);
  assert.equal(frameIndex(3.75), 3);
  assert.ok(Math.abs(frameFrac(3.75) - 0.75) < 1e-9);
});

test('marker positions span 0..1 by turn and keep their type', () => {
  const ms = markers([
    { turn: 1, type: 'barrier' },
    { turn: 18, type: 'capture' },
    { turn: 35, type: 'audit' },
  ], 35);
  assert.equal(ms[0].frac, 0);
  assert.equal(ms[2].frac, 1);
  assert.equal(ms[1].frac, 0.5);
  assert.equal(ms[1].type, 'capture');
});

test('single-frame games pin markers to 0', () => {
  assert.equal(markers([{ turn: 1, type: 'audit' }], 1)[0].frac, 0);
});

test('stepping moves one whole turn and respects bounds', () => {
  assert.equal(stepTurn(5.4, 1, 35), 6);
  assert.equal(stepTurn(0.2, -1, 35), 0);
  assert.equal(stepTurn(34, 1, 35), 34);
});

test('chip visibility follows the passing turn', () => {
  const chips = [{ step: 1 }, { step: 1 }, { step: 2 }];
  assert.equal(visibleChips(chips, 1).length, 2);
  assert.equal(visibleChips(chips, 0).length, 0);
  assert.equal(visibleChips(chips, 2).length, 3);
});
