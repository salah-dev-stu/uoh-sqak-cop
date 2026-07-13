# PRD — Strategy Brain (Stage 3, the graded move brain)

| Field | Value |
|---|---|
| **Mechanism** | Strategy brain — Bayesian belief + heuristic pursuit/evasion (the intellectual core & graded deliverable) |
| **Stage** | 3 of 7 (build order: after Stage 1 base-logic + Stage 2 MCP infra) |
| **Chapter** | Ch6 (Strategy & the algorithmic move brain) |
| **Gate** | **F8 — MOVE IS ALWAYS ALGORITHMIC; the LLM writes trash-talk only, never a move** |
| **FRs covered** | FR-C1, FR-C2, FR-C3, FR-C4, FR-C5 |
| **NFRs in play** | NFR-2 (OOP/no-dup), NFR-7 (TDD), NFR-8 (≤150 raw+logical), NFR-9 (ruff 0), NFR-10 (cov ≥85%), NFR-11 (zero hardcoding) + **Computational Fairness** |
| **Version** | 1.00 (single-source `shared/version.py`) |
| **Status** | Gate-2 per-mechanism draft — approve before code |
| **Milestone (binary)** | With a **known** target cell, the agent computes and executes a path to it autonomously, using zero LLM tokens. |

---

## 2. Purpose & scope

This is **the graded core**. The rubric scores *systems engineering and algorithmic cleverness*, not winning; the four metrics (Coordination, Adaptation, Integrity, Architecture) plus **Computational Fairness** all converge here. The brain must:

1. Prove **F8**: every move is produced by deterministic pure-Python code. The LLM (Stage 4) only decorates a move with bluff text and can be entirely absent while the game runs to completion.
2. Turn **partial observation** (Dec-POMDP: an agent never sees the opponent's true cell, only a scent-intensity field + its own exclusions) into a **Bayesian belief map**, and drive pursuit/evasion from `most_likely()`.
3. Expose a **clean student seam** (FR-C4) so a brain is swapped by config with **no engine change** — this is what makes expectimax/Q-learning (FR-C5) additive, never on the critical path.
4. Stay **cheap and clever** on an 8 GB M2: heuristics are O(cells) per turn; the optional expectimax is depth-bounded; RL is tabular. Brute force is explicitly rejected (Computational Fairness).

**In scope:** `domain/brains.py`, `domain/belief.py`, `strategy/factory.py`, `strategy/police_heuristic.py`, `strategy/thief_heuristic.py`, and the *optional* `strategy/police_expectimax.py` + `strategy/qlearning.py`.

**Out of scope (owned elsewhere):** the scent *field* math and LLM hint text (`domain/smell.py`, `strategy/trash_talk.py` → **Stage 4 / `PRD_language_scent.md`**); board geometry & legality (`domain/board.py`, `domain/rules.py` → Stage 1); commit-reveal binding of the chosen `Intent` (Stage 6). This PRD **consumes** the Stage-1 `Board` and **shares** the belief/smell contract with Stage 4 (see §10 hand-off).

---

## 3. Requirements

### Functional

- **FR-C1 — Algorithmic seam & base class.** `domain/brains.py` defines `BrainBase` (abstract) plus the `Decision` dataclass. `BrainBase._pick_move(...)` and `BrainBase._decide_move(...)` **raise `NotImplementedError`**; `PoliceBrain`/`ThiefBrain` override them. `decide()` is concrete pure-Python. **No branch of the move computation may call an LLM** (F8). *(NFR-8: split across files if either brain nears 150 logical lines.)*
- **FR-C2 — Bayesian belief map.** `domain/belief.py` `BeliefGrid` maintains a prior over all 49 cells; `observe_smell()` applies a scent-intensity likelihood (weighted by `smell_trust`), `exclude()` zeroes provably-empty cells, `diffuse()` spreads mass over orthogonal adjacency each turn, renormalizing; `most_likely()` returns the argmax cell.
- **FR-C3 — Heuristic baseline.** `PoliceBrain` = greedy Manhattan step toward the belief argmax **plus** a barrier-placement heuristic that maximally cuts the thief's reachable set (box-in / min-cut intuition). `ThiefBrain` = pick the legal move maximizing distance from cop belief-mass while preferring high-degree (more-exit) cells; climb scent **away** from the cop.
- **FR-C4 — Student seam.** `strategy/factory.py` resolves `police_class`/`thief_class` = `"package.module:Class"` from `game.toml [strategy]`. Swapping a brain requires **no engine change** — the engine only ever sees `BrainBase`.
- **FR-C5 — Excellence (OPTIONAL, config-gated, never critical path).** `strategy/police_expectimax.py` (depth-limited expectimax over the belief map) and `strategy/qlearning.py` (tabular Q over belief-summary features + committed learning-curve artifact). Selected purely by pointing `police_class`/`thief_class` at them; default config never does.

### Non-functional (this stage)

- **NFR-C-a (F8 hard gate).** A test asserts no LLM/provider/`subprocess` symbol is reachable from `BrainBase.decide` or either subclass. Move output is a function of `(state, belief, config, seed)` only.
- **NFR-C-b (determinism / Computational Fairness).** Given a fixed `seed`, `decide()` is **totally deterministic**; all tie-breaks resolve via a seeded RNG. Per-turn cost is O(cells) for heuristics; expectimax is O(b^d) with `d≤2`, `b≤5`; no per-turn allocation beyond the 49-cell grid.
- **NFR-C-c (purity).** `domain/belief.py` and `domain/brains.py` import **nothing** from `infra/`, `peer/`, or `gui/` (PLAN dependency rule).
- **NFR-C-d (line budget).** Each file ≤150 raw **and** logical lines (`check_file_lines.py`); shared scoring helpers extracted to avoid duplication (NFR-2).

---

## 4. Design

### 4.1 `BrainBase` seam + `Decision` (`domain/brains.py`)

```python
# domain/brains.py  (target ≤120 logical lines)
from dataclasses import dataclass, field

@dataclass(frozen=True)
class Decision:
    move_type: str        # "move" | "stay" | "barrier"
    direction: str        # "N"|"S"|"E"|"W"|"STAY"
    hint: str = ""        # NL text — filled by Stage-4 trash_talk, NOT by the brain
    verdict: str = "truth"  # Intent bound into the commit: "truth" | "lie"
    fallback: bool = False  # True if a degenerate/STAY fallback fired
    random_move: bool = False  # True if a seeded tie-break/uniform pick was used
    response_seconds: float = 0.0  # brain compute time (telemetry, not scored)
    prompt_text: str = ""  # optional prompt handed to the LLM layer (Stage 4)
    reasoning: str = ""    # short algorithmic trace for logs/replay (audit-friendly)
    barrier_cell: tuple[int, int] | None = None  # cop only; None for thief

class BrainBase:
    def __init__(self, board, config, rng): ...
    def decide(self, state, belief) -> Decision:
        """Concrete, pure-Python. Times the pick, wraps it in a Decision,
        stamps response_seconds/reasoning. NEVER calls an LLM (F8)."""
        ...
    def _pick_move(self, state, belief):        # thief-style pure move
        raise NotImplementedError
    def _decide_move(self, state, belief):      # cop-style move+barrier
        raise NotImplementedError
```

- `decide()` measures `perf_counter()` around the subclass hook, sets `reasoning`/`response_seconds`, and returns the frozen `Decision`. `hint`, `verdict`, and `prompt_text` are placeholders the **Stage-4 trash-talk layer** fills in; the brain leaves `verdict="truth"` and `hint=""` by default so the physical board stays truthful (F6/F7 live in Stage 4).
- Both hooks return a light internal tuple `(move_type, direction, barrier_cell, random_move, fallback, reasoning)` that `decide()` packs — keeps subclasses tiny and DRY.

### 4.2 `BeliefGrid` math (`domain/belief.py`)

State: a 7×7 matrix `P` of non-negative masses summing to 1 (uniform prior `1/49`). Config: `smell_trust ∈ [0,1]`, diffusion `alpha` (self-retention), and grid `size` — all from `game.toml [belief]`, never literals (NFR-11).

**Signatures**

```python
class BeliefGrid:
    def __init__(self, size: int, smell_trust: float, alpha: float, rng): ...
    def observe_smell(self, smell_cells: dict[tuple[int,int], float]) -> None: ...
    def exclude(self, cells: Iterable[tuple[int,int]]) -> None: ...
    def diffuse(self) -> None: ...
    def most_likely(self) -> tuple[int, int]: ...
    def as_matrix(self) -> list[list[float]]: ...     # for the GUI heatmap (FR-G4)
    def mass_at(self, cell) -> float: ...
```

**(a) Bayesian update — `observe_smell` (FR-C2).** Scent intensity `τ(c) ∈ [0,1]` is evidence the opponent is at/near `c`. Likelihood blends the observation with trust so a possibly-lying field cannot dominate:

```
L(c)  = smell_trust · τ(c) + (1 − smell_trust) · (1/N)      # N = live cells
P'(c) = P(c) · L(c)
P(c)  = P'(c) / Σ_k P'(k)                                    # renormalize
```

`smell_trust=1` ⇒ pure Bayesian scent tracking; `smell_trust=0` ⇒ scent ignored (belief drifts on diffusion only). This is the tunable exposed to the OAT sensitivity analysis (G5).

**(b) `exclude`** — hard evidence sets `P(c)=0` for: the observer's own cell (co-location would be capture, already handled by rules), any cell **seen empty**, and (for the cop) barrier cells the thief cannot occupy. Renormalize after zeroing. If exclusion empties the grid (all-zero), fall back to uniform over remaining live cells (see §6).

**(c) `diffuse` — motion model (FR-C2).** Between turns the opponent may move one orthogonal step, so mass spreads:

```
P_next(c) = alpha · P(c)  +  (1 − alpha) · Σ_{n ∈ orth_nbrs(c)} P(n) / deg(n)
```

`deg(n)` counts *in-bounds, non-barrier* orthogonal neighbours, so probability is conserved on the bounded board (no leakage off-edge / into walls). Renormalize for float safety.

**(d) `most_likely`** = `argmax_c P(c)`, ties broken deterministically by the seeded RNG (NFR-C-b) then by `(row, col)` order.

### 4.3 `PoliceBrain` — pursuit + barrier box-in (`strategy/police_heuristic.py`)

Two coupled decisions per turn: **where to step** and **whether/where to drop a barrier**. Target `t = belief.most_likely()`.

**Movement — greedy Manhattan descent.** Among `board.legal_moves(self_pos, barriers)`, score each resulting cell `c'`:

```
score_move(c') =  −manhattan(c', t)                 # get closer to belief mass
                  + w_center · (−manhattan(c', center))   # tiny centrality tie-break
                  + w_belief · belief.mass_at(c')    # prefer high-probability cells
pick = argmax score_move ; ties → seeded RNG
```

`w_center` (~0.01) and `w_belief` (~0.5) come from config. Pure Manhattan alone can stall on symmetric ties; the belief-mass term breaks them toward where the thief probably is.

**Barrier placement — reachable-set / min-cut heuristic (the sophisticated bit).** The cop may drop one barrier on a cell orthogonally adjacent to *itself* per turn (Stage-1 rule), up to `max_barriers`. Evaluate each candidate barrier cell `q` by how much it shrinks the thief's escape:

```
def reach(from_cell, barriers):        # BFS over orthogonal, non-barrier, in-bounds
    return set of cells reachable within HORIZON steps       # HORIZON from config

R0 = reach(t, barriers)                         # thief's current reachable set
for q in candidate_barrier_cells(self_pos):     # adjacent, empty, not thief-cell
    Rq = reach(t, barriers ∪ {q})
    gain(q) = |R0| − |Rq|                        # cells of freedom removed
    # bonus for true articulation points (a cut that severs a whole region):
    if splits_region(t, q): gain(q) += cut_bonus
score_barrier(q) = gain(q) − lambda · manhattan(q, t)   # prefer cuts near the thief
```

Place the barrier only if `max(gain) ≥ min_gain` **and** it does not fully wall the cop off from pursuit; otherwise skip the barrier this turn and just step. This is a cheap greedy approximation to a min-cut/box-in: each turn removes the most freedom for O(cells) BFS cost. `HORIZON`, `cut_bonus`, `lambda`, `min_gain` are config.

`_decide_move` returns the step **and** an optional `barrier_cell`; capture-by-boxing emerges naturally when `reach(t) → {t}`.

> If the two heuristics push the file over 150 logical lines, extract the BFS/reachable helpers into `strategy/reach.py` (shared with expectimax) — keeps NFR-8/NFR-2.

### 4.4 `ThiefBrain` — evasion along the gradient (`strategy/thief_heuristic.py`)

The thief never sees the cop's true cell — it evades the **cop belief-mass** (its own `BeliefGrid` over the cop, fed by the cop's scent field) and prefers cells with more exits so it stays hard to trap.

