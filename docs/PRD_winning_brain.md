# PRD — Championship Brain (Phase P2: the league-points engine)

| Field | Value |
|---|---|
| **Mechanism** | Championship brain — scent-delta belief decoding + herd-to-corner pursuit + wall discipline + hardened evader + committed benchmark lab |
| **Phase** | **P2** of PLAN-CHAMPIONSHIP (Jul 23 – Aug 2); independent of P1, builds on P0's truthful foundations |
| **Gates** | **F7** (scent = intensity only, never coordinates) · **F8** (move ALWAYS algorithmic; LLM writes text only) |
| **Extends** | `PRD_strategy.md` (Stage 3). The `BrainBase` seam, `Decision`, `BeliefGrid`, and the factory are **unchanged**. |
| **Baselines** | `PoliceBrain`, `ThiefBrain`, `PoliceExpectimax` are **KEPT untouched** as seam alternatives and regression anchors. |
| **New modules** | `domain/scent_decode.py` · `strategy/police_herder.py` · `strategy/thief_evader_v2.py` · `strategy/archetypes.py` · `scripts/benchmark_lab.py` |
| **NFRs** | ≤150 raw+logical per file · ruff 0 · cov stays **100%** · zero hardcoding (all weights in `game.toml [strategy]`) · pure Python, **0 tokens** · TDD |
| **Version** | 1.00 (single-source `shared/version.py`) |
| **Status** | Gate-2 per-mechanism draft — approve before code |
| **Milestone (binary)** | `uv run python scripts/benchmark_lab.py --fast` prints a win-rate matrix in which `HerderCop` captures ≥90% vs every naive archetype and `EvaderBrain` survives ≥95% vs `HerderCop`, under **realistic (delta-belief) information**, deterministically from `[play].seed`. |

---

## 2. Measured problem statement (why the baseline cannot win the league)

The strategy lab (`league_eval.py` / `league_eval2.py`, N=120 games per cell,
randomized starts with min separation 4, seeds `1000+s`) measured the shipped
brains. **Capture-rate %** (mean turns / capture kinds omitted here; full
matrices reproduced by the lab, §7):

| capture-rate % | ThiefBrain | NaiveEdge | Random | Still |
|---|---|---|---|---|
| PoliceBrain (ours) | **0.0** | **0.0** | 30.8 | 14.2 |
| PoliceExpectimax | **0.0** | **0.0** | 37.5 | 9.2 |

A cop that captures **0%** vs *any* thief that moves purposefully scores 5/20
league points per opponent, forever. Three root causes, each measured:

1. **Phantom-trail belief plateau.** Mean belief error (argmax vs true thief)
   = **3.46 cells**. The scent field saturates (`deposit` caps at 1.0, decay is
   only 10%/turn) into a broad plateau over the thief's *history*; the argmax
   sits on old trail, not the thief. The cop chases a ghost. Worse, `game_loop`
   builds a **fresh `BeliefGrid` every turn**, throwing away all accumulated
   evidence — the "Bayesian" filter never actually filters across time.
2. **Greedy-parity stall.** Greedy Manhattan descent can close to distance 1
   but never to 0 against an evader that also moves: both move once per turn,
   so parity is conserved and the evader side-steps forever. Measured: mean
   distance *grows* from first-5 to last-5 turns in surviving games; dozens of
   "reached dist ≤ 2 then escaped" events per game.
3. **Squandered barriers.** Mean **10/14 barriers** placed far from the thief
   (the `min_gain` filter passes any cell that clips one reachable cell —
   usually near the *cop*, early), and across all 960 baseline games there were
   **zero boxed-in captures**. The one mechanism that beats parity (walls don't
   move) is spent by turn 10 on noise.

**Oracle ablation** (`league_eval2.py`: cop fed the *true* thief cell): perfect
information lifts PoliceBrain vs NaiveEdge to only **22.5%**. Conclusion:
belief must be fixed **and** the chase policy itself must change — herding +
walls, not greedy pursuit. The only lab probe that captured a real evader
combined all three fixes below.

---

## 3. Fix 1 — Delta-belief decoder (`domain/scent_decode.py`)

### 3.1 Insight

