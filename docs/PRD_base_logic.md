# PRD — Base Game Logic (Stage 1)

| Field | Value |
|---|---|
| **Mechanism** | Base game logic — 7×7 board geometry, move legality, barriers, capture/survival, scoring (single process, pure domain) |
| **Stage** | 1 of 7 (build order — the foundation of the graded spine) |
| **Chapter** | Ch3 (base game logic) |
| **Gates** | None directly — **foundation for all of F1–F14** (every gate stands on a correct engine) |
| **FRs covered** | FR-A1, FR-A2, FR-A3, FR-A4, FR-A5 |
| **NFRs in force** | NFR-2 (no dup), NFR-7 (TDD), NFR-8 (≤150 raw+logical), NFR-9 (ruff 0), NFR-10 (cov ≥85%), NFR-11 (zero hardcoding) |
| **Version** | 1.00 (single-sourced in `shared/version.py`) |
| **Status** | **Gate-2 draft** — approve with the full docs package before code |
| **Target files** | `domain/board.py`, `domain/rules.py`, `domain/scoring.py`, `domain/own_state.py`, `exceptions.py` (additive) |

---

## 1. Purpose & scope

Deliver the **pure, I/O-free game engine** for CipherChase: a 7×7 grid, orthogonal movement, truthful barrier placement, and the adjudication of capture / survival / boxed-in plus the score table. This is the **objective physics** of the world — the single source of truth that later stages (MCP transport, strategy brain, scent, crypto, reporting) all sit on top of. It runs in **one process with zero network, zero LLM, zero crypto** so it can be TDD'd in isolation.

**In scope:** board geometry, move-legality adjudication, barrier rules, terminal-state detection, config-driven scoring.

**Out of scope (owned by later PRDs):** belief/scent (`PRD_language_scent`), the move-choosing brain (`PRD_strategy` — this PRD only *validates* moves, never *chooses* them), commit-reveal (`PRD_crypto`), messaging (`PRD_mcp_infra`), reporting/GUI (`PRD_reporting_gui`). The **opponent's** true position is never known here — `own_state.py` holds only the local peer's own truth (F2/zero-trust foreshadowed).

**Design rule for the whole PRD:** every mandatory number (grid size, start cells, `max_barriers`, `survival_threshold`, `max_moves`, every score) is read from `config/game.json` via the injected config mapping — **never a literal in `domain/`** (NFR-11). Modules receive already-parsed config values as constructor/function args; `domain/` does not import `shared/config.py` (keeps `domain` pure, mockable, and dependency-inward per PLAN §2).

## 2. Requirements

Traceable to PRD §5 FR-A. Numbers shown are the Appendix-ו defaults that live in `game.json`, quoted here for clarity only.

- **FR-A1 — Grid & start cells.** A square grid of `board_size` (=7). Thief start `[3,3]`, cop start `[0,0]`, axis origin/index all read from config `board_and_agents`. Cells addressed as `Cell = tuple[int, int]` = `(row, col)`, `0 ≤ r,c < board_size`.
- **FR-A2 — Legal movement.** Moves are exactly `N, S, E, W, STAY` (orthogonal, single step). A move is **illegal** if it is diagonal (never emitted, but rejected defensively), lands out of bounds, or crosses/lands into a barrier cell. Illegal move → caller rejects → (upstream) technical loss; at this layer it **raises `IllegalMoveError`** or is filtered out of `legal_moves(...)`.
- **FR-A3 — Barriers.** The cop may place at most `max_barriers` (=14) barriers over the game, **one per turn**, on a cell **orthogonally adjacent to the cop's current cell**, and the placement is **declared truthfully** (this layer only records/validates; the truthfulness *audit* is `PRD_crypto`). A barrier placed **on the thief's cell = capture**.
- **FR-A4 — Terminal detection.** Detect (a) **capture** = cop and thief co-located, OR thief **fully boxed-in** (no legal move — all four neighbours out-of-bounds or barriered AND cop adjacent per config rule), OR barrier-on-thief (FR-A3); (b) **survival** = turn count reaches `survival_threshold` (=35) / `max_moves` (=35) with no capture.
- **FR-A5 — Scoring.** Terminal outcome → `(cop_score, thief_score)` looked up **from config `scoring`**: capture → `(20, 5)`; survival → `(5, 10)`; tie → `(2, 2)`; technical_loss → `(0, 0)`; `diversity_reward` (=10) added when the opponent is a new league group (flag passed in). No score literal appears in code.

## 3. Design

