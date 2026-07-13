# PRD — CipherChase: Distributed Cops-and-Robbers over a Peer-to-Peer Network

| | |
|---|---|
| **Project** | CipherChase (Police & Thief P2P) — Final Project, Course 203.3763 |
| **Course** | Orchestration of AI Agents · University of Haifa · Spring 2026 · Dr. Yoram Segal |
| **Team** | `uoh-sqak` — Salah Qadah (ID 323039974) + Andalus Kalash (ID 211435797) |
| **Package** | `cipherchase` (one layered codebase → **two** GitHub repos: `uoh-sqak-cop`, `uoh-sqak-thief`, role-swapped by config) |
| **Version** | 1.00 (single-sourced in `shared/version.py` + config `"version"`) |
| **Doc status** | **Gate-1 draft** — approve before PLAN/TODO/per-mechanism PRDs |
| **Deadline** | **Wed 2026-08-12 23:59 Asia/Jerusalem — STRICT** |
| **Spec** | `materials/police_thief_p2p.pdf` v3.0.0 (Appendix ו = mandatory numbers) + `software_submission_guidelines-V3.pdf` (rubric R1–R13) |

> **Naming note:** "CipherChase" / package `cipherchase` and the repo names above are a proposal — trivially renameable at this doc stage. Flag if you want a different brand.

---

## 1. Vision & problem statement

Build a **peer-to-peer** cops-and-robbers chase between **two mutually-distrustful autonomous agents** — a Cop and a Thief — with **no central server and no judge** ("אין שופט"). Each agent is *simultaneously a FastMCP server and client*, plays on a **7×7 grid** under **partial observation** (Dec-POMDP, n=2), and exchanges **free natural-language hints that may deliberately lie**. Because no referee exists, fairness is enforced **cryptographically** (Commit-Reveal + SHA-256 + end-of-game mutual audit): any tamper or false physical claim yields an automatic **0/0** by mathematics, not judgment.

The intellectual core — and the graded deliverable — is an **algorithmic move brain** (Bayesian belief + heuristic pursuit/evasion). The game runs to completion with **zero LLM tokens**; the LLM is confined to writing bluff text. The system is evaluated on **systems engineering** across four metrics — **Coordination, Adaptation, Integrity, Architecture** — plus **Computational Fairness** (a clever, cheap algorithm on a modest machine beats brute force). It is **not** graded primarily on winning.

## 2. Goals & non-goals

### 2.1 Goals (in priority order)
1. **G1 — Correct, complete, fair game engine** that satisfies all 14 final-project gates (F1–F14) and the software rubric (R1–R13).
2. **G2 — A graded strategy brain** (pure-Python heuristic baseline) that plays both roles competently and is swappable via a clean seam.
3. **G3 — Grader-runnable offline** with no keys, no live opponent: mocked LLM + MCP transport + Gmail, plus a committed real sample run (4 JSON artifacts + GUI/Replay screenshots).
4. **G4 — Two cross-linked public GitHub repos**, `v1.0-submission` tagged, ≥2 valid league games vs different groups.
5. **G5 — Excellence band ("best impressive"):** OAT sensitivity analysis + analysis notebook, Nielsen-heuristics UI pass, cost/token tables, ISO/IEC 25010 mapping, and an optional Q-learning brain with learning curves.

### 2.2 Non-goals (explicitly out of scope)
- **N1** — Any central server, judge, matchmaker, or shared memory between Cop and Thief (would be **disqualification**).
- **N2** — LLM deciding or influencing a move (LLM is bluff-text only).
- **N3** — Winning the league as a primary objective (self-grade = code quality only).
- **N4** — Novel cryptography; we use standard SHA-256 Commit-Reveal exactly as specified.
- **N5** — Persisting a trained RL policy as a hard dependency; Q-learning is an *optional* extension gated behind config, never on the critical path.

## 3. Users & stakeholders

