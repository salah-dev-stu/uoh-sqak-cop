# PLAN-CHAMPIONSHIP — From "Complete" to First Place

| | |
|---|---|
| **Goal** | **League first place = grade 100** (last = 75) + flawless four metrics (Coordination · Adaptation · Integrity · Architecture) + teardown-proof code quality |
| **Date** | 2026-07-19 · **24 days to the strict deadline (Wed 2026-08-12 23:59)** |
| **Basis** | Four full-project audits (source line-level, protocol/league-readiness, docs-vs-code drift, competitive strategy lab with 120-game experiment matrices) — every claim below is a measured finding, not a guess |
| **Doc status** | Planning gate — approve before implementation. Child PRDs: `PRD_league_runtime.md`, `PRD_winning_brain.md`, `PRD_integrity_hardening.md`. Tasks: `docs/TODO.md` §Championship (T406+) |

---

## 1. The math of first place

League points per opponent (we play BOTH roles vs each team):

| Outcome | Points |
|---|---|
| Our cop **captures** their thief | **20** |
| Our thief **survives** their cop | **10** |
| Our cop fails (their thief survives) | 5 |
| Our thief caught | 5 |
| **Diversity** — first valid match vs a NEW group | **+10** |
| Opponent crashes / hangs / illegal move | **technical win for us** |

**Winning line:** `capture(20) + survive(10) + diversity(10) = 40/opponent` vs a realistic `15–20` for a mid-table team. Multiply across the max distinct opponents (≤10 games, min 2 to pass). Three levers, in order of leverage:

1. **L1 — Play at all.** No live P2P runtime today = zero league games = fail. Highest priority by definition.
2. **L2 — Win both roles.** Cop must *capture* (currently 0% vs any belief-using thief); thief must *survive* (already ≥97.5%, harden it).
3. **L3 — Never lose technically + harvest technical wins.** Rock-solid timeouts/validation means opponent bugs become our points. Student-league reality: many matches are decided by crashes, not chess.

## 2. Audit verdict — what stands between us and 100

### 2.1 🔴 BLOCKER: no live match capability (L1)
The audited truth: `Orchestrator`, `McpTransport`, `build_peer_server`, `handshake`, `Watchdog`, `Deadline`, `StateMachine` have **zero production callers**. The CLI has no `peer` command; the SDK has no `run_peer`/`run_series` (docs promise both). Worse, the **reference wire choreography** (what every opponent will speak, extracted from the lecturer's repo) differs from our design:

- Per sub-game: mutual `negotiate` with `{terms, nonce, signature, identity}` → verify byte-equal terms → **thief moves first** → strict alternation where **one turn = ONE sealed `TurnMessage`** (`commit` seals `{step,state,position,move,intent,…}`; **no per-turn reveal — nonce and move stay hidden until the end-game audit**) → claims ride on turns (`capture_claim` every cop move, honest `claim_response` next thief turn, `win_claim` at survival) → mutual `submit_audit` re-verifies every record → series driver alternates roles per sub-game.
- **Our current per-turn commit→reveal flow is wrong for interop** (it leaks the move mid-game and its extra keys would crash a strict reference parser). It must be replaced, not extended.
- Source-verified breaking details (reference code wins over any summary): `submit_audit`'s tool parameter is named **`payload`** (ours declares `message` — instant crash both directions today); reference `TurnMessage.from_dict` is strict `cls(**data)` (our extra `move`/`intent` keys crash it); negotiation happens **per sub-game**; `opponent_url` requires a **`/mcp`** path suffix; the reference audit is **hash-only**; `capture_claim` rides only on police move-turns; a caught thief sends a final "You got me." turn; timeout results skip the audit.
- → Full spec + gap list in **`PRD_league_runtime.md`**. Includes the decisive proof: an **interop test that plays OUR peer against the actual reference peer locally** (we have it in-repo) — no other team will be able to show that.

### 2.2 🔴 BLOCKER: the cop cannot win (L2)
Strategy-lab matrices (N=120/cell, randomized starts):

| capture-rate % | ThiefBrain | NaiveEdge | Random | Still |
|---|---|---|---|---|
| PoliceBrain (ours) | **0.0** | **0.0** | 30.8 | 14.2 |
| PoliceExpectimax | **0.0** | **0.0** | 37.5 | 9.2 |

Diagnosed root causes (measured): **(a)** belief error averages 3.46 cells — the scent field saturates into a plateau and the cop chases a *phantom trail*, not the thief; **(b)** greedy Manhattan pursuit can never corner an evader (move parity — distance actually *grows* late-game); **(c)** 10/14 barriers squandered far from the thief, **zero boxed-in captures ever**. Oracle ablation: perfect information alone lifts NaiveEdge to only 22.5% — *the chase policy itself must change*.

The lab's winning recipe (only probe to beat a real evader): **scent-delta belief decoding** (`Δ = τ_t − (1−ρ)·τ_{t−1}` → argmax IS the thief's current cell — near-oracle accuracy from legal information) + **herd-to-corner pursuit** + **wall-on-escape-side barrier discipline** (capture = boxing, never co-location). Our thief additionally gets corner-avoidance + seeded tie-randomization (anti-predictor). Targets: **≥90% capture vs naive archetypes, ≥30% vs strong evaders, ≥95% thief survival**, all proven by a committed benchmark harness. → **`PRD_winning_brain.md`**.