```
danger = thief_belief.most_likely()             # most-likely cop cell
for c' in board.legal_moves(self_pos, barriers):
    dist   = manhattan(c', danger)              # farther from the cop = safer
    exits  = len(board.neighbors(c', barriers)) # high-degree = more escape routes
    scent  = -own_scent_intensity_at(c')        # climb AWAY from own fresh trail (anti-track)
    risk   = thief_belief.mass_at(c')           # avoid high cop-probability cells
score_evade(c') =  w_dist · dist
                 + w_exits · exits
                 + w_scent · scent
                 − w_risk · risk
pick = argmax score_evade ; ties → seeded RNG ; if none improves → STAY (fallback)
```

Weights `w_dist, w_exits, w_scent, w_risk` from `game.toml [strategy]`. `exits` is the "prefer high-degree cells" requirement — a corner (2 exits) is a death trap against a boxing cop, so the thief drifts toward open, well-connected cells. The `w_scent` term implements "climb scent away": the thief moves off its own strengthening trail so the cop's Bayesian tracker gets a colder signal. `_pick_move` returns a pure move (no barriers for the thief).

### 4.5 Factory / seam resolution (`strategy/factory.py`)

```python
def load_brain(spec: str, board, config, rng) -> BrainBase:
    module_path, _, cls_name = spec.partition(":")   # "pkg.mod:Class"
    module = importlib.import_module(module_path)
    cls = getattr(module, cls_name)
    brain = cls(board, config, rng)
    if not isinstance(brain, BrainBase):
        raise ConfigError(f"{spec} is not a BrainBase")   # from cipherchase.exceptions
    return brain
```