| Stakeholder | Need |
|---|---|
| **Cop agent (process)** | Chase, place barriers, box-in the thief; keep belief map; commit/reveal/audit honestly. |
| **Thief agent (process)** | Evade via scent gradient + belief; emit scent; commit/reveal/audit honestly. |
| **Opponent teams** | A byte-compatible interop contract (MCP tools, message shapes, commit formula, signed `game.json`). |
| **Grader (Dr. Segal)** | Clone → `uv sync` → run tests offline (no keys/opponent) → inspect a real sample run + artifacts + screenshots + docs. |
| **Team `uoh-sqak`** | Maintainable, ≤150-line, TDD'd codebase they can extend and defend at the pedantic-teardown self-grade (85). |

## 4. Locked decisions (D1–D7)

| # | Decision | Resolution |
|---|---|---|
| D1 | Codebase → repos | One layered `cipherchase` package developed once → published to **two** repos, cross-linked, role selected by `--role`/config. |
| D2 | LLM / trash-talk | Provider **seam**: `template` (0-token **default & test path**) · `claude_cli` (HW6 subscription) · `ollama` (local M2) · `claude_api` (Haiku). LLM never decides a move. |
| D3 | Strategy | **Heuristic baseline first** (Bayes belief + Manhattan + cop box-in); expectimax + Q-learning as plug-in extensions. |
| D4 | Opponents | **Salah arranges ≥2 different partner groups**; blocks league (F14), not the grade. *(external action)* |
| D5 | Deploy | **ngrok** primary + **Localtonet** documented fallback (ADR, F13); **localhost + FakeTransport** for all tests. |
| D6 | HW6 reuse | Reuse `ApiGatekeeper`, `GmailApiSender` (real `gmail.send` OAuth), `ClaudeCliProvider`, `check_file_lines.py`, Py-3.13 `ci.yml`. |
| D7 | Submission PDF number | `uoh-sqak-ex<NN>.pdf` — **`<CONFIRM-NN>` pending** (Salah checks `uoh-rl07-final-project-2026.docx`/Moodle `id=294462`). |

## 5. Functional requirements

Each requirement has an ID (used for TODO traceability) and maps to the gate(s) it satisfies. Mandatory numbers come from Appendix ו and are **config-driven, never hardcoded** (NFR-11).

### FR-A · Base game logic *(Stage 1 · Ch3 · → F-none-yet, foundation)*
- **FR-A1** 7×7 grid; thief start `[3,3]`, cop start `[0,0]`; axis origin/index from config.
- **FR-A2** Moves = `N/S/E/W/STAY` (orthogonal only); reject diagonal/out-of-bounds/through-barrier as **illegal** (illegal move → opponent rejects → technical loss).
- **FR-A3** Cop places ≤ `max_barriers` (14) barriers, one adjacent cell/turn, **declared truthfully**; barrier on thief's cell = capture.
- **FR-A4** Capture (co-location or fully boxed-in thief) and survival (`survival_threshold`=35 turns, `max_moves`=35) detection.
- **FR-A5** Scoring from config: capture cop 20 / thief 5; survival cop 5 / thief 10; tie 2; technical_loss 0/0; diversity_reward 10.

### FR-B · P2P MCP infrastructure *(Stage 2 · Ch2 · → F1, F2)*
- **FR-B1** Each agent runs its **own FastMCP server** (`transport="http", host, port` from config) — **no central server** (F1).
- **FR-B2** Exactly four `@mcp.tool`s, interop-named: `negotiate`, `receive_turn`, `submit_audit`, `receive_control`.
- **FR-B3** An MCP **client** that calls the opponent's URL; inbound messages land in **thread-safe queues** (not processed inline).
- **FR-B4** **Two separate processes / config dirs** (`config/police/` vs `config/thief/`); **no shared memory** (F2 — violation = disqualification).
- **FR-B5** On the wire, positions travel as coordinates only where the protocol allows; scent travels as an **intensity field, never opponent coordinates** (F7).

