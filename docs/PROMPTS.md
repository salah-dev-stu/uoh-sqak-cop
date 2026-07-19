# Prompt Book — CipherChase

> Log of the AI prompts and prompting strategy used to build this project (rubric §2 mandatory deliverable). Newest at the bottom of each phase. This is a *working log*, appended to as development proceeds — not a one-time artifact.

## How we use AI on this project
- **Model:** Claude Opus 4.8 (1M context) via Claude Code CLI (subscription, API-key-stripped — 0 API tokens).
- **Discipline:** Vibe-Coding Lifecycle — Idea → PRD → PLAN(C4+ADR) → TODO → per-mechanism PRDs → **two approval gates** → build stage-by-stage under TDD → README → run → push. No code before the docs package is approved.
- **In-game LLM use is separate and optional:** the *game engine* uses zero LLM (template trash-talk provider by default); any LLM is confined to bluff text and is fully mocked in tests. See `PRD_language_scent.md` and `RESEARCH-REPORT-Performance-Analysis.md`.

## Phase 0 — Brainstorming & decisions
- **Prompt (design brainstorm):** "Confirm the locked decisions D1/D3, resolve D2 (LLM mode), D5 (deploy/test), D6 (HW6 reuse), flag D7 (PDF number) + D4 (opponents); then propose the strategy-brain approaches and present the whole design for approval before any docs."
  - *Outcome:* decisions locked (see PRD §4); strategy brain = heuristic baseline first, expectimax + Q-learning behind the seam; "best impressive" excellence scope adopted.

## Phase 1 — Docs package (Gate 1 → Gate 2)
- **Prompt (context map, subagent):** "Map the reference `police_thief` repo's layer/module/test structure and the HW6 `parley` reuse assets (Gatekeeper `execute` shape, Gmail `gmail.send` sender, Claude-CLI provider, `check_file_lines.py`, Py-3.13 CI). Return conclusions, not file dumps."
- **Prompt (PRD):** "Write the top-level PRD with FR/NFR IDs, F1–F14 + R1–R13 traceability, locked decisions D1–D7, 7-stage acceptance milestones, risks."
- **Prompt (PLAN):** "Write the architecture PLAN: C4 (context/container/component), UML class + turn/audit sequence diagrams, legal-transition state machine, 11 ADRs, frozen interop contract (commit formula, 4 tools, 4 artifacts), testing architecture."
- **Prompt (7 per-mechanism PRDs, parallel subagents):** each agent read `PRD.md` + `PLAN.md` for canonical names, then wrote one of `PRD_{base_logic,mcp_infra,strategy,language_scent,cloud_tunnel,crypto,reporting_gui}.md` to a fixed section template, tagging every requirement with its FR/NFR ID and returning only a short consistency summary.
  - *Reconciliation:* divergences (committed-payload shape, `intent` vs `verdict`) were frozen in PLAN §8.1 as the single source of truth.
- **Prompt (TODO):** "Write 400–650 TDD-ordered tasks (Red-Green-Refactor per module), each tagged with its FR/NFR/F-gate ID, Stage 0–7 + cross-cutting + excellence, ending with a full coverage matrix."
  - *Critical verification:* grep-checked that every FR-*, NFR-1..14, and F1..14 maps to ≥1 real task line; the single gap (FR-I3) was tagged onto T025/T043.

## Phase 2 — Build (Stages 0–7, Jul 13–15)
- Per-stage TDD prompts: RED test first, minimal GREEN, ruff/line-check gates each module (board/rules/scoring, protocol/canonical/game_ids/negotiation, belief/brains/heuristics, smell/providers/trash-talk, crypto/sealing/declaration, gatekeeper/reporting/FSM/orchestrator, SDK/CLI/GUI). Notable iterations: the FSM rejected the orchestrator's first turn flow (missing VERIFYING hop — the state machine caught a real bug); the game loop surfaced a move-vs-barrier ordering bug fixed under test.
- Post-stage closes: physical-claim audit, LLM-through-gatekeeper, expectimax seam variant, real gmail.send scripts, OAT sensitivity, live 3D arena (Three.js, tuned from "chaotic" to legible after user feedback).

## Phase 3 — Championship planning (2026-07-19)
- **Prompt (4 parallel audits):** "Scan every file, every line" → (1) line-level source audit vs R1–R13; (2) protocol/league-readiness audit extracting the reference peer's exact wire choreography and our gap list; (3) docs-vs-code drift audit (every claim verified); (4) competitive strategy lab — 120-game win-rate matrices, root-cause diagnosis (phantom-trail belief, greedy-parity stall, squandered barriers), upgrade probes (HerderCop won).
  - *Key discoveries:* the P2P layer is test-only; our per-turn reveal is wrong vs the reference's sealed-single-message choreography (and two payload shapes would crash a reference peer today); our cop captures 0% vs any belief-using thief; the scent-delta decoder achieves near-oracle localisation from legal information.
- **Prompt (plan):** synthesize audits → `docs/PLAN-CHAMPIONSHIP.md` (league math, blockers, P0–P5 roadmap, risks) + three championship PRDs (`PRD_league_runtime`, `PRD_winning_brain`, `PRD_integrity_hardening` — 28 IH requirements) + TODO §Championship (T406+). Implementation deliberately deferred pending approval (planning gate).
