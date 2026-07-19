# PLAN-PHENOMENAL — Beyond Submission-Grade (P6–P8)

| | |
|---|---|
| **Goal** | Raise the build from "impressive" to **phenomenal**: dominate the last weak number, close the loop on the course's own theme (language-in-the-decision-loop), make the demo unforgettable, and make integrity *exhaustively* proven |
| **Date** | 2026-07-19 · deadline Aug 12 (all of this is cuttable; league logistics stay P3 and are NEVER blocked by it) |
| **Basis** | Championship state: 40 commits, 266 tests + interop pair, 100% cov, vs-reference series verified, cop 26.7/85–100%, masterclass arena v2 |
| **Doc status** | Planning gate — approve before implementation. Child PRDs: `PRD_apex_brain.md`, `PRD_showtime_arena.md`, `PRD_ironclad.md`. Tasks: TODO §Phenomenal (T623+) |

---

## 1. The full idea inventory (explored, then triaged)

Eighteen candidates were explored. Verdicts: **BUILD** (in a child PRD), **CUT** (honestly not worth it), or **DONE-ENOUGH**.

| # | Idea | Verdict | Why |
|---|---|---|---|
| 1 | **Opponent-model best-response cop** — we *know* evader decision rules; simulate the thief's reply to each of our candidate (move, barrier) actions and pick the action minimizing its best escape | **BUILD** (P6) | The decoder gives exact position; spending it on greedy chase wastes it. Predict-and-intercept is a grade-band claim |
| 2 | **Endgame solver** — once the believed thief is cornered (wall-dist ≤ 2, gap ≤ 4), run exact depth-bounded alpha-beta over the TRUE tiny state space → provably forced capture | **BUILD** (P6) | "The endgame is solved" is the strongest sentence available to the strategy chapter; 49-cell board makes it cheap |
| 3 | **Bluff-aware belief** — hints finally enter the DECISION loop: track the opponent's per-game hint truthfulness; when historically honest, nudge belief toward hint content; when a liar, invert or ignore | **BUILD** (P6) | The course is *Orchestration of AI agents*; today our NL layer is decorative in decisions. This closes F6 into the brain — the most on-theme upgrade possible |
| 4 | **Strategic deception** — OUR hint/intent chosen adversarially by the brain (lie about direction precisely when the cop is close), still template-text, still F8-legal (algorithm picks the words; LLM never picks the move) | **BUILD** (P6) | Symmetric counterpart of #3; together they make the language layer a real weapon |
| 5 | **Q-learning + learning curves** — tabular, feature-state (relative offset class, wall dists, budget), trained offline vs archetypes, policy shipped as a config-seam brain, curves in the notebook | **BUILD** (P6) | Rubric names RL curves explicitly; the "engineering vs learning, measured" chart is the professor chart |
| 6 | **Tournament + Elo + confidence intervals** — round-robin ALL brains (ours + archetypes), Elo ladder + Wilson 95% CIs on capture rates, in benchmark_lab + notebook | **BUILD** (P6) | Turns our claims into statistics; cheap on top of the existing lab |
| 7 | **Match room** — type an opponent URL in the arena → server spawns `run_peer` → the live match renders in 3D as it plays | **BUILD** (P7) | Makes the scariest logistics step (league match) a one-click demo; jaw-drop during the defense |
| 8 | **Live-spectate stream** — PeerRuntime emits frames (own position, belief, known barriers, claims) to a JSONL the arena tails | **BUILD** (P7) | The substrate for #7; ALSO the honest Dec-POMDP spectacle: you spectate *what our agent knows*, not omniscient truth |
| 9 | **Split-screen dual-belief** (T609) | **BUILD** (P7) | Two viewports, one timeline — the epistemics money shot |
| 10 | **Guided tour + WebM demo clip** (T618/T621) | **BUILD** (P7) | 25 s scripted camera explainer; the README's moving hero |
| 11 | **"The day we played the reference" fixture** — capture a real vs-reference match's spectate stream as a bundled third replay | **BUILD** (P7) | Replaying an actual foreign-peer match inside the arena = Coordination made visible |
| 12 | **Exhaustive tamper sweep** — flip EVERY record's every field (and single hex chars of commits) in the sample log; assert the audit catches 100% | **BUILD** (P8) | "All N mutations caught" is a one-line Integrity proof no prose can match |
| 13 | **Property-based tests (hypothesis)** — ∀-payload crypto round-trip, belief normalization invariants, board legality, lenient-parse fuzz on TurnMessage/turn_handler (never crashes) | **BUILD** (P8) | Depth-of-rigor signal; catches real edge cases cheaply |
| 14 | **Golden wire transcripts** (T518) — blessed loopback run recorded; fast replay test pins every byte shape | **BUILD** (P8) | The every-commit interop tripwire's deterministic twin |
| 15 | Ambient audio (T616) | **CUT** | Wow-per-effort too low; risks kitsch; keyboard `M` stub only if trivially free |
| 16 | Decoder vectorization / numpy | **CUT** | 7 ms/decision on a 30 s budget — solving a non-problem, adds a dependency |
| 17 | README GIF/badges/diagrams pass | **BUILD** (P7, small) | Hero GIF from the tour recording + CI badge once repos exist |
| 18 | Multi-sub-game offline series artifacts | **DONE-ENOUGH** | Live series already produces per-sub-game summaries; offline single-game proof suffices for the grader |

## 2. The three tracks