### FR-C · Strategy brain — the graded core *(Stage 3 · Ch6 · → F8)*
- **FR-C1** `BrainBase` with pure-Python `_pick_move`/`_decide_move`; subclasses `PoliceBrain`, `ThiefBrain`. **Movement is ALWAYS algorithmic** (F8).
- **FR-C2** **Bayesian belief map** of the opponent updated from scent + exclusions; `most_likely()` cell drives pursuit/evasion.
- **FR-C3** **Heuristic baseline:** cop = Manhattan pursuit toward belief-mass + barrier placement that **cuts escape routes / boxes-in**; thief = climb scent/belief gradient **away** from cop, prefer high-degree cells.
- **FR-C4** **Student seam** — `police_class`/`thief_class` = `package.module:Class` in `game.toml`; swapping the brain requires **no engine change**.
- **FR-C5** *(Excellence, optional)* Expectimax over the belief map, and a tabular **Q-learning** brain with committed **learning-curve** plots — both behind the FR-C4 seam, never on the critical path.

### FR-D · Language + scent *(Stage 4 · Ch4/6 · → F6, F7)*
- **FR-D1** **Scent/stigmergy** 5×5 field, center intensity 0.9, decay ρ=0.10/turn: `τ ← max(0, (1−ρ)τ + Δτ)`; thief deposits, both read the *opponent's* field only.
- **FR-D2** **Free natural-language hints** attached to a turn **may bluff**; the **physical board — barriers, captures, moves — must be TRUTHFUL** (lying about physical facts = severe disqualification).
- **FR-D3** Each move commits an `Intent ∈ {truth, lie}` declaring whether the hint lies (bound into the commit hash, revealed at audit).
- **FR-D4** **Trash-talk provider seam** (D2): `template` default (0 tokens); `every_n_steps` throttle; providers behind one interface; `claude_cli`/`ollama`/`claude_api` optional. The game completes with the LLM entirely absent.

### FR-E · Cloud / tunnel *(Stage 5 · Ch2 · → F13)*
- **FR-E1** Design + document **public tunnel** exposure (ngrok primary, Localtonet fallback) with an ADR; OAuth-gated where relevant.
- **FR-E2** All automated tests run on **localhost with a `FakeTransport`**; no test depends on a live peer, tunnel, or key.

### FR-F · Cryptographic fairness *(Stage 6 · Ch5 · → F3, F4, F5)*
- **FR-F1** **Commit-Reveal:** `commit = SHA256( canonical_json(State,Move,Intent,Nonce) + "|" + nonce )` where `canonical_json = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",",":"))`; nonce = `secrets.token_hex(16)` (32 hex). Verify with `secrets.compare_digest`. **Byte-identical formula with opponents.**
- **FR-F2** Turn order: **Commit → Acknowledge (lock) → Reveal (move+hint, nonce still hidden) → end-of-game reveal of ALL nonces**.
- **FR-F3** **Mutual audit** at game end re-hashes every recorded step both sides; any mismatch → `tamper_forfeit` **0/0** for the forging side.
- **FR-F4** **Step-0 signed declaration:** OS/CPU/RAM/GPU, LLM model+version, team, player IDs, and the **per-game GitHub commit hash**.

### FR-G · Reporting + GUI *(Stage 7 · Ch9/7 · → F10, F11, F12)*
- **FR-G1** **Four signed JSON artifacts** per series/sub-game — `declaration_<id>.json`, `config_<id>_g<NN>.json`, `log_<id>_g<NN>.json`, `result_<id>.json` — with shared `game_uid`, distinct `game_id`, `config_sha256` lock, and a **symmetric mutual signature** (hash only the symmetric outcome so both peers produce identical sigs).
- **FR-G2** Artifacts **auto-emailed** to `rmisegal+uoh26finalgame@gmail.com` as **JSON attachments** (plaintext = 0); **both sides send or neither is scored** (F11).
- **FR-G3** **Gatekeeper over Gmail** — token-bucket rate limiter (30 req/min, 2 concurrent, 5 s backoff, 3 retries, queue 100) + DOS guard + HTTP 429 handling; OAuth scope **`gmail.send` only** (F10).
- **FR-G4** **Live GUI** (Tkinter): local-truth **belief heatmap** + turn banner — **never the objective board** (F12).
- **FR-G5** **Replay Viewer**: re-hashes each logged step → green **"Verified OK"** / red **"TAMPERED"**; screenshots of both GUI and Replay committed in the README (F12).