### 2.3 🟡 INTEGRITY & RUBRIC LANDMINES (teardown-proof pass)
The pedantic-grader list (top of ~40 audit findings):

1. **Sealed payloads commit `barriers: []` every step** — game_loop never threads placed barriers into `OwnState`, so our own audit validates a wrong board. A real integrity bug in the Integrity project.
2. **The runnable path bypasses the gatekeeper entirely** (R3: `cli → sdk → game_loop` constructs no `ApiGatekeeper`; `_http_caller` ungated; provider gate optional).
3. **`intent="lie"` / hints never occur in any real run** — TrashTalk isn't wired into the game loop (F6 hollow).
4. **`check_compatible` never called at startup** (R6 decorative).
5. **~10 config keys read by nothing** (`belief.alpha`, `rpc_timeout_s`, `play.seed`, `[llm]`, `[gui]`, `[paths]`, `[email]` subject/enabled, gatekeeper `concurrent/queue_depth`…) while code literals shadow them (R11/R4).
6. **Docs promise ghost modules** (`peer/runtime.py`, `sdk/series.py`, `talk_providers.py`, `qlearning.py`, GUI live modules…), `run_peer` commands that don't parse, README says 195 tests (now 205), auto-email claimed but not wired, the emitted `declaration_*.json` lacks the signed hardware/LLM/git-commit body that `peer/declaration.py` builds.
7. Engine duplicated in `make_replay_data.py`; `"r,c"` codec at 4+ sites (R2). `viz/index.html` is 265 lines and outside the ≤150 checker's `*.py` glob (defend or split). *(RESOLVED in P4: split into 15 ES modules; index.html is now 80 lines and `check_file_lines.py` covers `viz/` js+html.)*
8. game_loop quirks: fresh deposit decayed same turn; thief sees the cop's true position (breaks Dec-POMDP realism — fix with the same delta-belief the cop gets).

Every item → a task; the principle is **"docs tell the truth, the truth is impressive."** → **`PRD_integrity_hardening.md`**.

### 2.4 🟢 Assets already in the bank
205 tests / 100% cov / ruff 0 / ≤150 / 26 commits · frozen byte-level crypto with golden vectors · physical-claim audit · strong thief · working 4-artifact reporting + sample run · 3D arena showpiece · full docs suite · Py-3.13 CI.

## 3. Phased roadmap (24 days, overlapping tracks)