Exact names per PLAN §3 (`domain/`) and §4 (UML). All four files stay **≤150 lines raw AND logical** (NFR-8) — enforced by `check_file_lines.py` in CI from commit 1. Shared enums (`Direction`, `MoveType`, `Outcome`) live in `constants.py` (PLAN §3 "enum names / non-config literals only") so no duplication across modules (NFR-2).

### 3.1 `constants.py` (additive — enum names only, not config)
```python
class Direction(str, Enum):   # unit deltas resolved in Board, not here
    N = "N"; S = "S"; E = "E"; W = "W"; STAY = "STAY"

class Outcome(str, Enum):
    CAPTURE = "capture"; SURVIVAL = "survival"; TIE = "tie"
    TECHNICAL_LOSS = "technical_loss"

Cell = tuple[int, int]   # (row, col) — the canonical cell type, imported everywhere
```
`_DELTAS: dict[Direction, tuple[int,int]]` (the only geometry constant — pure enum-to-unit-vector map, not a config number) may live in `board.py`.

### 3.2 `domain/board.py` — geometry (FR-A1/A2)
`Board` is constructed with the config-supplied size; it holds **no game state** (barriers/positions are passed in), so it is a stateless geometry service — reused by both peers and by the strategy brain.

```python
class Board:
    def __init__(self, size: int) -> None: ...                       # size from config (FR-A1)
    def in_bounds(self, cell: Cell) -> bool: ...                     # 0 <= r,c < size
    def distance(self, a: Cell, b: Cell) -> int: ...                 # Manhattan |Δr|+|Δc|
    def neighbors(self, cell: Cell, barriers: frozenset[Cell]) -> list[Cell]: ...
        # in-bounds orthogonal cells not in barriers
    def target_of(self, cell: Cell, direction: Direction) -> Cell: ...  # apply unit delta
    def legal_moves(self, cell: Cell, barriers: frozenset[Cell]) -> list[Direction]: ...
        # every Direction whose target is in_bounds and not barriered; STAY always legal
    def step(self, cell: Cell, direction: Direction,
             barriers: frozenset[Cell]) -> Cell: ...
        # returns new cell; raises IllegalMoveError if target illegal (FR-A2)
```
Data shapes: `barriers` always a `frozenset[Cell]` (immutable, hashable, cheap membership). `legal_moves` returns `Direction` list ordered `[N,S,E,W,STAY]` for determinism (test-stable, reproducible replays).

### 3.3 `domain/rules.py` — adjudication (FR-A2/A3/A4)
Pure functions taking explicit positions/barriers (no hidden state). Depends only on `Board` + `constants`.
```python
def is_legal_move(board: Board, cell: Cell, direction: Direction,
                  barriers: frozenset[Cell]) -> bool: ...             # FR-A2
def validate_move(board: Board, cell: Cell, direction: Direction,
                  barriers: frozenset[Cell]) -> Cell: ...             # returns target or raises IllegalMoveError
def can_place_barrier(board: Board, cop: Cell, target: Cell,
                      barriers: frozenset[Cell], max_barriers: int) -> bool: ...
    # target adjacent to cop, in bounds, not already a barrier, len(barriers) < max_barriers (FR-A3)
def is_boxed_in(board: Board, thief: Cell, cop: Cell,
                barriers: frozenset[Cell]) -> bool: ...
    # thief has no legal non-STAY move AND cop adjacent (config toggle) (FR-A4)
def is_capture(cop: Cell, thief: Cell, board: Board,
               barriers: frozenset[Cell]) -> bool: ...               # co-location OR boxed-in (FR-A4)
def outcome(cop: Cell, thief: Cell, turn: int, board: Board,
            barriers: frozenset[Cell], *, survival_threshold: int) -> Outcome | None: ...
    # None = game continues; else CAPTURE / SURVIVAL (FR-A4)
```
`survival_threshold`/`max_barriers` are **passed in** from config — never read from a module constant.

### 3.4 `domain/scoring.py` — score table (FR-A5)
```python
class Scoring:
    def __init__(self, table: Mapping[str, Mapping[str, int]],
                 diversity_reward: int) -> None: ...   # table + reward from config "scoring"
    def score(self, outcome: Outcome, *, new_opponent: bool = False
              ) -> tuple[int, int]: ...                # (cop_score, thief_score)
    def technical_loss(self) -> tuple[int, int]: ...   # always (0, 0)
```
`table` shape (mirrors `game.json.scoring`): `{"capture": {"cop":20,"thief":5}, "survival": {"cop":5,"thief":10}, "tie": {"cop":2,"thief":2}, "technical_loss": {"cop":0,"thief":0}}`. `diversity_reward` (=10) added to the **relevant** side when `new_opponent` and outcome is scoring (per FR-K2 semantics; exact recipient documented as an open question §9). Zero literals — every number comes from the injected `table`.