### FR-H · Orchestration & reliability *(cross-cutting · → F9)*
- **FR-H1** Single **Orchestrator** gateway drives the turn loop.
- **FR-H2** **Legal-transition state machine** (`WAITING→COMPUTING→COMMITTING→AWAITING_REVEAL→VERIFYING→…`, error→`TECHNICAL_LOSS`); illegal transitions rejected.
- **FR-H3** **Deadline Tracker** (per-message expiry/retry) + **Watchdog** (heartbeat ~180 s, controlled shutdown + state persistence). A silent opponent → **technical loss, never a hang**.

### FR-I · Configuration & versioning *(cross-cutting · → F2, R4, R6, R11)*
- **FR-I1** **`config/game.json`** — the signed shared constitution (byte-identical both sides, `config_sha256`-locked): `board_and_agents`, `movement_and_barriers`, `scoring`, `pheromones`, `network_and_league`, `rate_limiter_gatekeeper`.
- **FR-I2** **`config/game.toml`** — private per-peer: `[game]`, `[network]`, `[strategy]`, `[trash_talk]`, `[llm]`, `[email]`, etc. Private TOML **never** overrides the signed JSON.
- **FR-I3** Rate limits live in **config, never code** (R4). Version starts **1.00**, single-sourced, with a startup compatibility check (R6).

### FR-J · SDK layer *(cross-cutting · → R1)*
- **FR-J1** `SimulationSdk` is the **single business entry** (`run_peer`, `run_series`); `cli.py` and `gui/` hold **zero business logic** and call only the SDK (R1).

### FR-K · League & submission *(→ F14, submission rules)*
- **FR-K1** Publish **two** cross-linked repos (Cop + Thief), public or shared with `rmisegal@gmail.com`; annotated git tag **`v1.0-submission`**.
- **FR-K2** Play **≥2 valid games vs different groups** (diversity reward for new opponents; truthful game-count declaration — a lie = disqualification).
- **FR-K3** Each member submits separately on Moodle `id=294462`; PDF `uoh-sqak-ex<CONFIRM-NN>.pdf` from the Word template (fields unaltered).
- **FR-K4** Commit `docs/RESEARCH-REPORT-Performance-Analysis.md` (resource/RPM/cost/fallback analysis).

## 6. Non-functional requirements (software rubric R1–R13)

| ID | Requirement | Threshold |
|---|---|---|
| NFR-1 (R1) | All logic through the SDK; GUI/CLI hold none | review |
| NFR-2 (R2) | OOP, **zero duplication** — extract at 2+ sites | 0 dup |
| NFR-3 (R3) | **One `ApiGatekeeper.execute()`** wraps every external call (LLM, MCP, Gmail, subprocess), wired not decorative | all routed |
| NFR-4 (R4) | Rate limits in **config**, never code | config |
| NFR-5 (R5) | **Queue, not drop** — overflow → FIFO queue + backpressure | test |
| NFR-6 (R6) | Version starts **1.00**, single-source, startup compat check | test |
| NFR-7 (R7) | **TDD** Red-Green-Refactor; happy + error paths; externals mocked | green |
| NFR-8 (R8) | **≤150 lines/file — raw AND logical**, tests included | `check_file_lines.py` |
| NFR-9 (R9) | `ruff check` (E,F,W,I,N,UP,B,C4,SIM) = **0** | 0 |
| NFR-10 (R10) | `pytest --cov` **≥85%** with LLM+MCP+Gmail mocked | ≥85% |
| NFR-11 (R11) | **Zero hardcoded** grid/ports/scoring/endpoints/model | 0 |
| NFR-12 (R12) | **Zero secrets**; `.env-example`; `.gitignore` excludes `.env,*.key,*.pem,credentials.json,token.json` before first commit | 0 |
| NFR-13 (R13) | **`uv` only**; `uv.lock` committed; no pip/venv/requirements.txt | auto |
| NFR-14 (ours) | **Python-3.13 CI** running ruff + line-check + version-sync + pytest-cov (reference has none — our standing win) | green |