The scent field is *additive with known decay*: every turn the thief deposits a
5×5 Chebyshev kernel (center `c_int = 0.9`, falloff `f = 0.7`) and the whole
field decays by `ρ = 0.1` (all from `game.toml [pheromones]`). Therefore the
**difference between what we see and what pure decay predicts is exactly the
fresh deposit**, and its argmax is the thief's *current* cell:

```
Δ(c) = τ_t(c) − (1 − ρ) · τ_{t−1}(c)          # observed minus predicted decay
argmax_c Δ(c) ≈ thief's cell at t              # fresh kernel center = 0.9·f⁰ = 0.9
```

The kernel is unimodal (`0.9·f^d`, Chebyshev `d`), so absent saturation the
argmax of `Δ` **is** the deposit center — near-oracle accuracy from 100% legal
information (an intensity map only crosses the wire, F7). This holds under
either deposit/decay ordering (if the engine decays the fresh deposit in the
same turn — audit §2.3-8, fixed in P0 — `Δ(c) = (1−ρ)·dep(c)`: same argmax,
scaled constant).

### 3.2 Class contract

```python
# domain/scent_decode.py  (pure domain: imports only constants; ~60 logical lines)
class ScentDecoder:
    def __init__(self, decay: float, delta_floor: float, tie_ratio: float): ...
    def decode(self, snapshot: dict[str, float], step: int) -> dict[str, float] | None:
        """Return a Δ-evidence map for BeliefGrid.observe_smell, or None if ambiguous."""
```

State: `self._prev: dict[str, float] | None`, `self._prev_step: int`.

```
decode(snapshot, step):
    if _prev is None:                      # FIRST TURN: no baseline yet —
        _prev, _prev_step = snapshot, step #   return snapshot as-is (raw field is
        return dict(snapshot)              #   still evidence, just blurrier)
    gap = step − _prev_step                # MISSED TURN(S) (e.g. hint-only turn,
    pred(c) = (1 − ρ)^gap · _prev(c)       #   replay skip): decay the baseline
    Δ(c) = max(0, snapshot(c) − pred(c))   #   gap times, never assume gap == 1
    _prev, _prev_step = snapshot, step
    Δmax = max(Δ.values(), default=0)
    if Δmax < delta_floor: return None                     # ambiguity case A
    ties = {c : Δ(c) ≥ tie_ratio · Δmax}
    if not chebyshev-coherent(ties): return None           # ambiguity case B
    return Δ                               # feed to belief.observe_smell(Δ)
```

### 3.3 Saturation-cap edge case — when is Δ ambiguous?

`SmellField.deposit` clamps: `τ ← min(1.0, τ + dep)`. If the thief lingers, the
center clamps once `(1−ρ)·τ_prev + 0.9 > 1.0`, i.e. **whenever
`τ_prev > 0.111`** — after a single revisit. Then the observed
`Δ(center) = 1.0 − (1−ρ)·τ_prev < 0.9` shrinks toward `ρ·1.0 = 0.1` while
un-clamped ring cells shrink less uniformly, so the argmax can smear.
Quantified trigger and fallback:

- **Case A — flat delta:** `Δmax < delta_floor` (default `0.05` — well below
  the un-clamped ring-1 deposit `0.9·0.7·(1−ρ) ≈ 0.57` yet above float noise
  and deep-saturation residue `ρ·τ ≤ 0.1` only when clamping is total).
