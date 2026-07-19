// Entry so `node --test viz/test/` works on Node 22 (directory args resolve
// through index.js). Each file also runs standalone: node --test viz/test/*.mjs
import './data.test.mjs';
import './timeline.test.mjs';
import './tour.test.mjs';