## 7. Constraints & assumptions
- **C1** Hardware: macOS Apple-Silicon M2, 8 GB → Ollama small models only; Claude CLI on subscription (API-key-stripped); template mode = 0 tokens. Algorithms must be cheap (Computational Fairness).
- **C2** Grader has **no keys and no live opponent** → every external dependency mockable; a committed sample run is the proof of real execution.
- **C3** Interop is only guaranteed if the commit formula, tool names, message shapes, and signed `game.json` match the opponent **byte-for-byte**.
- **C4** Token budget ~200k/series; max 10 games/team; min 2 to pass.
- **A1** Opponents will exchange URLs + declaration manually (no matchmaking exists).

## 8. Risks & mitigations
| Risk | Mitigation |
|---|---|
| No opponent found in time (D4) | Offline artifacts satisfy the grade; league is separate. Start outreach **now**; run a loopback "self-match" to validate interop early. |
| Interop mismatch with opponent | Freeze the commit formula + schemas as a documented contract early (Stage 2/6); test against the reference's exact bytes. |
| Q-learning eats the timeline | Strictly optional, behind the seam; ship the heuristic baseline first and only then attempt RL. |
| ≤150-line pressure | Enforce `check_file_lines.py` in CI from commit 1; design small modules from the PLAN. |
| Secret leak (instant fail) | `.gitignore` for secrets committed **before** any code; CI scan; `.env-example` only. |
| Deadline slip (strict) | Bottom-up stages with binary Milestone gates; continuous commits; the four earliest stages (A–C, F) are the graded spine. |

## 9. Acceptance criteria & milestones (the 7 build stages)

Each stage is its own per-mechanism PRD and has a **binary Milestone** gate; the next stage does not start until the current one is green (ruff-0, ≤150, tests passing).

| Stage | Per-mechanism PRD | Milestone (binary pass) | Gates |
|---|---|---|---|
| 1 | `PRD_base_logic.md` | Two pieces move legally, blocked at barriers, illegal move rejected | FR-A |
| 2 | `PRD_mcp_infra.md` | Message from peer A received + interpreted by peer B over localhost | F1,F2 · FR-B |
| 3 | `PRD_strategy.md` | With known target, agent computes + executes a path autonomously | F8 · FR-C |
| 4 | `PRD_language_scent.md` | Scent map updates each step; LLM emits a truth/lie hint; game runs with 0 tokens | F6,F7 · FR-D |
| 5 | `PRD_cloud_tunnel.md` | Remote peer connects + plays a full round (design + ADR; localhost-tested) | F13 · FR-E |
| 6 | `PRD_crypto.md` | Move committed → revealed w/ valid nonce; Step-0 verifies; audit voids a tamper | F3,F4,F5 · FR-F |
| 7 | `PRD_reporting_gui.md` | Match auto-emailed (4 JSON); GUI shows belief; Replay says "Verified OK" | F9,F10,F11,F12 · FR-G,H |

**Definition of Done (whole project):** all F1–F14 pass; R1–R13 + NFR-14 green in CI; a committed sample run with 4 JSON artifacts + GUI/Replay screenshots; two tagged cross-linked repos; ≥2 league games; full docs package (this PRD + PLAN + TODO + 7 per-mechanism PRDs + PROMPTS + RESEARCH-REPORT); README academic report.

## 10. Excellence band (G5 — "best impressive")
OAT sensitivity analysis + Jupyter/LaTeX analysis notebook · Nielsen-heuristics UI pass · cost/token & RPM tables · ISO/IEC 25010 quality mapping · parallelism notes · optional Q-learning brain with learning-curve plots. All additive, none on the critical path.

## 11. Traceability summary
Every gate is owned: **F1,F2**→FR-B · **F3,F4,F5**→FR-F · **F6,F7**→FR-D (+FR-B5) · **F8**→FR-C · **F9**→FR-H · **F10**→FR-G3 · **F11**→FR-G1,G2 · **F12**→FR-G4,G5 · **F13**→FR-E · **F14**→FR-K. Every R-rule → NFR-1..14. The `docs/TODO.md` (Gate 2) must contain at least one task per FR-x and NFR-x ID above; the PLAN's self-review will assert this coverage.
