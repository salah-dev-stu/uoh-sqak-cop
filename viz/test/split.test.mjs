import test from 'node:test';
import assert from 'node:assert/strict';
import { halfRects } from '../js/split.js';

test('halfRects splits the canvas into two equal side-by-side viewports', () => {
  const [left, right] = halfRects(800, 600);
  assert.deepEqual(left, { x: 0, y: 0, w: 400, h: 600 });
  assert.deepEqual(right, { x: 400, y: 0, w: 400, h: 600 });
});

test('halfRects handles an odd width without dropping a column', () => {
  const [left, right] = halfRects(801, 600);
  assert.equal(left.w + right.w, 801);       // no pixel lost to rounding
  assert.equal(right.x, left.w);             // right starts where left ends
});
