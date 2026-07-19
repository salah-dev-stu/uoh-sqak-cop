import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { parseGame, deriveEvents, distanceSeries, beliefErrorSeries, glyphModel,
  manhattan, argmax2d, scoreEstimate } from '../js/data.js';

const load = f => parseGame(JSON.parse(readFileSync(new URL('../' + f, import.meta.url), 'utf8')));
const honest = load('replay3d.json');
const tampered = load('replay3d_tampered.json');

test('parseGame rejects wrong schema', () => {
  assert.throws(() => parseGame({ viz_schema: 1, frames: [] }));
});

test('event derivation: one marker per barrier increment, audit closes the game', () => {
  const ev = deriveEvents(honest);
  const last = honest.frames.at(-1);
  assert.equal(ev.at(-1).type, 'audit');
  assert.equal(ev.at(-1).turn, last.turn);
  let prev = 0, inc = 0;
  for (const f of honest.frames){ if (f.barriers.length > prev) inc++; prev = f.barriers.length; }
  assert.equal(ev.filter(e => e.type === 'barrier').length, inc);
  assert.equal(ev.some(e => e.type === 'capture'), honest.outcome === 'capture');
});

test('distance & belief-error series', () => {
  const d = distanceSeries(honest), e = beliefErrorSeries(honest);
  assert.equal(d.length, honest.frames.length);
  assert.equal(d[0], manhattan(honest.frames[0].cop, honest.frames[0].thief));
  const f0 = honest.frames[0];
  assert.equal(e[0], manhattan(argmax2d(f0.belief), f0.thief));
  assert.ok(e.every(x => Number.isInteger(x) && x >= 0));
});

test('glyph model: chronological interleave, honest log is clean', () => {
  const g = glyphModel(honest);
  assert.equal(g.chips.length, honest.records.length);
  assert.deepEqual([g.chips[0].side, g.chips[0].step], ['cop', 1]);
  assert.deepEqual([g.chips[1].side, g.chips[1].step], ['thief', 1]);
  assert.ok(g.chips.every(c => c.short.length === 9 && c.short[0] === '#'));
  assert.equal(g.firstBad, -1);
  assert.equal(g.tampered, false);
});

test('glyph model: tampered fixture flags the forged step in display order', () => {
  const g = glyphModel(tampered);
  assert.equal(g.tampered, true);
  const bad = g.chips[g.firstBad];
  assert.equal(bad.status, 'TAMPERED');
  assert.deepEqual([bad.side, bad.step], ['thief', 1]);
  assert.equal(g.firstBad, 1); // cop step 1 seals first, forged thief step 1 is next
});

test('score estimate voids the match on tamper', () => {
  assert.deepEqual(scoreEstimate(tampered, 999), { cop: 0, thief: 0 });
  const s = scoreEstimate(honest, honest.frames.length);
  assert.equal(s.thief > 0, honest.outcome === 'survival');
});