- **Case B — incoherent ties:** the near-tied set `{c : Δ(c) ≥ tie_ratio·Δmax}`
  (default `tie_ratio = 0.8`) does not fit inside one Chebyshev-radius-1 block
  (a genuine kernel's top cells always do).

In either case `decode` returns `None` and the brain **falls back to the
persistent belief** (§3.4), which has integrated every previous turn — the
plateau still localizes a lingering thief because a lingering thief is *at* the
plateau peak. Saturation is thus self-correcting: clamping only happens when
the thief stays put, which is exactly when stale belief is accurate.

### 3.4 Persistent belief (never reset)

`BeliefGrid` is unchanged; the **usage** changes. Each side owns ONE grid for
the whole game (created at game start, held by the brain wrapper in
`sdk/game_loop.py` / `peer` runtime):

```
each turn:  ev = decoder.decode(snapshot, step)
            if ev is not None: belief.observe_smell(ev)   # Bayesian update
            belief.exclude(own_cell); belief.exclude(b) for b in new_barriers
            belief.diffuse()                              # motion model, α=0.85
```

Observe→exclude→diffuse **across turns, never reconstructed** — this alone
collapses the measured 3.46-cell error; with delta evidence the lab probes ran
near-oracle. First turn with an empty snapshot (`{}`): decoder stores it,
returns `{}`; `observe_smell({})` is a no-op and belief stays uniform —
identical to today's cold start.

---

## 4. Fix 2 — `HerderCop` (`strategy/police_herder.py`)

`class HerderCop(PoliceBrain)` — inherits `_candidates`/weight plumbing, over-
rides `_pick_move` and `_pick_barrier`. Capture philosophy: **capture is via
boxing (walls + adjacency), never co-location** — walls don't move, so parity
cannot save the thief. All constants below are config keys in
`game.toml [strategy]` (names in `code font`); nothing is hardcoded.

### 4.1 Approach-from-anti-corner scoring (herding phase)

Drive the thief's best-escape set toward the nearest corner by always standing
on the *open-board side* of it:

```
t  = belief.most_likely()                         # delta-decoded believed thief
k* = argmin_{k ∈ corners} manhattan(t, k)         # thief's nearest corner
g  = (t.row + sgn(t.row − k*.row),                # "ghost" chase point: one cell
      t.col + sgn(t.col − k*.col))                #   anti-corner-ward of the thief
if g out of bounds: g = t
for d in board.legal_moves(pos, barriers):
    c' = target_of(pos, d)
    score(c') = − manhattan(c', g)                          # herd from the open side
                − herd_tether · manhattan(c', t)            # …but never lose contact
                + w_belief · belief.mass_at(c')             # tie-break toward mass
pick = argmax score;  near-ties (within tie_eps) → seeded RNG
```

Defaults: `herd_tether = 0.3`, `tie_eps = 1e-9`. Standing anti-corner-ward
makes every thief "safest" move point corner-ward; the corner shrinks its
reachable set for free.

### 4.2 Phase switch → boxing mode

```
wall_dist(t) = min(t.row, size−1−t.row, t.col, size−1−t.col)
BOXING iff wall_dist(t) ≤ box_wall_k  AND  manhattan(pos, t) ≤ box_dist
```

Defaults: `box_wall_k = 1`, `box_dist = 4`. In boxing mode the chase point
becomes the thief's **best escape cell**
`e* = argmax_{n ∈ neighbors(t, barriers)} |reach(n, barriers ∪ {t})|` (the exit
leading to the largest free region) — the cop blockades the way *out* of the
corner pocket instead of stepping onto the thief (which parity forbids), while
barriers (§4.3) seal the rest. Terminal condition is Stage-1
`rules.is_boxed_in` (all thief neighbours barrier/cop) — boxing, by design.

### 4.3 Barrier discipline — hold fire, then wall the escape side

The baseline's failure was *when*, not *where*. Policy:

```
HOLD FIRE unless:  manhattan(pos, t) ≤ fire_dist            # default 3
              AND  wall_dist(t) ≤ fire_wall_k               # default 2 (near boundary)
esc = (t.row + sgn(t.row − pos.row), t.col + sgn(t.col − pos.col))  # flee direction
R0  = |reach(t, barriers)|
for q in candidates(pos, barriers):        # adjacent to cop, legal per rules
    gain(q) = R0 − |reach(t, barriers ∪ {q})|
    score(q) = w_gain·gain(q) − w_esc·manhattan(q, esc) − w_near·manhattan(q, t)
    if q ∈ corner_cut(t): score(q) += w_cut      # min-cut bonus, see below
place argmax iff gain ≥ min_gain
     AND cop's own region still touches reach(t, barriers ∪ {q})   # no self-trap
     AND q ≠ this turn's move target
```

Defaults: `w_gain = 2.0`, `w_esc = 1.0`, `w_near = 0.5`, `w_cut = 3.0`,
`min_gain = 1`. **`corner_cut(t)`** — when `t` lies inside the 2×3 (or 3×2)
region flush against its nearest corner, the min-cut sealing that pocket is the
fixed 3-cell diagonal fence (e.g. corner `(0,0)`, region rows 0–1 × cols 0–2:
cut = `{(2,0),(2,1),(2,2)} ∪ {(0,3),(1,3)}` minus whichever side the pocket
doesn't open on — computed by `reach` difference, table-free). Barriers laid on
the cut convert the corner into a dead end with one guarded mouth: the cop
holds the mouth, `is_boxed_in` fires. Budget arithmetic: hold-fire means
≥ `14 − fire budget` barriers remain for the endgame; the corner cut needs ≤ 5.
The lab's `WallCop` probe with exactly this discipline was the **only** cop to
score against a live evader.

---

## 5. Fix 3 — Thief hardening (`strategy/thief_evader_v2.py`)

`class EvaderBrain(ThiefBrain)` — extends the baseline scorer (which stays
untouched at ≥97.5% survival vs baseline cops) with three terms tuned against
Herder-class pursuers:

```
score(c') = w_dist · manhattan(c', believed_cop)
          + w_exits · |neighbors(c', barriers)|
          − w_risk  · [manhattan(c', believed_cop) ≤ 1]
          + w_reach · |reach_H(c', barriers)|          # NEW: corner avoidance
picks = { d : score(d) ≥ best − tie_eps }
pick  = seeded_rng.choice(sorted(picks))               # NEW: anti-predictor
```

- **Corner avoidance** (`w_reach`, default `0.4`): `reach_H` = BFS truncated at
  `reach_horizon` steps (default 6, O(cells)); cells whose H-step reachable set
  is small (corners: ~8 vs center: ~25) are structurally dangerous vs a herder
  *before* any wall appears — the thief refuses the corner the herder steers
  toward.
- **Seeded tie-randomization:** near-tied moves (within `tie_eps`) are chosen
  by an RNG seeded from `[play].seed` (mixed with role + step:
  `random.Random(seed * 1009 + step)`), so an `InterceptCop`-style one-step
  predictor faces genuine move entropy, yet any replay with the same seed is
  bit-identical (NFR-C-b preserved; `Decision.fallback`/reasoning notes the
  random pick).
- **Survival-clock awareness:** with `turns_left = survival_threshold − step`
  (threaded via params from `[movement_and_barriers]`): when
  `turns_left < clock_threshold` (default 8) switch to **deep safety** —
  multiply `w_dist` and `w_reach` by `clock_boost` (default 2.0) and veto any
  move with `|reach_H| < reach_floor` (default 6) if an alternative exists.
  Rationale: with few turns left the thief needs only to *not lose*; distance
  and open space dominate scent-hygiene niceties.

---

## 6. Benchmark lab as a committed deliverable

The scratchpad experiment (`league_eval.py`/`league_eval2.py`) becomes
repo-permanent — the evidence engine for the research report and the
regression gate for every future brain tweak.

- **`src/cipherchase/strategy/archetypes.py`** (~60 lines): the opponent
  archetype set as first-class seam brains — `NaiveEdgeThief` (flees to the
  far corner: the classic student thief), `RandomThief` (seeded uniform legal
  move), `StillThief` (degenerate anchor). Being real `BrainBase` subclasses,
  any of them is also selectable via `thief_class` in config — the archetypes
  double as league sparring stand-ins.
- **`scripts/benchmark_lab.py`** (~140 lines; shared helpers split to
  `scripts/benchlib.py` if the ≤150 budget threatens): the harness —
  - randomized-start pair generation: seed `1000+s`, rejection-sample until
    `manhattan(cop0, thief0) ≥ 4` (identical to the lab, so historical numbers
    stay comparable);
  - matrix runner over `{PoliceBrain, PoliceExpectimax, HerderCop} ×
    {ThiefBrain, EvaderBrain, NaiveEdge, Random, Still}` under **realistic
    info** (both sides delta-belief, §8) via the real `sdk/game_loop` seam —
    no duplicated engine (R2);
  - metrics per cell: capture-rate %, mean turns-to-capture, capture-kind
    split (coloc/barrier/**boxed**), mean belief error
    `manhattan(argmax, true)`, barriers placed;
  - output: a **markdown table** on stdout (pasted verbatim into
    `docs/RESEARCH-REPORT-Performance-Analysis.md`) + optional `--json` blob
    for plots;
  - `--fast` mode: N=20, brains subset — **CI-runnable < 60 s** on the
    Py-3.13 workflow; full mode N=120 for the report.

CLI: `uv run python scripts/benchmark_lab.py [--fast] [--n 120] [--seed 1000] [--json out.json]`.
All parameters flow from config/flags; nothing hardcoded (R11).

---

## 7. Acceptance targets (binary — measured by `benchmark_lab.py`, full mode)

| # | Target | Threshold | Baseline today |
|---|---|---|---|
| A1 | HerderCop capture vs **NaiveEdge** | **≥ 90%** | 0.0% |
| A2 | HerderCop capture vs **Random** | **≥ 90%** | 30.8% |
| A3 | HerderCop capture vs **Still** | **≥ 90%** | 14.2% |
| A4 | HerderCop capture vs **ThiefBrain-class** evaders | **≥ 30%** | 0.0% |
| A5 | EvaderBrain survival vs **HerderCop-class** pursuers (realistic delta-belief info both sides) | **≥ 95%** | n/a (new) |
| A6 | Mean belief error with decoder+persistent grid, all cells | **≤ 1.0 cell** | 3.46 |
| A7 | Per-move decision time (M2, worst brain incl. BFS) | **< 5 ms** | ~1 ms |
| A8 | Token cost of any move path | **0** (F8 guard test) | 0 |
| A9 | Baseline matrix (PoliceBrain/Expectimax rows) reproduced within ±3 pts | regression anchor | — |

A1–A5 gate P2 exit (PLAN §3); A9 proves the baselines were truly untouched.

---

## 8. Dec-POMDP realism fix (game_loop information rule)

Audit §2.3-8: `game_loop` hands the thief the **cop's true position** every
turn — the thief plays a POMDP with an oracle, which both inflates its
survival number and breaks the Dec-POMDP claim (and the audit narrative that
"nobody sees the opponent's cell"). New rule, both sides symmetric:

> **An agent's belief may be built ONLY from: (1) the opponent-scent intensity
> snapshot legally received that turn (F7), decoded via `ScentDecoder`; (2) NL
> hints (which may lie — weighted by `smell_trust` semantics); (3) a
> one-turn-DELAYED position observation where the wire protocol implies it
> (the opponent's *previous, already-revealed-by-audit-record* step), injected
> as a synthetic deposit of `center_intensity` at the delayed cell; (4) its own
> exclusions (own cell, barriers). Never the current true cell.**

Concretely in `run_game`: the thief keeps a persistent `BeliefGrid` + decoder;
each turn it receives `{prev_cop_cell: center_intensity}` (position at `t−1` —
the lab's measured `mode="delayed"`), observes, diffuses. The cop's belief path
switches to decoder + persistent grid per §3.4. Both leagues and benchmarks run
this same rule, so every number in §7 is earned under legal information — and
the thief's ≥95% target (A5) is honest, not oracle-assisted.

---

## 9. TDD plan, edge cases, milestone, traceability, risks

### 9.1 TDD (red→green→refactor; all seeded, no LLM/network anywhere)

**`test_scent_decode.py`** — kernel round-trip: deposit at `c`, decay, deposit
at `c'`; `argmax Δ = c'` for all `c'` moves incl. STAY · first-turn returns raw
snapshot · gap=2 uses `(1−ρ)²` baseline · saturation: force `τ_prev = 1.0`
plateau, assert `decode → None` (case A) and brain falls back to persistent
argmax · incoherent ties (two distant equal Δ cells) → `None` (case B) ·
empty-snapshot no-op.

**`test_police_herder.py`** — anti-corner geometry: for each corner, chase
point `g` is anti-corner-ward of `t` · phase switch flips exactly at
`box_wall_k`/`box_dist` boundary values · boxing targets the max-reach escape
cell · hold-fire: no barrier when `dist > fire_dist` (param sweep) ·
corner-cut: thief in the 2×3 pocket → chosen barriers ⊆ cut set, and after ≤5
placements `is_boxed_in` is achievable with cop at the mouth · self-trap
candidates rejected · scripted 10-turn end-to-end: herder captures a scripted
edge-hugger **by boxing, never co-location** (assert capture kind).

**`test_thief_evader.py`** — corner-avoidance: with equal distance/exits, the
larger-`reach_H` cell wins · tie-randomization: same seed ⇒ identical game;
different seeds ⇒ ≥2 distinct move sequences over 10 near-tie turns ·
survival-clock: below threshold, a `reach_floor`-violating move is vetoed when
an alternative exists; not vetoed when it's the only legal move (fallback).

**`test_benchmark_lab.py`** — `--fast` matrix runs, table well-formed, start
pairs respect min-separation, archetypes load via `factory.load_brain` (seam
proof) · **`test_game_loop_realism.py`** — thief's belief input never contains
the cop's current cell (spy on `observe_smell`); delayed cell equals `t−1`
position; persistent grids are the same object across turns.

### 9.2 Edge cases

| Case | Handling |
|---|---|
| Decoder ambiguous (saturation / ties) | return `None`; persistent belief drives the turn (§3.3) |
| First turn / empty snapshot | raw snapshot as evidence; `{}` no-op; belief uniform |
| Missed/skipped step (`gap > 1`) | baseline decayed `(1−ρ)^gap`; `gap ≤ 0` → treat as restart, re-baseline |
| Chase/ghost point out of bounds | clamp to `t` (herd) / to nearest in-bounds (box) |
| Barrier would self-trap or seal cop out | rejected by the reach-connectivity check, step only |
| `max_barriers` exhausted mid-boxing | degrade to blockade-the-mouth movement only |
| All moves veto'd by `reach_floor` | veto lifted, best available taken, `fallback=True` |
| Belief all-zero after exclusions | `BeliefGrid._normalize` uniform fallback (existing, unchanged) |
| `[play].seed` absent | typed `ConfigError` at load (the key becomes load-bearing — closes audit item R11-`play.seed`) |

### 9.3 Milestone & Definition of Done

**Milestone (binary):** as in the header — one command, matrix printed, A1–A5
green, reproducible from seed.

**DoD:** five new files each ≤150 raw+logical (`check_file_lines.py` green) ·
ruff 0 · coverage stays **100%** (new tests cover every new branch; mock
nothing but time) · baselines byte-identical (git diff empty on
`police_heuristic.py`, `thief_heuristic.py`, `police_expectimax.py`,
`belief.py`, `brains.py`, `factory.py`) · config defaults added to both
`config/police/game.toml` and `config/thief/game.toml`, championship brains
selected there via the existing `police_class`/`thief_class` seam · matrix
pasted into the research report · CI runs `benchmark_lab.py --fast`.

### 9.4 Traceability

| Requirement / audit finding | Design | Test |
|---|---|---|
| F8 move-is-algorithmic | all brains pure Python, RNG-only | existing `test_f8_no_llm` + new brains under same guard |
| F7 intensity-only wire | decoder consumes `snapshot()` dicts only | `test_scent_decode` |
| PLAN §2.2(a) phantom trail (3.46) | §3 decoder + persistent grid | `test_scent_decode`, A6 |
| PLAN §2.2(b) parity stall | §4.1–4.2 herd + blockade, boxing capture | `test_police_herder` e2e |
| PLAN §2.2(c) squandered barriers | §4.3 hold-fire + corner min-cut | hold-fire + cut tests, boxed-kind metric |
| Audit §2.3-8 thief oracle info | §8 information rule | `test_game_loop_realism` |
| Audit R11 dead `play.seed` | §5 tie-RNG seeded from it | evader determinism test |
| FR-C4 seam intact | new brains are `BrainBase` subclasses via factory | `test_benchmark_lab` seam proof |
| League L2 (PLAN §1) | A1–A5 targets | `benchmark_lab.py` full run |

### 9.5 Risks

| Risk | L×I | Mitigation |
|---|---|---|
| Herder rework destabilizes green suite | M×M | new brains are NEW seam classes; baselines untouched (A9 anchor); factory swap is one config line back |
| A4 (≥30% vs strong evader) missed after EvaderBrain hardening | M×M | targets measured vs *ThiefBrain-class* (the realistic opponent tier); EvaderBrain-vs-HerderCop is intentionally thief-favored (A5) — mirrors league asymmetry |
| ≤150 / 100%-cov erosion | M×M | modules pre-split (§6 benchlib note); TDD cadence; `check_file_lines.py` in CI already |
| Decoder brittle vs foreign scent params | L×H | ρ/kernel come from the *negotiated shared config*, not assumptions; ambiguity fallback (§3.3) degrades to today's behavior, never worse |
| Benchmark drift vs scratchpad numbers | L×M | identical start-seeding scheme; A9 reproduces the baseline matrix as a checksum |
