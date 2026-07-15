# TODO — CipherChase Master Build List (TDD order)

> Companion to `docs/PRD.md`, `docs/PLAN.md`, and the 7 per-mechanism PRDs. Every task is a GitHub-style checkbox tagged with the requirement / gate IDs it implements. Build **bottom-up**, stage by stage; each module group follows **Red → Green → Refactor** (failing happy test → failing error test → implement → `ruff` 0 + `check_file_lines.py` ≤150 raw+logical → coverage). Each stage ends with a **binary Milestone** copied from PRD §9. No stage starts until the previous Milestone is green (ruff-0, ≤150, tests passing, CI Py-3.13 green).
>
> ID legend: `FR-*` functional (PRD §5), `NFR-*` rubric R1–R13 + our CI (PRD §6), `F#` final-project gate (PRD §F-gates). Numbers (grid, ports, scores, rates) are **always** config-driven (NFR-11); a task naming a number quotes the Appendix-ו default for clarity only.

---

## Stage 0 — Scaffold & standards

- [x] T001 (NFR-13) Run `uv init` at repo root to create the `cipherchase` project skeleton (no pip/venv/requirements.txt).
- [x] T002 (NFR-13) Add `[project]` metadata (name `cipherchase`, `requires-python = ">=3.13"`) to `pyproject.toml`.
- [x] T003 (NFR-13) Declare runtime deps (`fastmcp`, `tomli`/stdlib `tomllib`, google client libs) in `pyproject.toml` via `uv add`.
- [x] T004 (NFR-13, NFR-10) Declare dev deps (`pytest`, `pytest-cov`, `ruff`) in `pyproject.toml` via `uv add --dev`.
- [x] T005 (NFR-9) Configure `[tool.ruff.lint] select = ["E","F","W","I","N","UP","B","C4","SIM"]` in `pyproject.toml`.
- [x] T006 (NFR-10) Configure `[tool.pytest.ini_options]` + `[tool.coverage.*]` (source = `src/cipherchase`, `--cov` fail-under 85) in `pyproject.toml`.
- [x] T007 (NFR-13) Run `uv sync` and commit the generated `uv.lock`.
- [x] T008 (NFR-2) Create `src/cipherchase/` package skeleton with `__init__.py` and `py.typed`.
- [x] T009 (NFR-2) Create empty package dirs `domain/`, `peer/`, `infra/`, `shared/`, `strategy/`, `report/`, `gui/`, `sdk/` each with `__init__.py`.
- [ ] T010 (NFR-2) Create `tests/` tree mirroring the package (`tests/domain/`, `tests/peer/`, `tests/infra/`, `tests/shared/`, `tests/strategy/`, `tests/report/`, `tests/gui/`, `tests/e2e/`, `tests/fakes/`) each with `__init__.py`.
- [x] T011 (FR-A1, NFR-2) Write failing test `tests/test_constants.py` asserting `Direction` has exactly `N,S,E,W,STAY` members.
- [x] T012 (FR-A5, NFR-2) Extend the failing test to assert `Outcome` has `CAPTURE,SURVIVAL,TIE,TECHNICAL_LOSS` members.
- [x] T013 (FR-A1, NFR-2) Implement `constants.py` with `Direction`, `Outcome`, `MoveType` enums and `Cell = tuple[int,int]` alias (enum names / non-config literals only).
- [x] T014 (FR-A2) Add the `_DELTAS` enum→unit-vector map location note in `constants.py` docstring (geometry constant, resolved in `board.py`).
- [ ] T015 (NFR-11) Write failing test asserting each custom exception class exists and subclasses a common `CipherChaseError`.
- [x] T016 (NFR-11) Implement `exceptions.py` with `CipherChaseError` base + `IllegalMoveError`, `IllegalBarrierError`.
- [x] T017 (FR-F1) Add `CryptoError` to `exceptions.py`.
- [x] T018 (FR-G3, NFR-5) Add `GateLimitError` / `RateLimitExceeded` to `exceptions.py`.
- [ ] T019 (FR-B3) Add `TransportError`, `TransportTimeout`, `QueueFullError` to `exceptions.py`.
- [ ] T020 (FR-I1) Add `ConfigError` and `HandshakeError` to `exceptions.py`.
- [ ] T021 (FR-D4) Add `ProviderUnavailable` to `exceptions.py`.
- [ ] T022 (FR-H2) Add `IllegalTransition` to `exceptions.py`.
- [x] T023 (NFR-6) Write failing test `tests/shared/test_version.py` asserting `VERSION == "1.00"`.
- [x] T024 (NFR-6) Write failing test asserting `check_compatible("1.00")` passes and `check_compatible("2.00")` raises.
- [x] T025 (NFR-6, FR-I3) Implement `shared/version.py` with single-sourced `VERSION = "1.00"` and `check_compatible(other)` startup guard.
- [x] T026 (NFR-6, NFR-11) Write failing test asserting `game.toml`'s `version` field equals `shared/version.py` `VERSION` (single-source sync).
- [x] T027 (NFR-9, NFR-8) `ruff check` = 0 and `check_file_lines.py` ≤150 on `constants.py`, `exceptions.py`, `shared/version.py`.
- [x] T028 (FR-I1) Create `config/police/game.json` — signed shared constitution skeleton (`schema_version`, `agreed_between`, `board_and_agents`, `world`, `movement_and_barriers`, `scoring`, `pheromones`, `network_and_league`, `rate_limiter_gatekeeper`, `commit_payload_spec`).
- [x] T029 (FR-I1, F2) Copy the byte-identical `game.json` to `config/thief/game.json` (must match cop's bytes).
- [x] T030 (FR-A1, NFR-11) Fill `game.json.board_and_agents` (`board_size` 7, thief `[3,3]`, cop `[0,0]`, axis origin top-left).
- [x] T031 (FR-A3, NFR-11) Fill `game.json.movement_and_barriers` (`max_barriers` 14, `require_cop_adjacent` true, `directions` `[N,S,E,W,STAY]`).
- [x] T032 (FR-A5, NFR-11) Fill `game.json.scoring` (capture 20/5, survival 5/10, tie 2/2, technical_loss 0/0, `diversity_reward` 10, `survival_threshold` 35, `max_moves` 35).
- [x] T033 (FR-D1, NFR-11) Fill `game.json.pheromones` (`grid_size` 5, `deposit_intensity` 0.9, `decay_rate` 0.10, `falloff` 0.7, `min_emit` 1e-3, `absorb_gain` 1.0).
- [x] T034 (FR-G3, NFR-4) Fill `game.json.rate_limiter_gatekeeper` (rate 30/min, capacity 30, `max_concurrent` 2, `backoff_s` 5, `retries` 3, `queue` 100).
- [x] T035 (FR-E1, NFR-11) Fill `game.json.network_and_league` (schema fields for agreed league params; no host/port literals in code).
- [x] T036 (FR-I2) Create `config/police/game.toml` — private per-peer (`version`, `[game]`, `[belief]`, `[strategy]`, `[trash_talk]`, `[gui]`, `[paths]`, `[play]`, `[network]`, `[llm]`, `[email]`).
- [x] T037 (FR-I2, F2) Create `config/thief/game.toml` — role-swapped (own `my_port`, `opponent_url`, `role`, brain classes).
- [x] T038 (FR-C4, NFR-11) Set `[strategy] police_class`/`thief_class` defaults to `cipherchase.strategy.police_heuristic:PoliceBrain` / `...thief_heuristic:ThiefBrain` in both `game.toml`.
- [x] T039 (FR-C3, NFR-11) Add `[strategy]`/`[belief]` heuristic weights (`w_center`, `w_belief`, `w_dist`, `w_exits`, `w_scent`, `w_risk`, `lambda`, `min_gain`, `HORIZON`, `smell_trust`, `alpha`) with provisional defaults.
- [x] T040 (FR-D4, NFR-11) Add `[trash_talk]` (`provider=template`, `every_n_steps=3`, `lie_probability=0.4`) and `[llm]` (`provider=template`, `model`, `version`) to both `game.toml`.
- [x] T041 (FR-E1, NFR-11) Add `[network]` (`host="127.0.0.1"`, `my_port`, `opponent_url`, `rpc_timeout_s`, `queue_maxsize`) to both `game.toml`.
- [x] T042 (FR-G2, NFR-11) Add `[email]` (`recipient=rmisegal+uoh26finalgame@gmail.com`, `sender`, `subject_template`) to both `game.toml`.
- [x] T043 (FR-G3, NFR-4, FR-I3) Create `config/police/rate_limits.json` and `config/thief/rate_limits.json` (token-bucket params, config-not-code).
- [x] T044 (NFR-12) Create `.env-example` documenting all env var names (no real secrets).
- [x] T045 (NFR-12) Create `.gitignore` excluding `.env`, `*.key`, `*.pem`, `credentials.json`, `token.json` BEFORE first commit.
- [x] T046 (NFR-12) Add a CI/secret-scan note + `config/*/.env` ignore entries to `.gitignore`.
- [x] T047 (NFR-8) Reuse HW6 `scripts/check_file_lines.py` (raw + logical line counter) into `scripts/`.
- [ ] T048 (NFR-8) Write failing test `tests/test_line_limits.py` invoking `check_file_lines.py` over `src/` + `tests/` and asserting exit 0.
- [ ] T049 (NFR-3) Write failing test `tests/shared/test_gatekeeper.py` asserting `ApiGatekeeper.execute(callable, service=, action=)` returns the callable result and records a ledger event.
- [ ] T050 (NFR-3) Reuse HW6 `ApiGatekeeper` typed methods (`google_send`, `run_subprocess`, `http_request`) into `shared/gatekeeper.py`.
- [ ] T051 (NFR-3) Implement the `ApiGatekeeper.execute(callable, *, service, action)` façade (ADR-004) routing to the typed method + ledger record.
- [ ] T052 (FR-G2, NFR-3) Reuse HW6 `GmailApiSender` (real `gmail.send` OAuth, injectable backend) into `infra/email_sender.py` skeleton.
- [ ] T053 (FR-D4, NFR-3) Reuse HW6 `ClaudeCliProvider` (API-key-stripped subprocess) into `infra/llm_provider.py` skeleton.
- [x] T054 (NFR-14) Reuse HW6 `.github/workflows/ci.yml` targeting Python 3.13.
- [x] T055 (NFR-14, NFR-9) Add a CI job step running `uv run ruff check` (must be 0).
- [x] T056 (NFR-14, NFR-8) Add a CI job step running `check_file_lines.py` (≤150 raw+logical).
- [x] T057 (NFR-14, NFR-6) Add a CI job step running the version-sync check (`game.toml` version == `VERSION`).
- [x] T058 (NFR-14, NFR-10) Add a CI job step running `uv run pytest --cov` with fail-under 85.
- [ ] T059 (NFR-13) Add `CONTRIBUTING.md` / dev-setup notes (uv-only workflow, `uv sync`, `uv run pytest`).
- [ ] T060 (NFR-9, NFR-8, NFR-14) Confirm ruff-0, line-check pass, and CI green on the Stage-0 scaffold branch.
- [ ] **Milestone S0:** `uv sync` succeeds; CI (Py-3.13) runs ruff-0 + line-check + version-sync + pytest-cov skeleton green; secrets git-ignored before first commit.

## Stage 1 — Base logic (FR-A1..A5)

### `domain/board.py` — geometry (FR-A1/A2)
- [x] T061 (FR-A1, NFR-7) Write failing happy test `tests/domain/test_board.py`: `Board(size).in_bounds`, `distance` (Manhattan), `neighbors` counts (corner 2, edge 3, center 4).
- [x] T062 (FR-A2, NFR-7) Write failing happy test: `legal_moves` on empty board returns `[N,S,E,W,STAY]` order; `step` moves for each direction.
- [x] T063 (FR-A2, NFR-7) Write failing error test: `step`/`target_of` off an edge and into a barrier raises `IllegalMoveError`.
- [x] T064 (FR-A1) Implement `Board.__init__(size)` + `in_bounds` + `distance` (size injected from config, no literal).
- [x] T065 (FR-A2) Implement `Board.target_of`, `neighbors(cell, barriers)`, `legal_moves(cell, barriers)` (deterministic `[N,S,E,W,STAY]` order).
- [x] T066 (FR-A2) Implement `Board.step(cell, direction, barriers)` raising `IllegalMoveError` on illegal target.
- [x] T067 (FR-A1, NFR-11) Add config-variation test: a 5×5 fixture makes `in_bounds((4,4))` True and `in_bounds((5,5))` False (proves NFR-11).
- [x] T068 (NFR-9, NFR-8) `ruff` 0 + `check_file_lines.py` ≤150 on `domain/board.py` and its test.
- [x] T069 (NFR-10) `pytest --cov` on `domain/board.py` ≥85%.

### `domain/rules.py` — adjudication (FR-A2/A3/A4)
- [x] T070 (FR-A2, NFR-7) Write failing happy test `tests/domain/test_rules.py`: `is_legal_move`/`validate_move` accept legal, return target cell.
- [x] T071 (FR-A3, NFR-7) Write failing happy test: `can_place_barrier` accepts adjacent-in-budget target; rejects non-adjacent/duplicate/over-budget.
- [x] T072 (FR-A4, NFR-7) Write failing happy test: `is_capture` on co-location True; `is_boxed_in` True only when no legal move AND cop adjacent (config toggle).
- [x] T073 (FR-A4, NFR-7) Write failing happy test: `outcome` returns None mid-game, `CAPTURE` on co-location, `SURVIVAL` at threshold; capture precedes survival same turn.
- [x] T074 (FR-A2, NFR-7) Write failing error test: `validate_move` raises `IllegalMoveError`; barrier wrapper raises `IllegalBarrierError`.
- [x] T075 (FR-A2) Implement `is_legal_move` + `validate_move` (delegates to `Board`).
- [x] T076 (FR-A3) Implement `can_place_barrier(board, cop, target, barriers, max_barriers)` + `place_barrier` wrapper raising `IllegalBarrierError`.
- [x] T077 (FR-A4) Implement `is_boxed_in(board, thief, cop, barriers)` honoring `require_cop_adjacent` config toggle.
- [x] T078 (FR-A4) Implement `is_capture` (co-location OR boxed-in OR barrier-on-thief).
- [x] T079 (FR-A4) Implement `outcome(cop, thief, turn, board, barriers, survival_threshold)` (capture checked first).
- [x] T080 (FR-A4) Add edge-case test: thief boxed-in but cop NOT adjacent → not capture (SURVIVAL-track).
- [x] T081 (FR-A3) Add edge-case test: barrier placed exactly on thief's cell → capture, not error.
- [x] T082 (NFR-11) Add config-variation test: `max_barriers=2` fixture rejects the 3rd barrier.
- [x] T083 (NFR-9, NFR-8) `ruff` 0 + line-check ≤150 on `domain/rules.py` and its test.
- [x] T084 (NFR-10) `pytest --cov` on `domain/rules.py` ≥85%.

### `domain/scoring.py` — score table (FR-A5)
- [x] T085 (FR-A5, NFR-7) Write failing happy test `tests/domain/test_scoring.py`: each `Outcome` → correct `(cop,thief)` tuple from a fixture table.
- [x] T086 (FR-A5, NFR-7) Write failing happy test: `diversity_reward` applied when `new_opponent=True`; `technical_loss()` always `(0,0)`.
- [x] T087 (FR-A5, NFR-7) Write failing error test: unknown outcome key raises `KeyError`/`ConfigError` (never a silent default).
- [x] T088 (FR-A5) Implement `Scoring.__init__(table, diversity_reward)` reading injected config `scoring` mapping.
- [x] T089 (FR-A5) Implement `Scoring.score(outcome, new_opponent)` + `technical_loss()` (zero literals).
- [x] T090 (NFR-11) Add config-variation test: a mutated score table changes the returned tuple (proves no hardcoding).
- [x] T091 (NFR-9, NFR-8) `ruff` 0 + line-check ≤150 on `domain/scoring.py` and its test.
- [x] T092 (NFR-10) `pytest --cov` on `domain/scoring.py` ≥85%.

### `domain/own_state.py` — local peer truth (foundation for F2)
- [x] T093 (F2, NFR-7) Write failing happy test `tests/domain/test_own_state.py`: `OwnState` holds role/position/barriers/turn/history; never opponent data.
- [x] T094 (FR-A3, NFR-7) Write failing happy test: `moved_to`, `with_barrier`, `advanced` return NEW instances (immutability).
- [x] T095 (NFR-7) Write failing error test: original `OwnState` unchanged after `moved_to` (side-effect-free).
- [x] T096 (F2) Implement `OwnState` dataclass (role, position, barriers `frozenset`, turn, history tuple).
- [x] T097 (FR-A3) Implement immutable `moved_to`, `with_barrier`, `advanced` update methods.
- [x] T098 (NFR-9, NFR-8) `ruff` 0 + line-check ≤150 on `domain/own_state.py` and its test.
- [x] T099 (NFR-10) `pytest --cov` on `domain/own_state.py` ≥85%.

### Stage-1 integration & dependency purity
- [x] T100 (FR-A1, FR-A2, NFR-7) Write two-piece legal-move sequence test (the Milestone scenario): cop + thief each move and land where expected.
- [x] T101 (FR-A2) Write test: `legal_moves` excludes a barriered direction; out-of-bounds/into-barrier `step` raises `IllegalMoveError`.
- [x] T102 (NFR-2) Assert `domain/` imports nothing from `infra/`, `peer/`, `gui/`, or `shared.config` (dependency-inward purity test).
- [x] T103 (NFR-9, NFR-8, NFR-14) Confirm ruff-0, line-check, and CI Py-3.13 green on the Stage-1 branch.
- [x] **Milestone S1:** Two pieces move legally, are blocked at barriers, and an illegal move is rejected (`Board.step` moves both; `legal_moves` excludes a barriered direction; illegal `step` raises `IllegalMoveError`).

## Stage 2 — MCP infrastructure (FR-B1..B5, F1, F2)

### `domain/protocol.py` — wire dataclasses (FR-B2)
- [x] T104 (FR-B2, NFR-7) Write failing happy test `tests/domain/test_protocol.py`: `TurnMessage.to_dict → from_dict` round-trip identity.
- [x] T105 (FR-B2, NFR-7) Write failing happy test: `ControlMessage` and `AuditPayload` round-trip; `from_dict` ignores unknown keys, fills defaults.
- [x] T106 (FR-B2, NFR-7) Write failing error test: `from_dict` on a dict missing required fields surfaces an error (never crashes).
- [x] T107 (FR-B2, F6) Implement `TurnMessage` dataclass (step, sender, hint, smell_grid, commit, timestamp, barrier_placed, capture_claim, claim_response, win_claim) + `to_dict`/`from_dict`.
- [x] T108 (FR-B2) Implement `ControlMessage` dataclass (kind, sender, sub_game_number, status, step_budget, payload) + `to_dict`/`from_dict`.
- [x] T109 (FR-B2, F3) Implement `AuditPayload` dataclass (sender, records, result_claim) with `records[*]` = `{payload, nonce, commit}` passthrough + `to_dict`/`from_dict`.
- [x] T110 (FR-B5, F7) Write test `test_no_opponent_coords_on_wire`: serialized `TurnMessage` carries only `smell_grid` intensities, never an opponent-coordinate field.
- [x] T111 (NFR-9, NFR-8) `ruff` 0 + line-check ≤150 on `domain/protocol.py` and its test.

### `domain/game_ids.py` — deterministic ids
- [x] T112 (F1, NFR-7) Write failing happy test `tests/domain/test_game_ids.py`: both "peers" derive identical `game_uid` from same inputs.
- [x] T113 (NFR-7) Write failing happy test: `game_id(game_uid, sub_game_number)` distinct per sub-game, deterministic.
- [x] T114 (F1) Implement `game_uid(agreed_between, config_sha256, series_seed)` (hash of sorted party ids + sha + seed).
- [x] T115 (F1) Implement `game_id(game_uid, sub_game_number)`.
- [x] T116 (NFR-9, NFR-8) `ruff` 0 + line-check ≤150 on `domain/game_ids.py` and its test.

### `domain/negotiation.py` — game.json agreement (FR-I1)
- [x] T117 (FR-I1, NFR-7) Write failing happy test `tests/domain/test_negotiation.py`: matching `game.json` → `compare_agreements` True.
- [x] T118 (F5, NFR-7) Write failing error test: mismatched `game.json` → `compare_agreements` False (via `secrets.compare_digest`).
- [x] T119 (FR-I1) Implement `build_agreement(game_json, my_party)` assembling constitution + `agreed_between`.
- [x] T120 (FR-F1, FR-I1) Implement `sign_agreement(game_json)` = `config_sha256` over canonical JSON (same canonical rule as crypto).
- [x] T121 (F5) Implement `compare_agreements(mine, theirs)` byte-identical check with `secrets.compare_digest`.
- [x] T122 (NFR-9, NFR-8) `ruff` 0 + line-check ≤150 on `domain/negotiation.py` and its test.

### `infra/mcp_server.py` — FastMCP server + 4 tools (FR-B1/B2/B3, F1)
- [x] T123 (FR-B3, NFR-5, NFR-7) Write failing happy test `tests/infra/test_mcp_server.py`: `Inboxes.put` blocks/backpressures at cap (queue-not-drop), `drain` returns FIFO order.
- [x] T124 (FR-B2, NFR-7) Write failing happy test `test_build_peer_server_has_exactly_four_tools`: names exactly `negotiate`, `receive_turn`, `submit_audit`, `receive_control`.
- [x] T125 (FR-B3, NFR-7) Write failing happy test `test_tool_enqueues_not_inline`: `receive_turn(msg)` enqueues + returns ack WITHOUT running game logic (patched brain asserted uncalled).
- [ ] T126 (FR-B3, NFR-7) Write failing error test `test_malformed_message_not_enqueued`: bad dict → `{"ok": False}`, queue empty.
- [x] T127 (FR-B3, NFR-5) Implement `Inboxes` container (4 bounded `queue.Queue`, `maxsize` from config) with blocking `put` (backpressure) + `drain`.
- [x] T128 (FR-B1, NFR-11) Implement `build_peer_server(role, inboxes)` reading `host`/`port` from config, returning configured `FastMCP` (no `mcp.run` inside builder).
- [x] T129 (FR-B2, FR-B3) Implement the 4 `@mcp.tool`s (`negotiate`/`receive_turn`/`submit_audit`/`receive_control`), each validate-shape → enqueue → ack `(message: dict) -> dict`.
- [x] T130 (NFR-5) Write test `test_queue_overflow_is_fifo_not_drop`: push `maxsize+1`, assert backpressure + FIFO + zero loss.
- [x] T131 (NFR-9, NFR-8) `ruff` 0 + line-check ≤150 on `infra/mcp_server.py` and its test.

### `infra/mcp_client.py` — McpTransport (FR-B3, NFR-3)
- [x] T132 (FR-B3, NFR-7) Write failing happy test `tests/infra/test_mcp_client.py`: `send_turn`/`exchange_agreement`/`exchange_audit` call the opponent URL; `poll_turn`/`drain_inboxes` read local queues.
- [ ] T133 (NFR-3, NFR-7) Write failing test `test_every_outbound_call_routes_through_gatekeeper`: each `send_*`/`exchange_*` goes through `ApiGatekeeper.execute(service="mcp", action=<tool>)`.
- [x] T134 (FR-B3, NFR-7) Write failing error test `test_rpc_timeout_maps_to_transport_timeout`: outbound past `rpc_timeout_s` raises `TransportTimeout`.
- [x] T135 (FR-B3, NFR-11) Implement `McpTransport(opponent_url, inboxes)` with `exchange_agreement`, `send_turn`, `send_control`, `exchange_audit` (all gatekept, URL from config).
- [x] T136 (FR-B3) Implement inbound-read methods `poll_turn`, `poll_control`, `drain_inboxes` (non-network, non-blocking on `timeout=None`).
- [ ] T137 (NFR-3) Wrap every outbound MCP call in `ApiGatekeeper.execute(..., service="mcp", action=<tool>)`.
- [x] T138 (NFR-9, NFR-8) `ruff` 0 + line-check ≤150 on `infra/mcp_client.py` and its test.

### `tests/fakes/fake_transport.py` — test harness (FR-E2)
- [x] T139 (FR-E2, NFR-7) Implement `FakeTransport` in-memory queue-pair mirroring `McpTransport`'s 7-method surface (A.send_turn → B.inboxes.turn).
- [x] T140 (FR-E2) Write test `test_fake_transport_wires_A_to_B`: A's `send_turn` lands in B's `turn` inbox and vice-versa (no HTTP/FastMCP).

### `peer/handshake.py` — handshake glue (F5, F14)
- [x] T141 (F5, NFR-7) Write failing happy test `tests/peer/test_handshake.py`: `run_handshake` builds agreement → exchange → match → returns locked `Agreement` with `game_uid`/`game_id`.
- [x] T142 (F5, NFR-7) Write failing error test `test_agreement_mismatch_raises_handshake_error`: mismatch → `HandshakeError` (→ technical loss, no hang).
- [x] T143 (F14, F5) Implement `run_handshake(transport, config, my_party)` (build → `exchange_agreement` → `compare_agreements` → derive ids → lock) with a Step-0 declaration hook for crypto.
- [x] T144 (NFR-9, NFR-8) `ruff` 0 + line-check ≤150 on `peer/handshake.py` and its test (handshake declaration body completed in Stage 6).

### Stage-2 config separation & loopback (F1, F2)
- [ ] T145 (F2, NFR-7) Write test `test_two_config_dirs_distinct_inboxes`: two processes/config dirs yield DISTINCT `Inboxes` objects (no shared memory).
- [ ] T146 (F2) Write test asserting no module holds a reference reachable from both peers (zero-shared-memory guard).
- [x] T147 (FR-B4, NFR-11) Add `shared/config.py` `ConfigManager` loading `game.toml ⊕ signed game.json ⊕ rate_limits.json` (host/port/opponent-url/timeouts/queue-maxsize).
- [x] T148 (FR-I2, FR-I1) Write test: private `game.toml` NEVER overrides signed `game.json` values.
- [x] T149 (FR-B2, NFR-7) Write `test_game_ids_deterministic` + `test_negotiation_byte_identical_match` at the peer boundary.
- [x] T150 (F1, F2, NFR-7) Write the Milestone test `test_loopback_A_to_B_over_fake_transport`: A builds a `TurnMessage`, `send_turn`; B `poll_turn` returns byte-equal msg + `from_dict` reconstructs it.
- [x] T151 (F7, FR-B5) Write `test_no_opponent_coords_on_wire` at transport level (only `smell_grid` intensities cross).
- [ ] T152 (NFR-3) Write `test_gatekeeper_ledger_records_mcp_calls`: MCP sends recorded with `service="mcp"`.
- [ ] T153 (NFR-9, NFR-8, NFR-14) Confirm ruff-0, line-check ≤150 (incl. tests), CI Py-3.13 green on the Stage-2 branch.
- [ ] T154 (F1) Document a manual two-process localhost smoke run (A `send_turn` lands in B's queue) in `docs/`.
- [x] **Milestone S2:** A message from peer A is received and interpreted by peer B over localhost (`test_loopback_A_to_B_over_fake_transport` green + manual two-process smoke).

## Stage 3 — Strategy brain (FR-C1..C5, F8)

### `domain/brains.py` — BrainBase seam + Decision (FR-C1, F8)
- [x] T155 (FR-C1, NFR-7) Write failing happy test `tests/domain/test_brains.py`: `Decision` frozen dataclass carries `move_type,direction,hint,intent,fallback,random_move,response_seconds,reasoning,barrier_cell`.
- [ ] T156 (FR-C1, NFR-7) Write failing happy test: `BrainBase.decide` times the pick, stamps `reasoning`/`response_seconds`, returns a `Decision`.
- [x] T157 (FR-C1, NFR-7) Write failing error test: `BrainBase._pick_move`/`_decide_move` raise `NotImplementedError`.
- [x] T158 (FR-C1) Implement `Decision` dataclass (default `intent="truth"`, `hint=""` — safe truthful default per interop freeze §8.1).
- [x] T159 (FR-C1, F8) Implement `BrainBase.__init__(board, config, rng)` + concrete pure-Python `decide(state, belief)` (never calls an LLM).
- [x] T160 (FR-C1) Implement `_pick_move`/`_decide_move` abstract hooks raising `NotImplementedError`; `decide` packs the returned internal tuple.
- [x] T161 (NFR-9, NFR-8) `ruff` 0 + line-check ≤150 on `domain/brains.py` and its test.

### `domain/belief.py` — Bayesian belief map (FR-C2)
- [x] T162 (FR-C2, NFR-7) Write failing happy test `tests/domain/test_belief.py`: uniform prior `1/49`; `observe_smell` shifts mass to high-τ cells and stays normalized (Σ=1±ε).
- [x] T163 (FR-C2, NFR-7) Write failing happy test: `diffuse` conserves total mass on a bounded board WITH barriers (Σ before == Σ after).
- [x] T164 (FR-C2, NFR-7) Write failing happy test: `most_likely` argmax with DETERMINISTIC seeded tie-break then `(row,col)` order.
- [x] T165 (FR-C2, NFR-7) Write failing error test: excluding all cells → uniform-live fallback (`fallback` path), never divide-by-zero.
- [ ] T166 (FR-C2, NFR-11) Implement `BeliefGrid.__init__(size, smell_trust, alpha, rng)` (config-driven, validate ranges → `ConfigError`).
- [x] T167 (FR-C2) Implement `observe_smell(smell_cells)` Bayesian likelihood blend `L=smell_trust·τ+(1−smell_trust)/N` + renormalize.
- [x] T168 (FR-C2) Implement `exclude(cells)` (zero own cell / seen-empty / barrier cells) + renormalize + all-zero uniform fallback.
- [x] T169 (FR-C2) Implement `diffuse` motion model `P_next=alpha·P+(1−alpha)·Σ P(n)/deg(n)` with in-bounds/non-barrier `deg`.
- [x] T170 (FR-C2, FR-G4) Implement `most_likely`, `mass_at`, `as_matrix` (heatmap feed).
- [ ] T171 (FR-C2, NFR-11) Add parametrized test: `smell_trust=0` ignores scent, `=1` pure Bayesian.
- [x] T172 (NFR-9, NFR-8) `ruff` 0 + line-check ≤150 on `domain/belief.py` and its test.
- [x] T173 (NFR-10) `pytest --cov` on belief ≥85%.

### `strategy/factory.py` — student seam (FR-C4)
- [x] T174 (FR-C4, NFR-7) Write failing happy test `tests/strategy/test_factory.py`: `load_brain("pkg.mod:Class", ...)` returns a `BrainBase`.
- [x] T175 (FR-C4, NFR-7) Write failing error test: bad spec / non-BrainBase / missing symbol → typed `ConfigError`.
- [x] T176 (FR-C4) Implement `load_brain(spec, board, config, rng)` (`importlib` resolve `package.module:Class`, isinstance guard).
- [x] T177 (FR-C4) Write test: swapping `police_class` to a stub brain changes moves with NO engine edit.
- [x] T178 (NFR-9, NFR-8) `ruff` 0 + line-check ≤150 on `strategy/factory.py` and its test.

### `strategy/police_heuristic.py` — pursuit + barrier box-in (FR-C3)
- [x] T179 (FR-C3, NFR-7) Write failing happy test `tests/strategy/test_police_brain.py` (path convergence): given a known target + no barriers, repeated `decide()` strictly reduces `manhattan(cop,target)` and reaches it (the Milestone assertion).
- [x] T180 (FR-C3, NFR-7) Write failing happy test (barrier reduces reachable): after a placed barrier `|reach(thief)|` strictly decreases; an articulation-point barrier splits the region.
- [ ] T181 (FR-C3, NFR-7) Write failing error/edge test: a self-trapping barrier candidate is rejected (cop stays connected to thief region).
- [x] T182 (FR-C3, NFR-11) Implement greedy Manhattan movement scoring `−manhattan(c',t)+w_center·(−manhattan(c',center))+w_belief·mass_at(c')` (weights from config).
- [x] T183 (FR-C3, NFR-2) Extract BFS `reach(from_cell, barriers, HORIZON)` + `splits_region` into `strategy/reach.py` (shared, avoids dup, keeps ≤150).
- [x] T184 (FR-C3) Implement barrier heuristic: `gain(q)=|R0|−|Rq|` (+ `cut_bonus`), `score_barrier=gain−λ·manhattan(q,t)`, place only if `max(gain)≥min_gain` and not self-trapping.
- [x] T185 (FR-C3) Implement `_decide_move` returning step + optional `barrier_cell` (capture-by-boxing emerges when `reach(t)→{t}`).
- [ ] T186 (FR-A3) Write test: `max_barriers` exhausted → barrier disabled, still returns a legal move (graceful degrade).
- [x] T187 (NFR-9, NFR-8) `ruff` 0 + line-check ≤150 on `police_heuristic.py`, `reach.py`, and tests.
- [x] T188 (NFR-10) `pytest --cov` on police heuristic ≥85%.

### `strategy/thief_heuristic.py` — evasion (FR-C3)
- [x] T189 (FR-C3, NFR-7) Write failing happy test `tests/strategy/test_thief_brain.py`: chooses the legal move that INCREASES distance from `danger` when one exists.
- [ ] T190 (FR-C3, NFR-7) Write failing happy test: prefers the higher-degree (more-exit) cell when distances tie.
- [ ] T191 (FR-C3, NFR-7) Write failing error test: no legal move → `STAY` + `fallback=True`.
- [x] T192 (FR-C3, NFR-11) Implement evasion scoring `w_dist·dist + w_exits·exits + w_scent·(−own_scent) − w_risk·risk` (weights from config), seeded tie-break.
- [x] T193 (FR-C3) Implement `_pick_move` (pure move, no barriers; thief maintains its own symmetric `BeliefGrid` over the cop).
- [x] T194 (NFR-9, NFR-8) `ruff` 0 + line-check ≤150 on `thief_heuristic.py` and its test.
- [x] T195 (NFR-10) `pytest --cov` on thief heuristic ≥85%.

### F8 hard gate + edge cases
- [ ] T196 (F8, NFR-7) Write `tests/strategy/test_f8_no_llm.py`: patch/spy the provider + `subprocess.run`, run a full heuristic game via `FakeTransport`, assert provider NEVER called and every move produced (0 tokens).
- [x] T197 (F8) Write static test asserting no LLM/provider/`subprocess` symbol is reachable from `BrainBase.decide` or subclasses.
- [ ] T198 (NFR-C, FR-C1) Write determinism test: fixed `seed` → `decide()` totally deterministic across runs (seeded RNG for all tie-breaks).
- [ ] T199 (FR-C2) Write edge test: empty smell field at turn 0 → `observe_smell({})` no-op, cop pursues center default.
- [ ] T200 (FR-C3) Write edge test: NaN/negative config weight → constructor raises `ConfigError`.
- [ ] T201 (NFR-2) Assert `domain/belief.py` + `domain/brains.py` import nothing from `infra/`, `peer/`, `gui/`.

### `strategy/police_expectimax.py` + `strategy/qlearning.py` (FR-C5, OPTIONAL — excellence)
- [ ] T202 (FR-C5, NFR-7) [OPTIONAL] Write `tests/strategy/test_expectimax.py`: value monotonicity vs depth; returns a `Decision` shape identical to heuristic.
- [ ] T203 (FR-C5) [OPTIONAL] Implement `police_expectimax.py` depth-limited (`d≤2`) expectimax over top-K belief cells, reusing `reach.py`.
- [ ] T204 (FR-C5, NFR-7) [OPTIONAL] Write `tests/strategy/test_qlearning.py`: Q-update arithmetic; absent-table fallback to heuristic policy.
- [ ] T205 (FR-C5) [OPTIONAL] Implement tabular `qlearning.py` (belief-summary discrete state, ε-greedy, seeded RNG) selectable only via config seam.
- [ ] T206 (FR-C5) [OPTIONAL] Add offline trainer script producing `docs/sample-run/qlearning-curve.png` (never on critical path).
- [ ] T207 (NFR-9, NFR-8, NFR-14) Confirm ruff-0, line-check, CI Py-3.13 green on the Stage-3 branch (optional files excluded from DoD).
- [x] **Milestone S3:** With a known target cell, `PoliceBrain` computes and executes a path that reaches it autonomously, deterministically, at zero LLM tokens (`test_path_convergence` green).

## Stage 4 — Language & scent (FR-D1..D4, F6, F7)

### `domain/smell.py` — SmellField (FR-D1, F7)
- [x] T208 (FR-D1, NFR-7) Write failing happy test `tests/domain/test_smell.py`: `deposit` sets center to `deposit_intensity` (0.9), rings to `0.9·falloff^d`.
- [x] T209 (FR-D1, NFR-7) Write failing happy test: `decay_all` gives `τ←0.9·τ` when `Δτ=0`; N decays → `0.9^N·τ` within tolerance.
- [x] T210 (FR-D1, NFR-7) Write failing error test: repeated decay + a negative `Δτ` never yield `<0` (clamp `max(0,·)`).
- [x] T211 (FR-D1, F7, NFR-7) Write failing happy test: `snapshot()` emits only `"r,c"→float` string keys, drops sub-epsilon cells, no tuple/coordinate value.
- [x] T212 (FR-D1, NFR-11) Implement `SmellField.__init__(cfg)` reading `grid_size`, `deposit_intensity`, `decay_rate`, `falloff`, `absorb_gain`, `min_emit` from `game.json.pheromones`.
- [x] T213 (FR-D1) Implement `deposit(center, intensity)` (center + Chebyshev-ring falloff, accumulate) and `intensity_at`/`strongest_cell`.
- [x] T214 (FR-D1) Implement `decay_all` formula `τ←max(0,(1−ρ)·τ+Δτ)` with `ρ=0.10` from config.
- [x] T215 (FR-D1, F7) Implement `snapshot()` (`{"r,c": round(τ,6)}` above `min_emit`) and `absorb(smell_map)` (read side, parse same map).
- [ ] T216 (FR-D1, NFR-7) Write test: `absorb(snapshot())` round-trips within tolerance; malformed key/NaN/out-of-range value dropped (no crash).
- [ ] T217 (FR-D1) Write test: cop never calls `deposit` (asymmetry — only thief deposits), enforced by wiring.
- [x] T218 (NFR-9, NFR-8) `ruff` 0 + line-check ≤150 on `domain/smell.py` and its test.
- [x] T219 (NFR-10) `pytest --cov` on smell ≥85%.

### `domain/belief.py` — observe_smell read contract (FR-C2, shared)
- [x] T220 (FR-D1, F7, NFR-7) Write `tests/domain/test_belief_observe.py`: `observe_smell` raises mass on hot cells, renormalizes to Σ=1; malformed maps ignored.
- [x] T221 (FR-D1) Confirm `observe_smell` consumes the exact `snapshot()` dict shape and is called once per received turn BEFORE `diffuse()` (contract with Stage 3).

### `strategy/talk_providers.py` + `infra/llm_provider.py` — provider seam (FR-D4)
- [x] T222 (FR-D4, NFR-7) Write failing happy test `tests/strategy/test_template_provider.py`: `TemplateProvider.generate` deterministic given a seed, returns non-empty `str`.
- [ ] T223 (FR-D4, F6, NFR-7) Write failing happy test: `intent="lie"` draws from `BLUFF`, `intent="truth"` from `HONEST` phrase bank.
- [x] T224 (FR-D4) Implement `TalkContext` frozen read-only dataclass (role, step, belief_summary, intent, recent) — NO move authority.
- [x] T225 (FR-D4) Implement `TalkProvider` Protocol + `TemplateProvider` (0 tokens, seeded `rng.choice` over `HONEST`/`BLUFF` banks).
- [ ] T226 (FR-D4) Implement `ClaudeCliProvider`, `OllamaProvider`, `ClaudeApiProvider` thin wrappers (each ≤150 lines).
- [x] T227 (FR-D4, NFR-7) Write `tests/infra/test_llm_provider.py`: `ClaudeCliProvider` mocked by patching `subprocess.run` (HW6 pattern), no real process.
- [ ] T228 (FR-D4, NFR-7) Write failing error test: `build_provider` with unknown provider name → `ConfigError`; missing binary/key → `ProviderUnavailable` preflight.
- [x] T229 (FR-D4, NFR-11) Implement `build_provider(cfg)` factory in `infra/llm_provider.py` (maps `[llm]`/`[trash_talk]` provider → class, injects gatekeeper).
- [ ] T230 (NFR-3) Non-template providers wrap their one external call in `ApiGatekeeper.execute(service="llm", action=...)`.
- [x] T231 (NFR-9, NFR-8) `ruff` 0 + line-check ≤150 on `talk_providers.py`, `infra/llm_provider.py`, and tests.

### `strategy/trash_talk.py` — orchestration + intent + throttle (FR-D2/D3/D4, F6)
- [x] T232 (FR-D3, F6, NFR-7) Write failing happy test: `choose_intent(rng, cfg)` respects `lie_probability` over seeded draws (statistical band).
- [x] T233 (FR-D4, NFR-7) Write `tests/strategy/test_trash_talk_throttle.py`: on off-steps (`step % every_n_steps != 0`) the LLM provider is NOT called; template line returned.
- [ ] T234 (FR-D4, NFR-3, NFR-7) Write test: on on-steps the provider is called via `gatekeeper.execute` (NFR-3 wiring asserted).
- [x] T235 (FR-D4, NFR-7) Write failing error test: provider timeout/non-zero exit/empty output → `talk` returns the template fallback (move never blocked).
- [x] T236 (FR-D3) Implement `choose_intent(rng, cfg)` (seedable Bernoulli, gated to "something to hide").
- [x] T237 (FR-D4) Implement `talk(step, ctx)`: compute intent → throttle → try provider → fall back to template on any failure.
- [ ] T238 (FR-D2, F6) Implement `HONEST`/`BLUFF` template banks keyed by role+intent; phrases never encode a physical field.
- [ ] T239 (FR-D3) Wire `Decision.hint`/`intent` fill by the trash-talk layer (brain leaves `intent="truth"`, `hint=""` by default).
- [x] T240 (NFR-9, NFR-8) `ruff` 0 + line-check ≤150 on `strategy/trash_talk.py` and its test.
- [x] T241 (NFR-10) `pytest --cov` on trash_talk ≥85%.

### Stage-4 e2e + gate proofs (F6, F7)
- [x] T242 (FR-D4, F8, NFR-7) Write `tests/e2e/test_zero_token_game.py`: full cop-vs-thief game with `provider=template` reaches terminal state, asserts 0 LLM calls / 0 tokens (Milestone).
- [x] T243 (FR-D1, F7) In the e2e test assert the scent map is non-empty and UPDATES each step (thief's transmitted `snapshot()` differs turn-to-turn).
- [ ] T244 (FR-D2, F6) Write board-truth-under-bluff test: a step with `intent="lie"` still has TRUTHFUL `move`/`barrier_placed`/`capture_claim` and re-hashes clean at audit.
- [ ] T245 (FR-D3, F6) Write test: `intent="lie"` paired with a FALSE physical field is caught at audit as tamper → 0/0 (intent never launders a physical lie).
- [ ] T246 (NFR-9, NFR-8, NFR-14) Confirm ruff-0, line-check, CI Py-3.13 green on the Stage-4 branch.
- [x] **Milestone S4:** Scent map updates each step; the LLM emits a truth-or-lie hint; a full game runs at 0 tokens with `provider=template`.

## Stage 5 — Cloud / tunnel (FR-E1, E2, F13)

- [x] T247 (FR-E1, NFR-11, NFR-7) Write `tests/infra/test_bind_config.py`: `mcp_server` reads `host`/`my_port` from `game.toml [network]`; default `host="127.0.0.1"` (no literal in code).
- [x] T248 (FR-E1, NFR-11) Wire `build_peer_server` serving params `mcp.run(transport="http", host=cfg.network.host, port=cfg.network.my_port)` (league override `0.0.0.0`).
- [x] T249 (FR-E1, NFR-11, NFR-7) Write test: `mcp_client` targets `opponent_url` from config; no host/port/URL literal in code.
- [ ] T250 (FR-E1, NFR-3) Confirm the URL-agnostic `McpTransport` still routes every call through the gatekeeper for a tunnel URL (no branching logic added).
- [x] T251 (FR-E2, F13, NFR-7) Write test proving a full FakeTransport loopback match runs with NO socket / NO live peer / NO key (C2).
- [x] T252 (FR-E1, F13) Document the ngrok PRIMARY runbook (start peer on `0.0.0.0:my_port`, `ngrok http <port>`, exchange URLs, set `opponent_url`) in `docs/deploy-tunnel.md`.
- [x] T253 (FR-E1, F13) Document the Localtonet FALLBACK runbook (equivalent outbound tunnel) in `docs/deploy-tunnel.md` (ADR-005 reference).
- [x] T254 (FR-E1) Document NAT-traversal rationale (outbound relay, no port-forwarding), TLS termination at edge, and the security model (ephemeral URLs, no secrets in URL, integrity over untrusted transport).
- [x] T255 (FR-E1, F13) Document the league pre-match checklist (exchange URLs, lock `game.json`, verify `config_sha256`, exchange declarations, set `host=0.0.0.0`, confirm `negotiate`).
- [x] T256 (FR-E2) Document the manual (non-CI) tunnel smoke-test procedure + committed screenshot; never part of `pytest`.
- [x] T257 (F13) Reference ADR-005 (ngrok primary / Localtonet fallback; deploy-time only) in `docs/deploy-tunnel.md`.
- [x] T258 (FR-E1) Note tunnel-drop = silent-peer funnels to `TECHNICAL_LOSS` (owned by Stage 7 watchdog; not reimplemented here).
- [ ] T259 (NFR-9, NFR-8, NFR-14) Confirm ruff-0, line-check, CI Py-3.13 green on the Stage-5 branch (config + docs only, no network in tests).
- [x] **Milestone S5:** A remote peer connects and plays a full round — validated on localhost (FakeTransport loopback) with the ngrok/Localtonet path fully designed in ADR-005 + runbooks.

## Stage 6 — Cryptographic fairness (FR-F1..F4, F3, F4, F5)

### `domain/crypto.py` — CommitReveal (FR-F1, F3)
- [ ] T260 (FR-F1, F3, NFR-7) Write failing happy test `tests/domain/test_crypto.py`: `seal(payload)` → `verify(payload, nonce, commit)` is True; mutated payload / wrong nonce → False.
- [ ] T261 (FR-F1, NFR-7) Write failing test asserting `verify` uses `secrets.compare_digest` (a one-char-different commit → False; no `==` on digests).
- [ ] T262 (FR-F1, F3, NFR-7) Write the GOLDEN-VECTOR byte-exact test: `CommitReveal.canonical({"b":2,"a":1}) == '{"a":1,"b":2}'` AND a known `(payload,nonce)` hashes to a hard-coded expected hex digest.
- [ ] T263 (FR-F1) Implement `CommitReveal.canonical(payload)` = `json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",",":"))`.
- [ ] T264 (FR-F1, F3) Implement the FROZEN `commit_of(payload, nonce)` = `sha256((canonical+"|"+nonce).encode()).hexdigest()` (interop-critical, single source).
- [ ] T265 (FR-F1) Implement `seal(payload)` (`nonce=secrets.token_hex(16)`, 32 hex) and `verify` (`secrets.compare_digest`).
- [ ] T266 (FR-F1, NFR-7) Write nonce distinctness/width test: many `seal` calls → all nonces distinct, each 32 hex chars.
- [ ] T267 (FR-F1) Write test asserting non-ASCII payload/hint hashes consistently (`ensure_ascii=False` + `.encode()` mandatory).
- [ ] T268 (NFR-11) Source separator / hash name / nonce width as module constants (from `constants.py`/config), never scattered literals.
- [ ] T269 (NFR-9, NFR-8) `ruff` 0 + line-check ≤150 on `domain/crypto.py` and its test.

### `audit_records` — mutual audit (FR-F3, F4)
- [ ] T270 (FR-F3, F4, NFR-7) Write test: an honest cop-vs-thief loopback record → `audit_records` returns `passed=True`, `failed_steps=[]`, `verified_steps==len(records)`.
- [ ] T271 (FR-F3, F4, NFR-7) Write tamper test (payload): flip one byte of a recorded `payload` → `passed=False`, step flagged `commit_mismatch`.
- [ ] T272 (FR-F3, F4, NFR-7) Write tamper test (move): commit move N, reveal move S → flagged `move_altered`.
- [ ] T273 (FR-F3, F4, NFR-7) Write tamper test (barrier): `barrier_placed` on an illegal cell → `false_barrier` → `tamper_forfeit` 0/0.
- [ ] T274 (FR-F3, F4, NFR-7) Write tamper test (capture/win): unsupported `capture_claim`/`win_claim` → `false_capture`/`false_win`.
- [ ] T275 (FR-F3, F4, NFR-7) Write missing-nonce test: drop one step's nonce → `missing_nonce` in `failed_steps`, `passed=False` (absence of proof = tamper).
- [ ] T276 (FR-F3) Implement `audit_records(records, board_view)` — (a) `verify`, (b) `payload["move"]!=move`, (c) claim cross-checks vs reconstructed board → `{passed, verified_steps, failed_steps}`.
- [ ] T277 (FR-F3, NFR-7) Write `CryptoError` test: non-serializable / missing-key payload raises `CryptoError`, handled as a failed step (not a crash).
- [ ] T278 (NFR-9, NFR-8) `ruff` 0 + line-check ≤150 on the audit path and its test.
- [ ] T279 (NFR-10) `pytest --cov` on `domain/crypto.py` ≥85%.

### `shared/sysinfo.py` — system probe (FR-F4)
- [ ] T280 (FR-F4, NFR-7) Write `tests/shared/test_sysinfo.py`: probe returns `{os,cpu,ram_gb,gpu}`; patched failing subprocess → fields default to `"unknown"` (never raises).
- [ ] T281 (FR-F4, NFR-3) Implement `sysinfo` probes (`platform`/`sw_vers`, `sysctl machdep.cpu.brand_string`, `hw.memsize`, `system_profiler`) — ALL subprocess via `ApiGatekeeper.execute(service="subprocess")`.
- [ ] T282 (FR-F4) Implement field-level graceful degrade to `"unknown"`.
- [ ] T283 (NFR-9, NFR-8) `ruff` 0 + line-check ≤150 on `shared/sysinfo.py` and its test.

### `peer/sealing.py` + `turn_sender.py` + `turn_handler.py` (FR-F2)
- [ ] T284 (FR-F2, NFR-7) Write `tests/peer/test_sealing.py`: each step appends `{step,payload,nonce,commit,move,barrier_placed,capture_claim,win_claim}`; nonces held private until `all_records()`.
- [ ] T285 (FR-F2) Implement `sealing.py` record bookkeeping + `all_records()` end-of-game reveal.
- [ ] T286 (FR-F2, NFR-3, NFR-7) Write `tests/peer/test_turn_sender.py`: commit path calls `crypto.seal`, records via sealing, sends `TurnMessage{commit,...}` through the gatekeeper (nonce withheld).
- [ ] T287 (FR-F2) Implement `turn_sender.py` (commit send, then reveal `{move,intent,hint}` with nonce STILL hidden until game end).
- [ ] T288 (FR-F2, F6) Bind `intent` into the committed payload `{state, move, intent, step}` per interop freeze §8.1 (payload = mover's own observable commitment only).
- [ ] T289 (FR-F2, NFR-7) Write `tests/peer/test_turn_handler.py`: on commit → ack (lock); on reveal → apply move + update belief; store opponent `{payload,move,commit}` awaiting nonce.
- [ ] T290 (FR-F2) Implement `turn_handler.py` receive path (ack → apply → store).
- [ ] T291 (NFR-9, NFR-8) `ruff` 0 + line-check ≤150 on `sealing.py`, `turn_sender.py`, `turn_handler.py`, and tests.

### `peer/handshake.py` (declaration) + `peer/summary.py` (FR-F3/F4, F4/F5)
- [ ] T292 (FR-F4, F5, NFR-7) Write declaration test: build → sign → `verify` True; tamper any body field or `git_commit` → verify False → handshake rejects.
- [ ] T293 (FR-F4, F5) Implement Step-0 declaration builder in `handshake.py` (schema, team, players, role, `git_commit`, llm, system from sysinfo, version, signature).
- [ ] T294 (FR-F4, F5) Implement declaration signing = SHA-256 over `canonical_json(body excluding signature)` (same canonical as commit); verify with `compare_digest`.
- [ ] T295 (FR-F3, F4, NFR-7) Write `tests/peer/test_summary.py`: exchange full record lists, run `audit_records` over the OPPONENT's records, decide `tamper_forfeit` vs verified outcome.
- [ ] T296 (FR-F3, F4) Implement `summary.py` (end-of-game reveal exchange, audit trigger, `tamper_forfeit` → `AUDIT→TECHNICAL_LOSS`, emit `failed_steps` evidence for Stage 7).
- [ ] T297 (NFR-9, NFR-8) `ruff` 0 + line-check ≤150 on declaration + `summary.py` code and tests.

### Stage-6 integration + threat-model proofs
- [ ] T298 (F3, F4, F5, NFR-7) Write the Milestone test: `seal→send commit→ack→reveal→record`, declaration builds+verifies, `audit_records` passes on honest log AND fails (→0/0) on a mutated copy.
- [ ] T299 (FR-F3, F4) Write replay-attack test: a replayed prior nonce won't hash against this game's payload/step (`game_uid`/`git_commit` bind the record).
- [ ] T300 (NFR-6) Confirm version-sync green (declaration `version` == `VERSION`) in CI for Stage 6.
- [ ] T301 (NFR-9, NFR-8, NFR-14) Confirm ruff-0, line-check, CI Py-3.13 green on the Stage-6 branch.
- [ ] **Milestone S6:** A move is committed then revealed with a valid nonce; the Step-0 declaration verifies; the mutual audit voids a tampered log (passes clean, forfeits 0/0 on tamper).

## Stage 7 — Reporting / GUI / reliability (FR-G1..G5, FR-H1..H3, F9, F10, F11, F12)

### `shared/rate_limiter.py` — token bucket (NFR-4, NFR-5)
- [ ] T302 (NFR-4, NFR-7) Write `tests/shared/test_rate_limiter.py`: refill `tokens=min(cap, tokens+rate·dt)`, allow iff `tokens≥1`, decrement on allow.
- [ ] T303 (NFR-5, NFR-7) Write failing test: overflow up to `queue=100` buffered FIFO; 101st → `RateLimitExceeded` (queue-not-drop).
- [ ] T304 (NFR-4, NFR-11) Implement `rate_limiter.py` token bucket (rate 30/60, capacity 30, `max_concurrent` 2 semaphore, backoff 5s, retries 3, queue 100) from config.
- [ ] T305 (NFR-5) Implement bounded FIFO queue + DOS guard (reject burst above capacity via `RateLimitExceeded`).
- [ ] T306 (NFR-9, NFR-8) `ruff` 0 + line-check ≤150 on `shared/rate_limiter.py` and its test.

### `shared/gatekeeper.py` — façade + flow control (FR-G3, F10, NFR-3)
- [ ] T307 (FR-G3, F10, NFR-7) Write test: `execute()` routes each service path (`gmail`/`llm`/`mcp`/`subprocess`) to the typed method and records a ledger event.
- [ ] T308 (FR-G3, F10, NFR-7) Write 429 test: injected HTTP 429 → asserts backoff + requeue + retry, success after N; retries exhausted → typed error.
- [ ] T309 (FR-G3, NFR-5) Extend `gatekeeper.execute` to enforce the token bucket + concurrency semaphore + queue before invoking the callable.
- [ ] T310 (FR-G3, F10) Implement 429/transient handling (sleep backoff, requeue, retry ≤ retries) and DOS guard surfacing typed errors.
- [ ] T311 (FR-G3, F10) Restrict OAuth scope to `gmail.send` only (documented + asserted in the sender config).
- [ ] T312 (NFR-9, NFR-8) `ruff` 0 + line-check ≤150 on `shared/gatekeeper.py` and its test.

### `report/schemas.py` + `report/artifacts.py` — 4 artifacts (FR-G1, F11)
- [ ] T313 (FR-G1, NFR-7) Write `tests/report/test_artifacts.py` schema test: `declaration_<id>.json` builder emits exactly its top-level keys.
- [ ] T314 (FR-G1, NFR-7) Write schema test: `config_<id>_g<NN>.json` carries the signed `game.json` body + matching `config_sha256` + zero-padded `sub_game`.
- [ ] T315 (FR-G1, NFR-7) Write schema test: `log_<id>_g<NN>.json` carries `records[{step,sender,payload,nonce,commit}]` + `summary` + `mutual_agreement`.
- [ ] T316 (FR-G1, NFR-7) Write schema test: `result_<id>.json` carries `sub_games[{sub_game,outcome,scores}]` + `final_result` + `mutual_agreement`.
- [ ] T317 (FR-G1, F11, NFR-7) Write test: `game_uid` shared + `game_id` distinct across all four artifacts.
- [ ] T318 (FR-G1) Implement `schemas.py` (schema names + versions constants).
- [ ] T319 (FR-G1) Implement the `declaration` builder (series-static keys, timezone `Asia/Jerusalem`, groups, players, roles, links, num_sub_games, max_tokens).
- [ ] T320 (FR-G1) Implement the `config` builder (signed body + `config_sha256` from `shared/config.py`).
- [ ] T321 (FR-G1) Implement the `log` builder (records verbatim from sealing + summary + mutual_agreement).
- [ ] T322 (FR-G1) Implement the `result` builder (per-sub-game outcome/scores + final_result + mutual_agreement).
- [ ] T323 (NFR-9, NFR-8) `ruff` 0 + line-check ≤150 on `schemas.py`, `artifacts.py`, and tests.

### `report/mutual_signature.py` — symmetric signature (FR-G1, F11, ADR-009)
- [ ] T324 (FR-G1, F11, NFR-7) Write `tests/report/test_mutual_signature.py`: two peer views of the SAME outcome → byte-identical `mutual_sig`.
- [ ] T325 (FR-G1, F11, NFR-7) Write test: perturbing a peer-PRIVATE field does NOT change the sig; perturbing an OUTCOME field does.
- [ ] T326 (FR-G1) Implement `mutual_signature` hashing only `{game_uid, sub_game, outcome, scores(sorted by role), final_result, audit_verdict, config_sha256}` with the same canonical JSON as crypto.
- [ ] T327 (FR-G1, F11) Implement `agreed` flag via `secrets.compare_digest` of the two peers' signatures (mismatch → downstream `TECHNICAL_LOSS`).
- [ ] T328 (NFR-9, NFR-8) `ruff` 0 + line-check ≤150 on `report/mutual_signature.py` and its test.

### `report/emit.py` + `infra/email_sender.py` — auto-email (FR-G2, F11, F10)
- [ ] T329 (FR-G2, NFR-7) Write `tests/report/test_emit.py`: `emit` writes 4 files to disk then calls the gatekeeper-wrapped sender exactly once with 4 attachments + empty body.
- [ ] T330 (FR-G2, F11) Implement `emit.py` (write the 4 JSON, hand to `email_sender` via `ApiGatekeeper.execute(service="gmail", action="send")`).
- [ ] T331 (FR-G2, F10, NFR-7) Write `tests/infra/test_email_sender.py`: Gmail mocked via an INJECTED fake `google` backend (HW6 pattern) — no real send in CI.
- [ ] T332 (FR-G2) Implement `email_sender.py` MIME builder (4 JSON attachments, neutral/empty body, plaintext payload = 0) over HW6 `GmailApiSender`.
- [ ] T333 (FR-G2, F11, NFR-7) Write test: only one side reports → `mutual_agreement.agreed=false` → BOTH scored 0.
- [ ] T334 (FR-G2, NFR-11) Read recipient/sender/subject from `game.toml [email]` (no literal).
- [ ] T335 (NFR-9, NFR-8) `ruff` 0 + line-check ≤150 on `emit.py`, `email_sender.py`, and tests.

### `peer/state_machine.py` — legal-transition FSM (FR-H2, F9)
- [ ] T336 (FR-H2, F9, NFR-7) Write `tests/peer/test_state_machine.py` legal-transition tests: every edge in PRD §3.5 accepted.
- [ ] T337 (FR-H2, F9, NFR-7) Write illegal-transition tests: an absent edge raises `IllegalTransition`.
- [ ] T338 (FR-H2) Implement the enumerated states + legal-transition table + `transition(to)` raising `IllegalTransition`.
- [ ] T339 (FR-H2, F9) Route every `IllegalTransition` / error to `TECHNICAL_LOSS → REPORTING` (all paths funnel through REPORTING).
- [ ] T340 (NFR-9, NFR-8) `ruff` 0 + line-check ≤150 on `peer/state_machine.py` and its test.

### `peer/deadline.py` + `peer/watchdog.py` (FR-H3, F9)
- [ ] T341 (FR-H3, F9, NFR-7) Write `tests/peer/test_deadline.py`: Deadline Tracker registers a `response_timeout` (30s), retries, and on final expiry signals `WAITING → TECHNICAL_LOSS` (fake clock).
- [ ] T342 (FR-H3) Implement `deadline.py` per-message expiry + retry + technical-loss trigger.
- [ ] T343 (FR-H3, F9, NFR-7) Write `tests/peer/test_watchdog.py`: on missed heartbeat (~180s) the watchdog persists state + records to disk then stops (never hangs).
- [ ] T344 (FR-H3) Implement `watchdog.py` heartbeat monitor + controlled shutdown + state persistence.
- [ ] T345 (FR-H3, F9) Write test: a silent opponent → technical loss, never a hang (deadline → FSM → REPORTING).
- [ ] T346 (NFR-9, NFR-8) `ruff` 0 + line-check ≤150 on `deadline.py`, `watchdog.py`, and tests.

### `peer/orchestrator.py` + `peer/runtime.py` (FR-H1, F9)
- [ ] T347 (FR-H1, F9, NFR-7) Write `tests/peer/test_orchestrator.py`: per turn the orchestrator asks the FSM to transition, calls crypto/turn helpers, hands failures to `TECHNICAL_LOSS`.
- [ ] T348 (FR-H1) Implement `orchestrator.py` single gateway (thin; delegates compute to brains, I/O to turn_sender/turn_handler via gatekeeper).
- [ ] T349 (FR-H1) Implement `runtime.py` `PeerRuntime` turn loop (thin; delegates to orchestrator + drains inboxes on its own thread).
- [ ] T350 (FR-H1) Implement `peer/controls.py` / `control_link.py` control channel (enable/status/restart/quit) reading `ControlMessage`.
- [ ] T351 (NFR-9, NFR-8) `ruff` 0 + line-check ≤150 on `orchestrator.py`, `runtime.py`, `controls.py`, and tests.

### `gui/` — Live GUI belief heatmap (FR-G4, F12)
- [ ] T352 (FR-G4, F12, NFR-7) Write `tests/gui/test_heatmap.py` (headless): `heatmap` color-mapping from a `BeliefGrid.as_matrix()` is a pure function of the matrix.
- [ ] T353 (FR-G4, F12) Implement `gui/heatmap.py` (color each cell by belief matrix + turn banner; NEVER renders opponent's true position).
- [ ] T354 (FR-G4) Implement `gui/board_view.py` (draw 7×7 grid + OWN pieces/barriers from `own_state`).
- [ ] T355 (FR-G4) Implement `gui/window.py` (Tk root, layout, composition only — no logic).
- [ ] T356 (FR-G4) Implement `gui/live_apply.py` (apply each committed/revealed step to the view model, subscribe to orchestrator step events).
- [ ] T357 (FR-G4, NFR-1) Implement `gui/live_controls.py` (start/pause/step buttons calling the SDK, ZERO business logic).
- [ ] T358 (FR-G4, F12) Write test: GUI reads only local `own_state` + `BeliefGrid`; asserts no objective-board data path exists (F12/F7).
- [ ] T359 (FR-G4) Guard Tk widget construction so import/logic tests run without a display (headless).
- [ ] T360 (NFR-9, NFR-8) `ruff` 0 + line-check ≤150 on all `gui/` live modules and tests.

### `gui/replay*` — Replay Viewer re-hash verifier (FR-G5, F12)
- [ ] T361 (FR-G5, F12, NFR-7) Write `tests/gui/test_replay.py`: one clean `log` → all steps green "Verified OK"; one flipped `commit` → that step red "TAMPERED".
- [ ] T362 (FR-G5) Implement `gui/replay_data.py` (load a committed `log_<id>_g<NN>.json`, expose `records[]`).
- [ ] T363 (FR-G5, F12) Implement `gui/replay.py` re-hashing each record via `CommitReveal.commit_of` + `compare_digest` vs stored `commit` → per-step + overall verdict (REUSES crypto, not a re-impl).
- [ ] T364 (FR-G5) Implement `gui/replay_controls.py` (load-file / step / play-through controls).
- [ ] T365 (FR-G5, F12) Write test: overall verdict = all-green ⇒ "Verified OK"; any red ⇒ "TAMPERED".
- [ ] T366 (NFR-9, NFR-8) `ruff` 0 + line-check ≤150 on all `gui/replay*` modules and tests.

### `scripts/send_sample_report.py` + Stage-7 integration
- [ ] T367 (FR-G2) Implement `scripts/send_sample_report.py` — the ONE real `gmail.send` (non-CI, excluded from pytest) producing the committed `docs/sample-run/` artifacts.
- [ ] T368 (F9, F11, F12, NFR-7) Write the Stage-7 Milestone e2e: full FakeTransport match → 4 JSON built + handed to gatekeeper-wrapped sender (fake backend); GUI shows heatmap; Replay reports "Verified OK".
- [ ] T369 (F12) Add a deliberately-tampered log fixture and assert Replay reports "TAMPERED".
- [ ] T370 (NFR-3) Write single-façade audit test: every external call across the app (gmail/llm/mcp/subprocess) goes through `ApiGatekeeper.execute` (NFR-3 wiring, not decorative).
- [ ] T371 (NFR-9, NFR-8, NFR-14) Confirm ruff-0, line-check ≤150 (incl. tests), CI Py-3.13 green on the Stage-7 branch.
- [ ] **Milestone S7:** A full loopback match is auto-emailed as 4 JSON attachments; the GUI shows the belief heatmap; the Replay Viewer reports "Verified OK" (and "TAMPERED" on a corrupted log).

## Cross-cutting — SDK & CLI

- [ ] T372 (FR-J1, NFR-1, NFR-7) Write `tests/sdk/test_sdk.py`: `SimulationSdk.run_peer` / `run_series` are the single business entry; CLI/GUI hold zero logic.
- [ ] T373 (FR-J1, NFR-1) Implement `sdk/sdk.py` `SimulationSdk` (`run_peer(role, config)`, `run_series(...)`) orchestrating handshake → runtime → reporting.
- [ ] T374 (FR-J1) Implement `sdk/series.py` (multi-sub-game series driver, `game_id` per sub-game, aggregate `result`).
- [ ] T375 (FR-J1, NFR-1) Implement `cli.py` (arg parse `--role`/`--config` → SDK; ZERO business logic, R1).
- [ ] T376 (FR-J1) Implement `__main__.py` delegating to `cli.main()`.
- [ ] T377 (NFR-1) Write test asserting `cli.py` and `gui/` import only the SDK (no direct `peer/`/`domain/` business calls).
- [ ] T378 (FR-J1, NFR-7) Write test: `run_series` produces a `result` with per-sub-game outcomes over a FakeTransport loopback.
- [ ] T379 (NFR-2) Extract any duplicated config-loading / rng-seeding into a shared SDK helper (no dup at 2+ sites).
- [ ] T380 (NFR-9, NFR-8) `ruff` 0 + line-check ≤150 on `sdk/sdk.py`, `sdk/series.py`, `cli.py`, `__main__.py`, and tests.
- [ ] T381 (NFR-10) Confirm whole-suite `pytest --cov` ≥85% with LLM + MCP + Gmail mocked.

## Docs & submission

- [ ] T382 (FR-K1) Write `README.md` academic report (vision, architecture, C4 summary, how-to-run, interop contract).
- [ ] T383 (FR-K1, F12) Embed committed GUI + Replay(Verified OK) + Replay(TAMPERED) screenshots from `docs/sample-run/` in the README.
- [ ] T384 (F11) Capture a real sample run: commit the 4 JSON artifacts (`declaration`/`config`/`log`/`result`) to `docs/sample-run/`.
- [ ] T385 (FR-K1) Capture and commit GUI + Replay screenshots to `docs/sample-run/`.
- [ ] T386 (NFR-7) Maintain `docs/PROMPTS.md` Prompt Book (running record of the vibe-coding prompts).
- [ ] T387 (FR-K4) Write `docs/RESEARCH-REPORT-Performance-Analysis.md` (resource/RPM/cost/fallback analysis).
- [ ] T388 (FR-K1, F14) Publish identical source to repo `uoh-sqak-cop` (public or shared with rmisegal@gmail.com).
- [ ] T389 (FR-K1, F14) Publish identical source to repo `uoh-sqak-thief`; cross-link both READMEs.
- [ ] T390 (FR-K1) Add a publish script pushing identical source to both repos with role-swapped `config/{police,thief}/`.
- [ ] T391 (FR-K1, F14) Create the annotated git tag `v1.0-submission` on both repos.
- [ ] T392 (FR-K3, F14) Fill the Word template → `uoh-sqak-ex<CONFIRM-NN>.pdf` (fields unaltered). [EXTERNAL/user — D7: confirm `<NN>`]
- [ ] T393 (FR-K3, F14) Each member submits separately on Moodle `id=294462`. [EXTERNAL/user]
- [ ] T394 (FR-K2, F14) Arrange ≥2 different partner groups and play ≥2 valid league games (diversity reward; truthful game-count declaration). [EXTERNAL/user — D4]
- [ ] T395 (FR-K2) Record the truthful league game count + opponents in the `declaration` links for both repos.
- [ ] T396 (NFR-12) Final secret-scan pass: confirm `.env`, `token.json`, `credentials.json`, `*.key`, `*.pem` never committed.
- [ ] T397 (NFR-13) Confirm `uv.lock` committed and no pip/venv/requirements.txt anywhere.
- [ ] T398 (NFR-14) Confirm CI (Py-3.13) green on `v1.0-submission` for both repos.

## Excellence (optional, G5)

- [ ] T399 (FR-C5) [OPTIONAL] Run an OAT (one-at-a-time) sensitivity analysis over `smell_trust`, `alpha`, and heuristic weights.
- [ ] T400 (FR-K4) [OPTIONAL] Produce a Jupyter/LaTeX analysis notebook of the OAT sweep + results.
- [ ] T401 (FR-G4) [OPTIONAL] Run a Nielsen-heuristics UI review pass over the Live GUI + Replay and record fixes.
- [ ] T402 (FR-K4) [OPTIONAL] Add cost/token & RPM tables (per provider) to the research report.
- [ ] T403 (FR-K4) [OPTIONAL] Add an ISO/IEC 25010 quality-characteristic mapping to the research report.
- [ ] T404 (FR-C5) [OPTIONAL] Add Q-learning learning-curve plots (`docs/sample-run/qlearning-curve.png`) + a short write-up.
- [ ] T405 (FR-K4) [OPTIONAL] Add a parallelism / Computational-Fairness cost note (per-turn O(cells)) to the research report.

---

## Coverage matrix

Every requirement, NFR, and gate below maps to at least one task ID.

| ID | Description | Task IDs |
|---|---|---|
| FR-A1 | 7×7 grid + start cells | T011, T013, T030, T061, T064, T067, T100 |
| FR-A2 | Legal N/S/E/W/STAY movement, illegal rejected | T014, T031, T062, T063, T065, T066, T070, T074, T075, T101 |
| FR-A3 | Barriers (≤14, adjacent, truthful, on-thief=capture) | T031, T071, T076, T081, T082, T094, T097, T186 |
| FR-A4 | Capture / survival / boxed-in detection | T032, T072, T073, T077, T078, T079, T080 |
| FR-A5 | Config-driven scoring | T012, T032, T085, T086, T087, T088, T089, T090 |
| FR-B1 | Own FastMCP server per peer, no central server | T112, T114, T115, T128, T150 |
| FR-B2 | Exactly 4 interop tools | T104, T105, T106, T107, T108, T109, T124, T129, T149 |
| FR-B3 | MCP client + thread-safe queues (not inline) | T123, T125, T126, T127, T130, T132, T134, T135, T136, T137 |
| FR-B4 | Two processes / config dirs, no shared memory | T147 |
| FR-B5 | Scent intensity-only on wire, no opponent coords | T110, T151 |
| FR-C1 | BrainBase + Decision, algorithmic-only | T155, T156, T157, T158, T159, T160, T198 |
| FR-C2 | Bayesian belief map | T162, T163, T164, T165, T166, T167, T168, T169, T170, T171, T199 |
| FR-C3 | Heuristic pursuit / barrier box-in / evasion | T179, T180, T181, T182, T183, T184, T185, T189, T190, T191, T192, T193, T200 |
| FR-C4 | Student seam (package.module:Class) | T038, T174, T175, T176, T177 |
| FR-C5 | Expectimax + Q-learning (optional excellence) | T202, T203, T204, T205, T206, T399, T404 |
| FR-D1 | Scent/stigmergy 5×5 decay 0.10 | T033, T208, T209, T210, T211, T212, T213, T214, T215, T216, T217, T220, T221, T243 |
| FR-D2 | Bluffing hints, truthful physical board | T238, T244 |
| FR-D3 | Intent∈{truth,lie} committed + audited | T232, T236, T239, T245, T288 |
| FR-D4 | Trash-talk provider seam, template default, throttle | T040, T222, T223, T224, T225, T226, T227, T228, T229, T233, T234, T235, T237, T242 |
| FR-E1 | Public-tunnel exposure design + docs | T035, T247, T248, T249, T250, T252, T253, T254, T255, T257, T258 |
| FR-E2 | No live network in tests (FakeTransport) | T251, T256 |
| FR-F1 | Frozen commit formula (SHA-256 + canonical JSON) | T120, T260, T261, T262, T263, T264, T265, T266, T267 |
| FR-F2 | Commit → ack → reveal → end-reveal nonces | T284, T285, T286, T287, T288, T289, T290 |
| FR-F3 | Mutual audit → 0/0 on tamper | T109, T270, T271, T272, T273, T274, T275, T276, T277, T295, T296, T299 |
| FR-F4 | Step-0 signed declaration (+ git commit hash) | T280, T281, T282, T292, T293, T294 |
| FR-G1 | Four signed JSON + symmetric mutual signature | T313, T314, T315, T316, T317, T318, T319, T320, T321, T322, T324, T325, T326, T327 |
| FR-G2 | Auto-email JSON attachments, both sides or 0 | T042, T052, T329, T330, T331, T332, T333, T334, T367 |
| FR-G3 | Gatekeeper over Gmail (token bucket + DOS + 429) | T034, T307, T308, T309, T310, T311 |
| FR-G4 | Live GUI belief heatmap (local truth) | T170, T352, T353, T354, T355, T356, T357, T358, T359, T401 |
| FR-G5 | Replay Viewer Verified OK / TAMPERED | T361, T362, T363, T364, T365 |
| FR-H1 | Single Orchestrator gateway | T347, T348, T349, T350 |
| FR-H2 | Legal-transition state machine | T336, T337, T338, T339 |
| FR-H3 | Deadline Tracker + Watchdog | T341, T342, T343, T344, T345 |
| FR-I1 | Signed shared game.json constitution | T028, T029, T030, T117, T119, T120, T121, T148 |
| FR-I2 | Private per-peer game.toml | T036, T037, T148 |
| FR-I3 | Rate limits in config; version 1.00 single-source | T026, T043 |
| FR-J1 | SDK single business entry; CLI/GUI zero logic | T372, T373, T374, T375, T376, T377, T378 |
| FR-K1 | Two cross-linked repos + v1.0-submission tag | T382, T383, T385, T388, T389, T390, T391 |
| FR-K2 | ≥2 valid league games vs different groups | T394, T395 |
| FR-K3 | Moodle submission + PDF | T392, T393 |
| FR-K4 | Research-report performance analysis | T387, T400, T402, T403, T405 |
| NFR-1 | All logic via SDK; GUI/CLI hold none | T357, T372, T375, T377 |
| NFR-2 | OOP, zero duplication | T008, T009, T010, T011, T012, T013, T102, T183, T201, T379 |
| NFR-3 | One ApiGatekeeper.execute() wraps every external call | T049, T050, T051, T133, T137, T152, T230, T234, T281, T286, T370 |
| NFR-4 | Rate limits in config, never code | T034, T043, T302, T304 |
| NFR-5 | Queue, not drop | T018, T123, T130, T303, T305, T309 |
| NFR-6 | Version 1.00 single-source + startup compat check | T023, T024, T025, T026, T057, T300 |
| NFR-7 | TDD Red-Green-Refactor; happy + error; externals mocked | T061, T070, T104, T155, T208, T260, T302, T336, T372 |
| NFR-8 | ≤150 lines/file raw AND logical (tests too) | T027, T047, T048, T068, T083, T091, T098, T111, T131, T240, T269, T291, T306, T340, T360, T366, T371, T380 |
| NFR-9 | ruff check = 0 | T005, T027, T055, T068, T083, T116, T131, T178, T218, T269, T312, T323, T371, T380 |
| NFR-10 | pytest --cov ≥85% (LLM+MCP+Gmail mocked) | T006, T058, T069, T084, T092, T099, T173, T188, T195, T279, T381 |
| NFR-11 | Zero hardcoding | T015, T016, T030, T031, T032, T033, T034, T035, T067, T082, T090, T128, T135, T166, T212, T229, T247, T248, T249, T268, T334 |
| NFR-12 | Zero secrets; .env-example; .gitignore before commit | T044, T045, T046, T396 |
| NFR-13 | uv only; uv.lock committed | T001, T002, T003, T004, T007, T059, T397 |
| NFR-14 | Python-3.13 CI (ruff + line + version-sync + cov) | T054, T055, T056, T057, T058, T060, T398 |
| F1 | P2P FastMCP, no central server | T112, T113, T114, T115, T128, T150, T154 |
| F2 | Two processes / config dirs, no shared memory | T029, T037, T093, T096, T145, T146 |
| F3 | Commit-Reveal + SHA-256 | T109, T260, T262, T264, T298 |
| F4 | Mutual audit → 0/0 on tamper | T270, T271, T272, T273, T274, T275, T295, T296, T298 |
| F5 | Step-0 signed declaration + per-game commit hash | T118, T121, T141, T142, T143, T292, T293, T294, T298 |
| F6 | NL hints may bluff; board/barriers/captures truthful | T107, T223, T232, T238, T244, T245, T288 |
| F7 | Scent 5×5 + belief drive moves; intensity-only wire | T110, T151, T211, T215, T220, T243 |
| F8 | Algorithmic brain; LLM = trash-talk only | T159, T196, T197, T242 |
| F9 | Orchestrator + FSM + deadline/watchdog; no hang | T336, T337, T339, T341, T343, T345, T347, T368 |
| F10 | Gatekeeper over Gmail; gmail.send only | T307, T308, T311, T331 |
| F11 | 4 signed JSON auto-emailed; both sides or 0 | T317, T324, T325, T327, T329, T330, T333, T368, T384 |
| F12 | Live GUI + Replay (Verified OK) + screenshots | T352, T353, T358, T361, T363, T365, T368, T369, T383 |
| F13 | Public tunnel; localhost for tests | T251, T252, T253, T255, T257 |
| F14 | Two repos + v1.0 tag + ≥2 league games | T143, T388, T389, T391, T392, T393, T394 |