- `police_class` / `thief_class` read from `game.toml [strategy]` (e.g. `"cipherchase.strategy.police_heuristic:PoliceBrain"`). Defaults point at the heuristics; FR-C5 is a one-line config change to `...police_expectimax:ExpectimaxPoliceBrain` or `...qlearning:QLearningThiefBrain`.
- Bad spec / non-BrainBase / missing symbol → typed `ConfigError`, never a silent import crash. The **engine (`peer/`) only ever holds a `BrainBase`** — proving FR-C4's "no engine change to swap."

---

## 5. Excellence extensions (OPTIONAL — FR-C5, behind the FR-C4 seam)

Both are selected *only* by config and are **never** on the critical path; the default series ships the heuristic baseline.

### 5.1 Depth-limited expectimax over the belief map (`police_expectimax.py`)

The cop treats the thief as a chance node distributed by the belief `P`. Value of a cop action `a` from state `s` at depth `d`:

```
V(s, d) = eval(s)                                   if d = 0 or terminal
MAX node (cop):   V(s, d) = max_{a ∈ cop_moves∪barriers} V(apply(s,a), d−1)
CHANCE (thief):   V(s, d) = Σ_{c} P(c) · V(place_thief(s,c), d−1)
                            over the top-K belief cells (K,d from config)
eval(s) = −manhattan(cop, E_P[thief])  −  β · |reach(thief)|   # box-in pressure
```

Depth `d≤2`, branching pruned to the **top-K** belief cells (K≈5) ⇒ O((5·5)^d) ≈ a few hundred evals/turn — cheap on the M2 (Computational Fairness). Reuses `strategy/reach.py`. Returns a `Decision` identical in shape to the heuristic, so the engine is oblivious.

### 5.2 Tabular Q-learning (`qlearning.py`) — MDP formulation

- **State (belief-summary features, discretised):** `(sign(Δrow), sign(Δcol))` from self to `most_likely()`, bucketed `manhattan` distance (near/mid/far), and bucketed local exit-count. Keeps the table small (~hundreds of entries) — deliberately *not* the raw 49-cell grid (Computational Fairness; avoids brute force).
- **Actions:** `N/S/E/W/STAY` (+ `barrier` for the cop variant).
- **Reward:** `+R_capture` (cop) / `+R_survive` (thief) at terminal; `−step_penalty` each turn (pushes the cop to end fast, rewards the thief for stalling); shaping `+γ·Δ(−manhattan)` optional.
- **Update:** `Q(s,a) ← Q(s,a) + η·[r + γ·max_a' Q(s',a') − Q(s,a)]`, ε-greedy exploration with decaying ε; seeded RNG for reproducibility.
- **Artifact (G5):** an offline trainer script produces `docs/sample-run/qlearning-curve.png` (reward/episode + capture-rate learning curve) and a pickled/JSON Q-table loaded read-only at play time. Training is **never** invoked on the critical path; if the table is absent the brain falls back to the heuristic policy.

