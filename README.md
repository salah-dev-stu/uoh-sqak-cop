# CipherChase — Distributed Cops-and-Robbers over a Peer-to-Peer Network

> **Final Project · Course 203.3763 "Orchestration of AI Agents"** · University of Haifa · Spring 2026 · Dr. Yoram Segal
> **Team `uoh-sqak`** — Salah Qadah (323039974) + Andalus Kalash (211435797)
> Paired repository (role-swapped): **`uoh-sqak-cop` ⇄ `uoh-sqak-thief`** *(links added at publish)*

Two mutually-distrustful autonomous agents — a **Cop** and a **Thief** — chase on a **7×7** grid over a
**peer-to-peer FastMCP** network with **no central judge**. Each agent is *simultaneously a server and a
client*, plays under **partial observation** (Dec-POMDP), and exchanges **natural-language hints that may
lie**. Because nobody is trusted, fairness is enforced **cryptographically** (Commit-Reveal + SHA-256 +
end-of-game mutual audit): any tamper or false board claim yields an automatic **0/0** by mathematics. The
move brain is **pure Python** — the game runs to completion at **zero LLM tokens**; the LLM only writes bluff text.

## Mandatory screenshots (F12)

| Live GUI — local belief heatmap | Replay Viewer — integrity check |
|---|---|
| ![Belief heatmap](docs/sample-run/live_gui_belief.png) | ![Replay Verified OK](docs/sample-run/replay_verified.png) |

The Live GUI shows **only this peer's belief** (never the objective board). The Replay Viewer re-hashes every
committed step of a logged game → green **"Verified OK"** / red **"TAMPERED"**. Above: the committed sample
run (`docs/sample-run/`) re-verifies clean on all 70 steps.

## Quick start (uv only — no keys, no live peer needed)

```bash
uv sync --dev                                   # Python 3.13 venv, all deps
uv run pytest                                   # 252 tests, 100% coverage, all externals mocked
uv run ruff check .                             # 0 findings
uv run python scripts/check_file_lines.py       # every .py ≤150 lines (raw AND logical)

# Play a full offline game → the 4 signed JSON reports:
uv run cipherchase self-match --config config/police --out logs
# Re-verify a logged game in the Replay Viewer (Tkinter):
uv run cipherchase replay --log docs/sample-run/log_uoh-sqak-police-c64efc39_g01.json
```

A committed **sample run** (4 signed JSON artifacts + the visuals above) lives in `docs/sample-run/` as
offline proof — the grader needs no API key, no credentials, and no opponent.

## Live 3D arena

![CipherChase 3D arena](docs/sample-run/arena_3d.png)

Watch a match unfold in **interactive 3D** — orbit the board, scrub the timeline, and hit **"New match"** to
run a brand-new game through the real engine and animate it live:

```bash
uv run python scripts/viz_server.py     # → http://localhost:8777
```

The **cyan cop** (light-beam) hunts the **magenta thief**; the floor is the cop's **live belief heatmap**
(bright = "probably here"); **amber walls** are barriers it raises to box the thief in. Self-contained
Three.js (vendored under `viz/`, no build step) — every barrier, belief cell, and move is real engine output.

---

## Academic report

### 1. Dec-POMDP model
Two agents (`n=2`) on a 7×7 grid under **partial observation**. Neither sees the other's coordinates; each
maintains a **Bayesian belief** (`domain/belief.py`) over the opponent's cell, updated from the opponent's
**scent field** (physical, cannot lie) and from exclusions, then diffused each turn to model motion. Actions
are `N/S/E/W/STAY`; the Cop additionally places barriers. Rewards (from `game.json`): capture 20/5, survival
5/10, tie 2, technical-loss 0/0, diversity 10. This is a zero-sum pursuit-evasion Dec-POMDP.

### 2. FastMCP coordination
Each peer runs **its own FastMCP HTTP server** (`infra/mcp_server.py`) exposing exactly four interop tools —
`negotiate / receive_turn / submit_audit / receive_control` — and an **MCP client** (`infra/mcp_client.py`)
to the opponent's URL. Inbound messages land in **thread-safe bounded queues** (queue-not-drop backpressure),
never processed inline. A DRY `BaseTransport` lets an in-memory `FakeTransport` drive full loopback matches in
tests with no socket. Coordination is stateful via a **legal-transition state machine** + **deadline tracker**
+ **watchdog** (`peer/`), so a silent peer becomes a technical loss, never a hang. Every external call —
MCP, LLM, Gmail, subprocess — is routed through one **`ApiGatekeeper.execute()`** (token-bucket + 429 retry +
ledger).