### P6 — APEX BRAIN (`PRD_apex_brain.md`) — the graded core, again
One new brain, one trained brain, one belief upgrade, and statistics:
- **`ApexCop`** = layered controller: (L1) ScentDecoder belief (exists) → (L2) **best-response search**: for each of our (move, barrier) candidates, predict the evader's reply from its own scoring rule (exact vs deterministic archetypes; distribution over near-ties vs our seeded EvaderV2) and minimize its escape value; → (L3) **endgame solver**: trigger on (wall-dist ≤ 2 ∧ gap ≤ 4 ∧ decoder-locked), exact alpha-beta (depth ≈ 8, 5 moves × ≤4 barrier candidates, memoized) on true positions — returns a *forced-capture line* or falls back to L2.
- **Bluff-aware belief**: per-opponent honesty tracker (Beta prior over "hint was true"); hint content parsed against template banks (we authored them — parseable by construction); belief nudge weight ∝ P(honest), sign-inverted for established liars. Fail-safe: weight caps small; a `bluff_weight=0` config kills it.
- **Strategic deception**: cop lies about heading exactly when gap ≤ 3 (maximum information value); thief lies about direction when cornered. Intent still sealed + audited (F6 intact).
- **`QBrain`**: tabular Q on features `(sign(Δr), sign(Δc), |Δr|+|Δc| bucket, wall-dist bucket, barriers-left bucket)`; ε-greedy; trained by `scripts/train_qbrain.py` vs archetype mix (seeded, ≤5 min wall); policy JSON under `analysis/`; loads via the existing seam. Notebook gets **learning curves** + the engineering-vs-learning comparison.
- **Statistics**: benchmark_lab grows Wilson 95% CIs + a round-robin **Elo ladder**; notebook + RESEARCH-REPORT updated.
- **Acceptance (measured, honest):** vs EvaderV2 ≥ 55% (from 23.3), vs ThiefBrain ≥ 55%, archetypes ≥ 95%, endgame-solver forced-capture proof test, thief survival vs ApexCop reported (whatever it is — our thief's number stays honest), per-decision ≤ 50 ms offline / well inside 30 s live.

### P7 — SHOWTIME (`PRD_showtime_arena.md`) — the demo nobody forgets
- **Spectate stream**: `PeerRuntime` gains an optional `listener(frame)` writing JSONL (own-knowledge frames: my position, belief matrix, known barriers, claims, hints, rail commits); `viz_server` gains `/api/spectate` (tail) + the arena a **LIVE mode** (auto-follows the stream head, "LIVE" chip).
- **Match room**: arena panel → enter opponent URL + role → `POST /api/match` → server spawns `run_peer` in a thread with the listener attached → the real match renders live; works identically for localhost rehearsal and real ngrok league games.
- **Split-screen dual-belief** for replays (both sides' beliefs, one timeline) — offline replays carry both matrices already (schema v2).
- **Guided tour**: scripted 25 s camera + captions sequence (board → scent → belief → sealed chips → audit wave); `T` key; **WebM recorder** captures it → `docs/media/tour.webm` + a GIF hero for the README.
- **Third fixture**: a captured real vs-reference spectate stream bundled as `replay_reference_match.json` — "replay the day we played the lecturer's peer."
- **Acceptance:** a localhost league match spectates live end-to-end from the match room; tour records ≤ 60 s; split-screen ships; all files still ≤ 150; node tests extended.

### P8 — IRONCLAD (`PRD_ironclad.md`) — rigor that ends arguments
- **Exhaustive tamper sweep** test: for the committed sample log, mutate every record's every payload field + nonce + each commit hex char class → `audit_records` catches **100%**; the count lands in the README ("N mutations, N caught").
- **Hypothesis property tests** (dev-dep): crypto seal/verify ∀ JSON-able payloads; canonical_json determinism; BeliefGrid Σ=1 invariant under arbitrary op sequences; board legality closure; `TurnMessage.from_dict` + `turn_handler.process` never raise on arbitrary dicts (fuzz).
- **Golden transcripts** (T518): blessed loopback series recorded to `tests/interop/golden/`; fast tests replay every message through OUR parser and (when present) the reference's strict parser.
- Also sweeps the leftover guard tasks: dead-config-keys test (T430), doc-truth CLI test (T463), PLAN-inventory test (T465).
- **Acceptance:** all new suites green in CI; coverage stays 100%; sweep count ≥ 500 mutations, 0 escapes.

## 3. Phasing & cut order (deadline-safe)

| Phase | Days | Cut order under pressure |
|---|---|---|
| P6 Apex brain | ~3 | Q-learning → bluff-aware belief → (never cut) best-response + endgame + stats |
| P7 Showtime | ~2.5 | audio-stub → GIF pass → split-screen → tour/WebM → (never cut) spectate + match room |
| P8 Ironclad | ~1 | golden transcripts → property tests → (never cut) tamper sweep |

League logistics (P3) and submission (P5) remain the critical path and interrupt ANY of this the moment opponents/repos are ready. Everything here lands behind the existing seams — the shipped champion config only changes if ApexCop's measured numbers beat it.

## 4. Traceability
Adaptation → P6 (#1–6) · Coordination → P7 (#7–8, #11) · Integrity → P8 (#12–14) + P6 #3/#4 (language vs audit tension made productive) · Architecture → every feature lands behind existing seams (BrainBase, listener hook, fixture loader) · Excellence rubric → RL curves (#5), notebook/statistics (#6), UI polish (#9–10).

## 5. Risks
Endgame search blow-up → hard depth/node caps + fallback to L2 (never stalls a live turn) · RL training time → capped episodes, seeded, offline-only artifact · bluff-belief backfires vs adversarial liars → capped weight, config kill-switch, measured before default-on · match-room security → localhost-bind only, no remote code, URL validated · scope creep → the cut order above is contractual.