---

## 6. Edge cases & error handling

| Case | Handling |
|---|---|
| **No legal move** (fully walled) | `Decision(move_type="stay", direction="STAY", fallback=True)`; cop-boxing of the *thief* here is a capture handled by Stage-1 rules, not an error. |
| **Ties in any argmax** | Deterministic: seeded RNG picks among maxima (`random_move=True`), then stable `(row,col)` order — reproducible given `seed` (NFR-C-b). |
| **Belief all-zero** (over-exclusion / empty likelihood) | `most_likely()` and `observe_smell` renormalize; if total mass is 0, reset to **uniform over live (non-barrier, in-bounds) cells** and set `fallback=True`. Never divide by zero. |
| **Empty smell field** (no scent yet, turn 0) | `observe_smell({})` is a no-op; belief stays at diffused prior; cop pursues board center as a sane default. |
| **Barrier would self-trap the cop** | Reject candidates that disconnect the cop from any thief-reachable region; skip barrier, just step. |
| **Bad `police_class`/`thief_class` spec** | `factory.load_brain` raises typed `ConfigError` at startup (fail fast, never mid-game). |
| **`max_barriers` exhausted** | Barrier heuristic disabled for the rest of the game; cop degrades gracefully to pure Manhattan pursuit. |
| **NaN/negative float from config weights** | `BeliefGrid`/brain constructors validate config ranges, raise `ConfigError`. |

---

## 7. TDD test plan (NFR-7/10 — externals mocked, **no LLM in any move test**)

Red→Green→Refactor; all deterministic via fixed `seed`. Target ≥85% coverage of the five files.

**Belief (`test_belief.py`)**
- `observe_smell` moves mass toward high-`τ` cells and stays normalized (Σ=1 ± ε).
- `exclude` zeroes named cells and renormalizes; excluding all → uniform-live fallback, `fallback` path hit.
- `diffuse` conserves total mass on a bounded board with barriers (Σ before == Σ after).
- `most_likely` argmax + **deterministic** tie-break under a fixed seed.
- `smell_trust=0` ⇒ scent ignored; `=1` ⇒ pure Bayesian — parametrized.

**Police heuristic (`test_police_brain.py`)**
- **Path convergence:** given a *known* fixed target and no barriers, repeated `decide()` strictly reduces `manhattan(cop, target)` and reaches it within `≤ manhattan(start,target)` turns (the **Milestone** assertion).
- **Barrier reduces reachable set:** after a placed barrier, `|reach(thief)|` strictly decreases vs. before; a chosen articulation-point barrier splits the region.
- Self-trap candidates are rejected (cop stays connected to thief region).
- `max_barriers` exhaustion ⇒ still returns a legal move.

**Thief heuristic (`test_thief_brain.py`)**
- Chooses the legal move that **increases** distance from `danger` when one exists.
- Prefers the higher-degree cell when distances tie (exit-count term dominates).
- No legal move ⇒ `STAY` + `fallback=True`.

**Seam & F8 (`test_factory.py`, `test_f8_no_llm.py`)**
- `load_brain` resolves `"pkg.mod:Class"` and returns a `BrainBase`; bad spec ⇒ `ConfigError`.
- Swapping `police_class` to a stub brain changes moves **with no engine edit**.
- **F8 guard:** patch/spy the provider + `subprocess.run`; run a full heuristic game via `FakeTransport`; assert the provider was **never called** and every move still produced — the game completes at **0 tokens**.

**Optional (`test_expectimax.py`, `test_qlearning.py`)** — run only if the files exist: expectimax value monotonicity vs. depth; Q-update rule arithmetic; absent-table fallback to heuristic.

---

## 8. Milestone (binary) + Definition of Done

**Milestone (binary):** With a **known** target cell injected into belief (or passed directly), `PoliceBrain` computes and executes a path that reaches the target autonomously, deterministically, and with **zero LLM tokens** — asserted by `test_police_brain.py::test_path_convergence`.