### 3.5 `domain/own_state.py` — local peer truth (foundation for F2)
Holds **only the local peer's own** position/barriers/history — never the opponent's true cell (zero-trust boundary; the opponent's location is *inferred* later by `belief.py`).
```python
@dataclass
class OwnState:
    role: str                       # "police" | "thief"
    position: Cell
    barriers: frozenset[Cell] = frozenset()
    turn: int = 0
    history: tuple[Cell, ...] = ()  # own path, for replay/audit

    def moved_to(self, cell: Cell) -> "OwnState": ...     # immutable update → new OwnState
    def with_barrier(self, cell: Cell) -> "OwnState": ...  # cop only; adds barrier
    def advanced(self) -> "OwnState": ...                  # turn += 1, append to history
```
Immutable-update style (returns new instances) makes step logs trivially auditable and side-effect-free (supports `PRD_crypto` record bookkeeping and `PRD_reporting_gui` replay).

## 4. Edge cases & error handling

All raised errors come from `cipherchase/exceptions.py` (PLAN §3). This PRD adds/uses:
- **`IllegalMoveError`** — diagonal, out-of-bounds, or into/through a barrier (FR-A2). Raised by `Board.step` / `rules.validate_move`.
- **`IllegalBarrierError`** — non-adjacent target, out-of-bounds, duplicate cell, or `max_barriers` exceeded (FR-A3). Raised by a `rules.place_barrier` wrapper (thin) or surfaced via `can_place_barrier` returning `False` for the query path.

Edge cases explicitly handled and tested:
- Move off any of the 4 board edges from an edge/corner cell → illegal.
- `STAY` is **always** legal (even when fully boxed) — it is the safe default a stuck thief falls back to.
- Barrier requested on a cell already barriered, or on a non-adjacent cell, or when `len(barriers) == max_barriers` → rejected.
- Barrier placed exactly on the thief's current cell → **capture** (FR-A3), not an error.
- Simultaneous co-location and survival-threshold on the same turn → **capture takes precedence** (checked first in `outcome`).
- Thief boxed-in but cop **not** adjacent (config `require_cop_adjacent=true`) → **not** capture (still SURVIVAL-track); documented toggle.
- Empty/partial config → construction raises `KeyError`/`ConfigError` upstream (config layer), never silently defaults a number (NFR-11).

## 5. TDD test plan

Pure domain — **no externals to mock** (no LLM, MCP, or Gmail). Tests live in `tests/domain/` and use a small `fixture_config` dict standing in for `game.json.board_and_agents` / `movement_and_barriers` / `scoring`, proving config-driven behaviour by **varying the fixture** (e.g. a 5×5 board, a `max_barriers=2`, a mutated score) and asserting the engine follows the config, not a literal.

Happy paths:
- `Board`: `distance`, `in_bounds`, `neighbors` (corner=2, edge=3, center=4 neighbours), `legal_moves` on empty board, `step` for each of N/S/E/W/STAY.
- Two-piece legal move sequence (the Milestone scenario) — cop and thief each move and land where expected.
- Barrier placement adjacent to cop within budget → accepted; state updated via `OwnState.with_barrier`.
- Capture by co-location; capture by barrier-on-thief; boxed-in detection.
- Survival: run to `survival_threshold` with no capture → `Outcome.SURVIVAL`.
- Scoring: each outcome → correct tuple from the fixture table; `diversity_reward` applied when `new_opponent=True`.

Error paths:
- `step`/`validate_move` raise `IllegalMoveError` for out-of-bounds and into-barrier.
- Barrier: non-adjacent / duplicate / over-budget → `can_place_barrier` False (and wrapper raises `IllegalBarrierError`).
- Config-variation test: same code + a 5×5 fixture → `in_bounds((4,4))` True, `in_bounds((5,5))` False, proving NFR-11.

Asserted: return values, raised exception types, immutability of `OwnState` (original unchanged after `moved_to`), determinism of `legal_moves` ordering. Target **≥85% coverage** on all four modules (NFR-10) — trivially reachable for pure functions.

## 6. Milestone (binary) & Definition of Done

**Milestone (binary pass):** In a single test process, **two pieces move legally, are blocked at barriers, and an illegal move is rejected** — i.e. `Board.step` moves both a cop and a thief to expected cells, `legal_moves` excludes a barriered direction, and an out-of-bounds/into-barrier `step` raises `IllegalMoveError`. (PRD §9, Stage 1 row.)

**Definition of Done:**
- All FR-A1..A5 implemented across the four named modules; barrier + capture + survival + scoring correct.
- `ruff check (E,F,W,I,N,UP,B,C4,SIM)` = **0** (NFR-9).
- Every file ≤150 lines **raw and logical** per `check_file_lines.py` (NFR-8).
- `pytest --cov` on `domain/` ≥ **85%**, all green, happy + error paths (NFR-7/10).
- **Zero hardcoded** numbers — grid, starts, `max_barriers`, thresholds, scores all injected from config; proven by a config-variation test (NFR-11).
- No duplication; shared enums/`Cell` in `constants.py` (NFR-2). `domain/` imports nothing from `infra/peer/gui/shared.config`.
- CI (Py-3.13) green on the stage-1 branch before Stage 2 starts.

## 7. Traceability

| FR / NFR | Where satisfied |
|---|---|
| FR-A1 (grid + starts) | §3.2 `Board.__init__/in_bounds`; §3.5 `OwnState.position`; config-injected |
| FR-A2 (legal moves) | §3.2 `legal_moves/step`; §3.3 `is_legal_move/validate_move`; §4 `IllegalMoveError` |
| FR-A3 (barriers) | §3.3 `can_place_barrier`; §3.5 `OwnState.with_barrier`; §4 `IllegalBarrierError` |
| FR-A4 (capture/survival/boxed-in) | §3.3 `is_boxed_in/is_capture/outcome` |
| FR-A5 (scoring) | §3.4 `Scoring.score/technical_loss` |
| NFR-2 (no dup) | §3.1 shared enums/`Cell`; §6 DoD |
| NFR-7 (TDD) | §5 |
| NFR-8 (≤150) | §3 (each file), §6 DoD |
| NFR-9 (ruff 0) | §6 DoD |
| NFR-10 (cov ≥85%) | §5, §6 DoD |
| NFR-11 (zero hardcode) | §1 design rule; §3.2–3.4 config injection; §5 config-variation test |

## 8. Dependencies / open questions for other PRDs

**Consumed by (keep names stable):**
- `PRD_strategy` — `PoliceBrain`/`ThiefBrain` call `Board.legal_moves/distance/neighbors` and `rules.can_place_barrier`; the brain **chooses**, this layer **validates**. `Cell = tuple[int,int]` (row, col) is the shared coordinate contract for the whole codebase.
- `PRD_mcp_infra` — `TurnMessage.barrier_placed/capture_claim/win_claim` fields carry the truthful physical facts this engine produces; wire positions are `[row, col]` lists (JSON) ↔ `Cell` tuples.
- `PRD_crypto` — audit re-runs `rules`/`Board` on recorded steps; `OwnState.history` feeds the record trail; determinism of `legal_moves` ordering matters for byte-stable replays.
- `PRD_reporting_gui` — `Outcome` enum + `Scoring` output feed `result_<id>.json`; `OwnState` path feeds Replay.
- `PRD_language_scent` — `Board.neighbors`/`legal_moves` inform "prefer high-degree cells"; belief/scent live in separate modules and do not touch this PRD's purity.

**Open questions to resolve with siblings:**
1. **Coordinate origin** — confirm `Cell=(row,col)` with `[0,0]` top-left (cop) vs the spec's axis convention in `game.json.board_and_agents`; must match the opponent byte-for-byte (`PRD_mcp_infra`/interop contract §8). *Proposed: (row, col), origin top-left.*
2. **Boxed-in definition** — does "fully boxed" require the cop to be orthogonally adjacent, or is any no-legal-move state a capture? Config toggle `require_cop_adjacent` proposed; final value set in `game.json.movement_and_barriers` and must be agreed with opponents.
3. **`diversity_reward` recipient** — does the +10 go to both sides, the local peer only, or the winner? Owned jointly with `PRD_reporting_gui`/FR-K2; `Scoring.score` currently applies it to both scoring sides pending confirmation.
4. **Move-collision / same-cell timing** — if cop and thief would occupy the same cell after simultaneous resolution, is that always a capture regardless of who moved? Sequencing is owned by `PRD_crypto`/`PRD_mcp_infra` turn order; this layer treats co-location as capture whenever evaluated.
