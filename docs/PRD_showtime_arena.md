# PRD — Showtime Arena (live spectating · match room · split-screen · guided tour)

| | |
|---|---|
| **Mechanism** | Showtime: the arena stops being a replay theater and becomes the place league matches *happen* — live spectating of a real peer match, a one-click match room, split-screen dual-belief, and a scripted guided tour that records itself |
| **Phase** | P7 (PLAN-PHENOMENAL §2) · builds on P1 runtime (`PeerRuntime`) + P4 masterclass arena (schema v2, module split) |
| **Gates served** | F12 (GUI/replay + demo media) · F14 (league match demonstrably playable) · Coordination rubric axis (PLAN-PHENOMENAL §4: ideas #7, #8, #9, #10, #11, #17) |
| **Hard constraints** | Every file ≤150 lines raw+logical **including JS** (`check_file_lines.py` already covers `viz/*.js`) · zero-build preserved (import-map + vendored Three, no bundler, no new deps) · `viz_server` binds **127.0.0.1 only** — the match room never becomes a remote-code hole |
| **Doc status** | Planning gate — approve before implementation. Tasks: TODO §Phenomenal (T623+) |

Predecessor: `PRD_masterclass_viz.md` established schema v2, the ES-module split (`main/scene/board/agents/scent/barriers/camera_rig/finales/crypto_rail/hud/views/timeline/data/capture`), node tests, and `scripts/viz_server.py` (`/api/game`). This PRD adds LIVE on top without disturbing offline behavior.

---

## 1. Spectate stream — the honest Dec-POMDP feed

The substrate for everything live: `PeerRuntime` emits **own-knowledge frames** — the spectator sees *what the agent knows*, never omniscient truth.

- **SH-1 · Listener hook.** `PeerRuntime.__init__` gains an optional keyword `listener: Callable[[dict], None] | None = None` (default None = zero behavior change). The runtime calls `listener(frame)` once after every `take_turn` return and once after every non-duplicate, non-malformed `handle` outcome (i.e. both halves of a turn cycle). Listener exceptions are swallowed (spectating must never kill a league match).
- **SH-2 · Frame shape** (versioned, own-knowledge only):
  ```json
  {"spectate_schema": 1, "turn": <step_number>, "role": "police|thief",
   "phase": "sent|received", "me": [r, c], "belief": [[..7]..7],
   "known_barriers": [[r,c], ...], "last_hint": "...", "last_intent": null,
   "claims": {"capture_claim": [..]|null, "claim_response": {..}|null,
              "win_claim": {..}|null}, "commit8": "ab12cd34",
   "sub_game": n, "outcome": null|{"result": "...", "winner": "..."},
   "ts": "<iso8601>"}
  ```
  `me` = own position, `belief` = my `decoder.grid` snapshot (rows list-of-lists), `commit8` = first 8 hex chars of my latest sealed record (`SealBook.records()[-1]["commit"]`), `last_hint`/`last_intent` = the *received* hint (intent is unknown for received hints until audit → `null`; own sent intent is NOT emitted, it is sealed).
- **SH-3 · No-truth-leak invariant (normative).** The stream contains **no opponent true position, no opponent belief, no sealed payloads/nonces, no own intent**. A frame is constructible purely from `rt.me`, `rt.belief`, `rt.barriers`, `rt.history[-1]`, claim fields of the wire just processed, and `commit8`. A dedicated test greps every emitted key/value against the opponent's actual trajectory (SH-19).
- **SH-4 · `JsonlListener`.** New `src/cipherchase/sdk/spectate.py` (≤150): `build_frame(rt, phase, wire_or_msg) -> dict` (pure, testable) + `class JsonlListener` — `__call__(frame)` appends one JSON line to `path` (opened append, flushed per line; truncation-tolerant readers per SH-8).
- **SH-5 · Threading.** `SimulationSdk.run_peer(..., listener=None)` → `run_series(..., listener=...)` → each `PeerRuntime(listener=...)`. CLI: `cipherchase peer --spectate <path>` (default off) constructs a `JsonlListener`; the interop capture (SH-16) uses this flag through the existing subprocess launch.

## 2. Server (`scripts/viz_server.py` amendments)

Stays ≤150 or splits a `scripts/viz_match.py` helper (match-thread + URL validation) alongside; both under `check_file_lines.py`.

- **SH-6 · `GET /api/spectate`** — reads the active match's JSONL tail (parse line-by-line; skip a torn final line) → `{"live": true, "frames": [...]}`; `{"live": false, "frames": []}` when no match ran. `Cache-Control: no-store` like `/api/game`.
- **SH-7 · `POST /api/match`** — body `{"opponent_url": "...", "role": "police|thief"}`. Validates: role in the pair; URL parses to scheme `http|https` + non-empty host + path ending `/mcp` (shape check only — no fetch). On pass: clone the role's config with `opponent_url` overridden, spawn `SimulationSdk.run_peer` in a **daemon thread** with a fresh `JsonlListener` (spool file under the scratch/logs dir), respond `{"ok": true, "stream": "/api/spectate"}`. **One match at a time**: a second POST while the thread is alive → HTTP 409 `{"ok": false, "error": "match already running"}`. Bad input → 400; internal failure → 500; **all errors are JSON bodies**, never HTML tracebacks.
- **SH-8 · Bind + safety.** Server stays `127.0.0.1`-bound (already true — a requirement now, with a test). The match thread is daemonized so Ctrl-C on the server never hangs; a dead/unreachable opponent simply lets `PeerRuntime`'s own watchdog produce a `timeout` result, which reaches the stream as a final `outcome` frame — the server never blocks on it.

## 3. Arena LIVE mode (`viz/js/live.js` + minimal `main.js` wiring)

- **SH-9 · Live poller.** `live.js` (≤150, DOM+fetch only, no three.js): polls `/api/spectate` every **800 ms**, keeps a monotone frame list (append only frames beyond the last seen `(sub_game, turn, phase)`), exposes `onFrames(cb)` / `start()` / `stop()`. Pure merge/parse helpers exported for node tests (SH-20).
- **SH-10 · Schema mapping.** A pure `spectateToViz(frames)` maps spectate frames into the existing schema-v2 frame shape the renderer already consumes: own token = the frame's `me` (rendered solid), opponent = **ghost at belief argmax** (exact reuse of Cop-view semantics in `views.js` — own-knowledge renders as the cop-view-like mode), `belief` = floor, `barriers` = `known_barriers`, `hint`/`intent` from `last_hint`; no `records`/`verdicts` → the crypto rail shows accumulating `commit8` chips as *sealed, unverifiable-yet* (audit wave only after the final `outcome` frame arrives). Truth view is disabled in LIVE (there is no truth to show — that IS the demo line).
- **SH-11 · LIVE presentation.** While polling: auto-follow the stream head (scrub pinned to the newest frame unless the user scrubs back), a pulsing **LIVE** chip in the HUD; scrubbing back pauses follow, jumping to head resumes it. On the final `outcome` frame: LIVE chip → "ENDED", normal finale path.
- **SH-12 · Match room panel.** A DOM form (in `index.html` + `live.js` handlers, no framework): opponent URL input + role select + **Start match** button → `POST /api/match` → on `{ok}` switch the arena to LIVE mode against `/api/spectate`. Errors (400/409/500, dead URL timeouts) render as a dismissible error chip in the panel — never a broken arena.
- **SH-13 · Offline degradation.** On boot the panel probes `/api/match` availability (an OPTIONS/failed fetch or the `/api/game` 404 path); when the arena is opened from disk or a server without match support, the panel is hidden and everything else behaves exactly as today (existing suite + arena unchanged offline — acceptance-tested).

## 4. Split-screen dual-belief (`viz/js/split.js`)

- **SH-14 · Replay-only toggle, key `4`.** Two viewports via `renderer.setScissorTest(true)` + `setViewport/setScissor` ×2: **left = the cop's belief world** (view-1 state), **right = the thief's** (view-2 state), one shared timeline/transport. Approach (spec'd, not open): **one scene, double-rendered per tick** — for each half, apply that side's view state (`views.apply` with the forced view + belief floor swap), render into the half's scissor rect with the shared camera (mirrored rig target). No second scene graph, no cloned geometry; cost = 2 draw passes, acceptable within the 60 fps/M2 budget (quality toggle still applies). Key `4` in LIVE is a no-op (only one belief exists).
- **SH-15 · HUD adaptation.** In split mode the HUD shows both belief-error sparks (cop mag, thief cyan) and suppresses the single-view ghost hints; pressing `1/2/3` exits split. `prefers-reduced-motion` unaffected (split is static layout, not motion).

## 5. Guided tour (`viz/js/tour.js`) + recorder (`viz/js/recorder.js`)

- **SH-16 · Tour.** `T` key starts a scripted ~25 s sequence on the honest fixture: camera-path keyframes (position/target/time tuples, eased) + a caption card per beat — **board → scent wake → belief floor → sealed-chips rail → audit wave finale**. `Esc` cancels and restores user camera/controls. `prefers-reduced-motion`: no camera flight — the caption sequence plays as static cards over the normal view. Tour drives the same transport (`setTurn`) — no parallel state.
- **SH-17 · WebM recording.** `recorder.js`: `canvas.captureStream(30)` + `MediaRecorder` (`video/webm`) armed by the tour (or `R`); on tour end it stops and triggers a download of `tour.webm`. **Manual publishing step (documented in README + this PRD, run by hand, never in CI):** commit the clip as `docs/media/tour.webm`, derive the README hero GIF via
  `ffmpeg -i docs/media/tour.webm -vf "fps=12,scale=720:-1:flags=lanczos" -loop 0 docs/media/tour.gif`
  and embed both in the README (idea #17).

## 6. Reference-match fixture — "the day we played the lecturer's peer"

- **SH-18 · Capture + bundle.** The interop launch path (`tests/interop/test_vs_reference.py` runs `cipherchase peer` as a subprocess) gains an env-gated hook: when `CIPHERCHASE_SPECTATE_OUT=<path>` is set (manual run only, alongside `CIPHERCHASE_INTEROP=1`), the test appends `--spectate <path>` to our peer's argv. A tiny converter (`scripts/make_reference_replay.py` or a `make_replay_data.py` mode, ≤150) turns the captured JSONL into `viz/replay_reference_match.json` (spectate schema, bundled). The arena's fixture control grows a third **"vs Reference"** option that loads it through the same `spectateToViz` mapping — replaying an actual foreign-peer match inside the arena. Never a CI dependency; the committed fixture is the artifact.

## 7. Acceptance (binary)

1. A localhost league match **started from the match room** (two local peers) renders live in the arena to completion, ending with the outcome banner.
2. The spectate JSONL of that match contains **zero opponent ground truth** (SH-19 test green; manual grep of the file agrees).
3. Split-screen (`4`) works on both bundled replays; `1/2/3` exits it; LIVE ignores it.
4. Tour plays end-to-end on the honest fixture, `Esc` cancels, and a recorded `tour.webm` downloads; `docs/media/tour.webm` + `tour.gif` committed and embedded in the README.
5. `viz/replay_reference_match.json` is bundled and loads via the "vs Reference" control.
6. Node tests extended: `live.js` merge/parse + `spectateToViz` covered; python suite covers listener frames + both endpoints.
7. `check_file_lines.py` green — every touched/new file (py + js) ≤150 raw+logical.
8. With the server absent (file:// or `/api/match` 404), the arena behaves **exactly as today**: existing pytest + node suites pass unmodified, match panel hidden.

## 8. TDD / test plan, edge cases, risks, traceability

**Python (pytest, mocked transport — grader-safe, no sockets):**
- `build_frame` shape test: every SH-2 key present, `belief` is 7×7, `commit8` length 8.
- **SH-19 · No-truth-leak test (a requirement, not just a test):** run a full loopback game with listeners on both runtimes; assert no cop frame ever contains the thief's true position (and vice versa) in any field, and no `nonce`/full payload appears.
- Listener call cadence: exactly one frame per send + one per processed receive; malformed/duplicate wires emit nothing; a raising listener does not break `run()`.
- `JsonlListener`: appends valid JSON lines; reader skips a torn final line (simulate truncation).
- Server endpoints with a **fake runtime** (monkeypatched `run_peer` writing canned frames): `/api/spectate` empty→live transitions; `/api/match` happy path, bad URL → 400, second POST → 409, spawned thread is daemon; error bodies are JSON.

**JS (`node --test`, extends `viz/test`) — SH-20:** frame merge monotonicity + torn-tail skip in `live.js`; `spectateToViz` mapping (ghost at belief argmax, no thief coordinate invented); tour keyframe interpolation clamps.

**Manual checklist:** match room vs a second local peer; kill the opponent mid-match → watchdog `timeout` frame → clean "ENDED"; dead opponent URL → error chip; record + convert media.

**Edge cases:** stream truncation mid-line (skip) · match already running (409, arena chip) · dead/bogus opponent URL (shape-reject or watchdog result, never a hang) · reduced-motion tour · LIVE with zero frames yet (empty-state message, keep polling).

**Risks:** match-room abuse → localhost bind + URL shape validation + no config paths from the client (mitigated, tested) · MediaRecorder codec variance across browsers → webm-only, manual step, never graded-path · split-screen perf → double-pass budget under the existing quality toggle · scope → PLAN cut order (GIF pass → split-screen → tour/WebM → **never cut** spectate + match room).

**Traceability:** SH-1..5 → PLAN idea #8 · SH-6..13 → #7 · SH-14..15 → #9 (T609) · SH-16..17 → #10 (T618/T621) + #17 · SH-18 → #11 · F12/F14 evidence → acceptance 1/4/5 · R8 → acceptance 7.