| Phase | Dates | Deliverable | Exit criterion (binary) |
|---|---|---|---|
| **P0 Integrity hardening** | Jul 19–24 | Fix committed-barriers bug; gatekeeper wired into the real path; TrashTalk/intent live in-game; startup version check; config keys actually read; doc-truth reconciliation pass | Audit re-run finds 0 of the §2.3 items; docs contain no false claim |
| **P1 League runtime** | Jul 21–29 | Reference-choreography peer: sealed single-message turns, thief-first alternation, claims, negotiate/terms alignment, `PeerRuntime`, `sdk/series` + role swap, audit exchange, `cipherchase peer --role` CLI, timeout→technical win | **Our peer completes a full series vs the ACTUAL reference peer on localhost, audits Verified-OK both sides** |
| **P2 Winning brain** | Jul 23–Aug 2 | Delta-belief decoder, HerderCop + wall discipline, thief hardening, committed benchmark lab + win-rate matrices in the research report | ≥90% capture vs {Naive, Random, Still}, ≥30% vs strong evader, ≥95% thief survival, benchmarks reproducible via one command |
| **P3 League ops** | Aug 1–8 | ngrok cross-machine smoke; opponent kit (1-page interop contract + our tunnel checklist to send other teams); **play ≥2 real matches** (D4); truthful declarations; auto-email live | ≥2 valid matches vs different groups completed, artifacts mutually emailed |
| **P4 Excellence & showcase** | Aug 3–9 | Analysis notebook (benchmark + sensitivity curves), ISO/IEC 25010 map, Nielsen pass, cost/RPM tables, 3D arena capture-cam + live-match replay, README theater, Prompt Book | Excellence checklist §9–16 fully ticked; README screenshots of a REAL league match |
| **P5 Submission** | Aug 8–12 | Two repos published + cross-linked, `v1.0-submission` tag, PDF `ex<NN>`, Moodle ×2, final secret scan, 2-day buffer | Both repos tagged & accessible; both members submitted before Aug 12 23:59 |

Dependencies: P1 unblocks P3; P2 is independent (pure domain/strategy); P0 first because every later diff builds on truthful foundations. **User-owned (cannot be delegated): D4 opponent outreach starts NOW (P3 needs partners scheduled), D7 PDF number, GitHub repo creation, Gmail OAuth consent, Moodle.**

## 4. Grading-lens traceability

| Metric / rubric | Where this plan lands the points |
|---|---|
| **Coordination** | P1: real P2P choreography interoperating with a *foreign* implementation, proven by the vs-reference test + ≥2 live matches |
| **Adaptation** | P2: belief that decodes scent deltas each turn, herding that adapts to thief position class, per-sub-game role swap; benchmark lab shows measured improvement over baseline (0%→90%) |
| **Integrity** | P0: barriers-in-payload fix, live intent/bluff with truthful board, audit + physical audit exercised in every real match; already-frozen crypto |
| **Architecture** | Seam-swappable brains (baseline kept as `police_heuristic`, championship brain added beside it), gatekeeper actually load-bearing, docs≡code |
| **Computational fairness** | Everything stays pure-Python, 0 tokens, ~40 ms/game on an 8 GB M2 — measured in the research report |
| **R1–R13** | P0 closes every audit finding; CI gains `--frozen` sync + self-match smoke step |
| **F1–F14** | F-gaps closed by P1 (F1/F9 live), P0 (F6 real bluffs, F11 auto-email, F5 signed declaration in artifacts), P3 (F13/F14 live matches) |

## 5. Risk register

| Risk | L×I | Mitigation |
|---|---|---|
| No opponents found (D4) | M×**Critical** | Outreach kit ready in P3 week 1; lecturer/class channels; fallback = documented live cross-machine self-league via ngrok + evidence we sought partners |
| Choreography misread → interop fails live | M×High | The vs-reference interop test IS the rehearsal; opponent kit pins byte-level contract; keep a strict+lenient parser (accept unknown fields, never crash) |
| Brain rework destabilizes green suite | M×M | New brains as NEW seam classes; baseline untouched; benchmark harness gates regressions |
| ≤150/coverage erosion under new code | M×M | Same TDD cadence; line-check in CI already; split modules pre-emptively |
| Time overrun | M×High | P0–P2 are internal and start now; P5 has a 2-day buffer; excellence (P4) is cuttable, league (P1/P3) is not |

## 6. Definition of FIRST PLACE done
≥2 valid league matches (max distinct opponents we can schedule) with our cop capturing and thief surviving · zero technical losses on our side · both repos tagged, docs≡code, audits clean · benchmark evidence in-repo · every F-gate demonstrably LIVE, not decorative.