### 3. Strategy (the graded brain)
Movement is **always algorithmic** (`strategy/`, behind a `BrainBase` seam swappable by config). The **Cop**
greedily minimises Manhattan distance to the belief peak and places barriers by a **reachability min-cut**
heuristic (the barrier that most shrinks the thief's reachable set). The **Thief** climbs the distance/exit
gradient away from the believed cop. Both are deterministic and cheap — aligned with **Computational
Fairness** (a clever algorithm on an 8 GB laptop, zero tokens, beats brute force). The `game_id`/`game_uid`,
`config_sha256`, and commit hash all share **one canonical-JSON** implementation for byte-identical interop.

### 4. Reinforcement learning
The heuristic baseline is the shipped brain. **Q-learning and depth-limited expectimax** are designed as
drop-in `police_class`/`thief_class` swaps (PRD_strategy §5) — the natural next step to convert the cop's
reliable *containment* into *capture* within the 35-move budget. Learning curves would appear here if enabled.

### 5. Fairness & integrity (why P2P works without a judge)
`commit = SHA256(canonical_json({step,state,move,intent}) + "|" + nonce)` with a `secrets` nonce, verified in
constant time. Each move is **committed** (move hidden) → **revealed** → and every nonce is disclosed only at
the **end-of-game mutual audit**, which re-hashes both logs; any mismatch → `tamper_forfeit` 0/0. A **Step-0
signed declaration** binds hardware + LLM model + the per-game GitHub commit. Reports carry a **symmetric
mutual signature** (identical on both peers). The bluff hint may lie; the physical board may not — that
asymmetry is what the audit enforces.

### 6. Paired repository
This is the `uoh-sqak-cop` view. The paired **`uoh-sqak-thief`** repository contains the identical codebase
with role-swapped config (`config/thief/`). *(cross-link added at publish.)*

---

## Architecture & docs
- `docs/PRD.md` — product requirements (FR/NFR IDs, F1–F14 + R1–R13 traceability)
- `docs/PLAN.md` — **C4 model + UML + state machine + 11 ADRs** + the frozen interop contract (§8)
- `docs/PRD_*.md` — the 7 per-mechanism PRDs (one per build stage)
- `docs/TODO.md` — 622 TDD tasks + coverage matrices · `docs/PROMPTS.md` — prompt book
- `docs/deploy-tunnel.md` — ngrok/Localtonet runbook (F13) · `docs/RESEARCH-REPORT-Performance-Analysis.md`

## Engineering standards
Built bottom-up through **7 stages**, strict **TDD** (Red-Green-Refactor), **continuous commits**. Every file
**≤150 lines** (raw *and* logical), **ruff = 0**, **pytest --cov = 100%** (LLM + MCP + Gmail all mocked),
**zero hardcoded** values (all from `config/`), **zero secrets** (`.env-example` only), **`uv` only**, and a
**Python-3.13 CI** running ruff + line-check + version-sync + coverage on every push.

## Layout
```
src/cipherchase/  cli · constants · exceptions
  ├─ domain/    board rules scoring own_state · belief smell · crypto canonical · protocol negotiation game_ids · brains
  ├─ strategy/  factory · police_heuristic · thief_heuristic · trash_talk         (the graded seam)
  ├─ peer/      orchestrator state_machine deadline watchdog · handshake sealing turn_sender turn_handler summary declaration
  ├─ infra/     mcp_server mcp_client transport_base inboxes · llm_provider · email_sender
  ├─ report/    schemas artifacts mutual_signature emit
  ├─ shared/    config gatekeeper rate_limiter sysinfo version
  ├─ sdk/       sdk (single entry) · game_loop
  └─ gui/       window (heatmap) · replay (verifier) · heatmap replay_data
config/{police,thief}/  game.json (signed, byte-identical) · game.toml (private, role-swapped) · rate_limits.json
```
