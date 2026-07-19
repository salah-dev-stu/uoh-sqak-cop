# PRD — Masterclass 3D Visualization ("The Exhibit")

| | |
|---|---|
| **Mechanism** | 3D arena upgrade: from replay toy → masterclass exhibit of the project's two invisible ideas — *partial information* and *cryptographic trust* |
| **Phase** | P4 (Excellence & showcase) · builds on P0's engine instrumentation hook (IH) and P1's live runtime |
| **Gates served** | F12 (GUI/replay deliverable + screenshots) · excellence band §UI/UX (Nielsen) · demo material for grading/league |
| **Current state** | `viz/index.html` (265-line monolith, vendored Three.js, bloom, orbit/scrub/new-match) + `scripts/viz_server.py` + static `replay3d.json` fallback |
| **Doc status** | Planning gate — approve before implementation. Tasks: TODO §Masterclass-Viz (T581+) |

## 1. Audit of the current arena
**Works:** self-contained Three.js (no CDN/build), calm neon look, orbit/zoom, scrub/speed, fresh-game API, belief floor, barrier rise, beams.
**Falls short of masterclass:** (a) tells no story — commit-reveal/audit invisible, single-perspective view hides the Dec-POMDP; (b) no cinematics — capture/survival end with a text overlay, camera is a passive orbit; (c) scent = static discs; (d) one 265-line HTML file (R8-spirit violation, untestable); (e) data layer duplicates the engine (fixed by IH-instrumentation); (f) no way to show a REAL league match.

## 2. Vision
One line: **"Watch two agents that don't trust each other hunt through fog — and watch mathematics referee them."** Three modes, one scene:
1. **Replay theater** (offline, grader-safe) — load any captured game, incl. a bundled tampered log that ends in a red shatter.
2. **Live spectate** — watch a real match (P1 runtime streams frames; falls back to the self-match generator today).
3. **Guided tour** — a 25-second scripted camera intro that explains board → scent → belief → sealed moves → audit, for demos and the README video.

## 3. Requirements

### MV-A · Cinematic camera & finales
- A1 Follow-cam: smooth damped framing that keeps both agents + action centroid in view; auto-zooms as the gap closes; user orbit overrides, idle resumes.
- A2 **Capture finale**: slow-mo (0.25×) dolly-in as the box closes → barrier walls slam with impact ripple → cop beam flare → freeze-frame scoreboard.
- A3 **Survival finale**: clock ring completes → thief beam fireworks → scoreboard.
- A4 Turn micro-pulses (agent hop easing, tile ping on landing); ALL motion honors `prefers-reduced-motion`.

### MV-B · The crypto story (the differentiator)
- B1 **Commit rail**: every move spawns a sealed glyph (rounded chip showing the first 8 hash chars) sliding onto a side rail — the game visibly accumulates *sealed evidence*, moves unreadable.
- B2 **Audit wave**: at game end the rail unlocks glyph-by-glyph in a wave; each flips green (verified) — final banner *Verified OK*.
- B3 **Tamper demo**: bundled `replay3d_tampered.json`; the forged step flips red, the rail shatters from that glyph onward, banner *TAMPERED — match void 0/0*. One toggle to switch honest/tampered replay.
- B4 Glyph inspector: click a glyph → payload/nonce/commit popover (real data from the log).

### MV-C · Dual-belief truth (the Dec-POMDP story)
- C1 View switcher: **Cop view** (cop belief floor + opponent scent only) · **Thief view** (thief's belief of the cop) · **Truth view** (replay-only: both real positions + both beliefs ghosted).
- C2 Split-screen "what each agent knows" mode (two viewports, one timeline).
- C3 Belief-error ribbon: line from belief-peak to true cell in Truth view — watch the phantom-trail error shrink when the P2 delta-belief brain lands (before/after replays = measurable Adaptation demo).

### MV-D · Living matter
- D1 Scent as particle wake: emitted at the thief's cell, drifting/fading with the real decay ρ — a readable gradient trail, not discs.
- D2 Barrier slam: wall drops with squash-stretch + ground ripple + dust puff.
- D3 Floor upgrade: subtle fresnel grid, vignette, tile ping on belief-peak jumps.

### MV-E · Information layer (HUD)
- E1 Event timeline on the scrub bar: markers for barriers, claims, captures, audit.
- E2 Sparklines: cop–thief distance + belief error over turns (canvas, tabular-nums).
- E3 Score/intent chips: live points, current hint text with truth/lie intent badge (visible in Truth view only — bluffs stay hidden in agent views).

### MV-F · Architecture (code quality = grade)
- F1 Split the monolith into ES modules **≤150 lines each**: `main.js, scene.js, board.js, agents.js, scent.js, barriers.js, beliefs.js, crypto_rail.js, camera.js, finales.js, hud.js, timeline.js, data.js, tour.js` + `style.css`; `index.html` becomes a ≤50-line shell. Extend `check_file_lines.py` to cover `viz/*.js` (closes the R8 gap).
- F2 One data schema shared with the engine: frames+events produced by the IH instrumentation hook on `run_game` (no duplicated engine); versioned `viz_schema`.
- F3 Zero build step preserved (import-map + vendored Three); works offline from disk except live mode.
- F4 Testable logic: pure functions (`data.js`, timeline reduction, glyph states, camera targets) get pytest-independent JS sanity checks via `node --test` in CI (small, no framework).

### MV-G · Performance & polish
- G1 60 fps on the M2: instanced tiles/particles, DPR cap 2, bloom budget, quality toggle (Low/High).
- G2 Keyboard: space play/pause, ←/→ step, 1/2/3 views, T tour, N new match; focus-visible states; ARIA labels on all controls.
- G3 Optional ambient audio (WebAudio synth, OFF by default; capture stinger).

### MV-H · Capture & submission media
- H1 In-app screenshot key (PNG of the canvas) → replaces README hero shots with real-match frames.
- H2 WebM recorder (canvas.captureStream + MediaRecorder) for a ≤60 s demo clip of the guided tour.
- H3 README/media refresh: masterclass stills (capture finale, audit wave, split-screen) + tour clip link.

## 4. Milestones (binary)
- **M-V1** (after MV-F/A/D): modularized arena plays a full replay with follow-cam, particle scent, slam barriers, capture finale — all files ≤150 lines, node smoke test green.
- **M-V2** (after MV-B/C/E): commit rail + audit wave green on honest log, red shatter on the tampered fixture; three views switchable; timeline markers live.
- **M-V3** (after MV-G/H + P1): live-spectate a real localhost league match; tour mode recorded to WebM; README media refreshed.

## 5. Traceability & risks
F12 → M-V1/M-V2 evidence · Nielsen/UX excellence → MV-E/G · Adaptation demo → C3 before/after · R8 → F1. **Risks:** scope creep (cut order if squeezed: G3 → C2 → H2 — never cut MV-B, it is the differentiator); WebGL perf on grader hardware (quality toggle + static fallback retained); live mode depends on P1 (falls back to generator, not blocking).