**Definition of Done (Stage 3):**
- `domain/brains.py`, `domain/belief.py`, `strategy/factory.py`, `strategy/police_heuristic.py`, `strategy/thief_heuristic.py` implemented, each ≤150 raw+logical (`check_file_lines.py` green).
- `ruff check` = 0; `pytest --cov` ≥85% on the five files with LLM/MCP/Gmail mocked.
- **F8 guard test passes** (no LLM reachable from any move path).
- Factory swaps a brain with no engine change (FR-C4 proven by test).
- Belief math tests (normalization, diffusion conservation, exclusion fallback) green.
- Config-driven weights/horizons — zero hardcoded numbers (NFR-11).
- *(Optional)* expectimax/Q-learning present behind the seam **only if** time allows; their absence does not block DoD.

---

## 9. Traceability

| Requirement / Gate | Design section | Test |
|---|---|---|
| **F8** (move always algorithmic) | §4.1 `BrainBase`, NFR-C-a | `test_f8_no_llm.py` |
| **FR-C1** BrainBase + Decision + NotImplementedError hooks | §4.1 | `test_factory.py`, brain tests |
| **FR-C2** Bayesian belief (observe/exclude/diffuse/most_likely) | §4.2 | `test_belief.py` |
| **FR-C3** heuristic pursuit + barrier box-in / evasion | §4.3, §4.4 | `test_police_brain.py`, `test_thief_brain.py` |
| **FR-C4** student seam (`package.module:Class`) | §4.5 | `test_factory.py` |
| **FR-C5** expectimax + Q-learning (optional) | §5 | `test_expectimax.py`, `test_qlearning.py` |
| **NFR-2/8** OOP/no-dup, ≤150 lines | §4.3 note (extract `reach.py`) | `check_file_lines.py` |
| **NFR-7/10** TDD, cov ≥85% | §7 | CI |
| **NFR-11** zero hardcoding | all `[belief]`/`[strategy]` config | config tests |
| **Computational Fairness** | §4.2–4.4 O(cells), §5 bounded | perf assertions |
| **Milestone** | §8 | `test_path_convergence` |

---

## 10. Dependencies & open questions

**Depends on (already built / defined):**
- Stage 1 `domain/board.py` — `distance`, `in_bounds`, `neighbors(cell, barriers)`, `legal_moves`, `step`; `domain/rules.py` for capture/boxed-in adjudication.
- `shared/config.py` — `game.toml [belief]` (`smell_trust`, `alpha`, `size`) and `[strategy]` (`police_class`, `thief_class`, all scoring weights/horizons).
- `shared/version.py`, `cipherchase/exceptions.py::ConfigError`, a seeded RNG passed by `peer/`.

**Shared contract the Stage-4 language/scent PRD (`PRD_language_scent.md`) MUST match:**
1. **Smell → belief interface.** `BeliefGrid.observe_smell()` consumes a `dict[(row,col) -> intensity ∈ [0,1]]`. `domain/smell.py` (Stage 4) must expose the opponent's field in exactly that shape (its `strongest_cell`/`snapshot` feed this dict). Field is **intensity only, never opponent coordinates** (F7).
2. **`smell_trust`** is a single source of truth in `game.toml [belief]` — the same weight the scent decay design references; do not duplicate it in `[trash_talk]`.
3. **`Decision` fields `hint`, `verdict`, `prompt_text`** are written by the Stage-4 trash-talk layer, not the brain. Stage 4 must keep `verdict` consistent with the truthful physical board (bluff allowed in `hint` text only; F6). The brain always emits `verdict="truth"` and empty `hint` as the safe default.
4. **Deposit/decay** (`ρ=0.10`, center `0.9`, 5×5) live in Stage 4; this PRD only *reads* the resulting field — no scent mutation happens in `domain/belief.py` or the brains.

**Open questions (for approval):**
- **Q1** Default weight values (`w_belief`, `w_dist`, `w_exits`, `w_scent`, `w_risk`, `alpha`, `HORIZON`, `lambda`, `min_gain`) — propose sensible defaults now and tune via the G5 OAT sensitivity sweep, or lock provisional values in `game.toml` at build time? *(Recommend: provisional defaults, OAT later.)*
- **Q2** Does the thief maintain its **own** `BeliefGrid` over the cop (symmetric design, cleanest) — confirmed assumed in §4.4 — or a lighter last-seen-scent heuristic? *(Recommend: symmetric BeliefGrid; reuse the same class.)*
- **Q3** Ship **either** expectimax **or** Q-learning for FR-C5 excellence (not both) to protect the timeline? *(Recommend: expectimax first — deterministic, no training artifact risk; Q-learning only if slack remains.)*
