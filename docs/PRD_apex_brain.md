# PRD — Apex Brain (Phase P6: the strategy layer, taken to research grade)

| Field | Value |
|---|---|
| **Mechanism** | Apex Brain — opponent-model best-response cop + exact endgame solver + bluff-aware belief + strategic deception + tabular Q-learning + tournament statistics (Wilson CI + Elo) |
| **Phase** | **P6** of PLAN-PHENOMENAL (§2, items #1–#6 of the idea inventory) — ~3 days; cut order under pressure: QBrain → bluff-belief → (never cut) best-response + endgame + stats |
| **Gates** | **F6** (hints may lie; intent sealed + mutually audited — this PRD finally puts hints INTO the decision loop) · **F7** (scent = intensity only) · **F8** (the MOVE is always pure Python; LLM writes words only — including every lie) |
| **Extends** | `PRD_winning_brain.md` (P2). The `BrainBase`/`Decision`/factory seam, the matched-filter `ScentDecoder`, persistent `BeliefGrid`, and `benchmark_lab` are the substrate. **All existing brains stay byte-untouched** as regression anchors. |
| **Baselines (measured, RESEARCH-REPORT §5, N=60/cell)** | `PoliceBrain + ScentDecoder` (shipped champion): **26.7 / 23.3 / 85.0 / 96.7 / 100.0** % capture vs ThiefBrain / EvaderV2 / NaiveEdge / Random / Still |
| **New modules** | `strategy/apex_cop.py` · `strategy/opponent_model.py` · `strategy/endgame.py` · `domain/hint_belief.py` · `strategy/deception.py` · `strategy/qbrain.py` · `scripts/train_qbrain.py` · `scripts/benchlib.py` (stats) · `analysis/qbrain_policy.json` (artifact) |
| **Champion rule** | The shipped `police_class`/`thief_class` config **swaps to a new brain ONLY if its measured full-matrix numbers beat the incumbent** (the HerderCop lesson: 3.3% vs 26.7% — we report negatives, we don't ship them) |
| **NFRs** | ≤150 raw+logical per file (tests too) · ruff 0 · coverage stays **100%** · zero hardcoding (every constant below is a `game.toml [strategy]`/`[qbrain]` key) · pure Python, **0 tokens** in any move path · TDD · uv only |
| **Version** | 1.00 (single-source `shared/version.py`) |
| **Status** | Gate-2 per-mechanism draft — approve before code |
| **Milestone (binary)** | `uv run python scripts/benchmark_lab.py` prints the extended matrix with Wilson 95% CIs and an Elo ladder in which **ApexCop ≥55% vs EvaderV2 AND ≥55% vs ThiefBrain and ≥95% vs every archetype**, deterministically from seed; the endgame forced-capture proof test is green. |

---

## 2. Measured problem statement — why 26.7/23.3 is a ceiling, not a plateau

The decoder war is **won**: the matched filter localises the thief near-exactly
(0.0 fit error at the true cell in tests; sensitivity §6 shows error 0.00 for any
`smell_trust > 0`). Yet the champion cop converts that near-oracle information
into only **26.7%** vs ThiefBrain and **23.3%** vs EvaderV2. Three measured facts
explain the ceiling, and each names its fix:

**(a) Greedy chase provably cannot corner an equal-speed evader — the move-parity
argument.** Turn order is cop-moves-then-thief-moves with a capture check after
each. Co-location capture requires the cop to step onto the thief's *current*
cell, so the thief only needs post-move distance ≥ 2. Suppose after the thief's
move `d(cop, thief) = 2`; the greedy cop closes to `d = 1`. From distance 1, the
thief's five options are: STAY (`d=1`, fatal next turn), step onto the cop
(suicide), step away along the approach axis (`d=2`, safe), or two lateral steps
(`d=2`, safe). **An interior thief always has ≥3 replies restoring `d ≥ 2`; an
edge thief ≥1; only a corner pocket with sealed sides has 0.** Greedy descent
therefore converges to the `d=1 ↔ d=2` oscillation forever — exactly the
"reached dist ≤ 2 then escaped" events measured by the dozens in WB §2, and why
today's 26.7% consists of punished mistakes, not forced wins. Capture must come
from (i) **intercept**: stepping onto the cell the thief is *about to* choose —
which requires predicting the reply (→ §3 L2), or (ii) **boxing**: removing all
escaping replies at once with walls — which near a corner is a finite, exactly
solvable game (→ §3 L3). The decoder gives the exact position; greedy chase
wastes it.

**(b) The exact fix is squandered.** An exact decode is worth the most when it
feeds a *model of the opponent's next move* — we literally possess the opponent
archetypes' decision rules (we wrote them: `archetypes.py`, `thief_heuristic.py`,
`thief_evader_v2.py`), and league thieves cluster in these classes (report §5).
Today no brain evaluates them.

**(c) Hints are decorative.** `TrashTalk.choose_intent` is a coin flip
(`lie_probability`); incoming hints never touch any `BeliefGrid`; no component
tracks whether the opponent's hints were true. The course is *Orchestration of
AI agents* and F6 built a whole sealed-intent audit pipeline — yet natural
language currently influences **zero** decisions on either side. §5–§6 close
that loop in both directions.

---

## 3. ApexCop — the layered controller (`strategy/apex_cop.py` + `strategy/opponent_model.py` + `strategy/endgame.py`)

`class ApexCop(PoliceBrain)` — reuses `_candidates` and the config plumbing;
overrides `_decide_move` (move + barrier are chosen **jointly**, unlike every
predecessor). Control flow per turn:

```
L1  belief   = decoder-fed persistent BeliefGrid (exists, unchanged)
    t̂        = decoder.last_decoded  if not None  else belief.most_likely()
    locked   = decoder.last_decoded is not None
               or belief.mass_at(belief.most_likely()) ≥ apex_lock_mass    # default 0.5
    if not locked:  return PoliceBrain._decide_move(...)     # L1-only fallback (AB-6)
L3  if endgame_trigger(t̂):                                   # §3.3
        line = EndgameSolver.solve(pos, t̂, barriers)
        if line is not None:  return line.first_action        # forced capture
L2  return best_response(pos, t̂, barriers)                    # §3.1–3.2
```

- **AB-1** `ApexCop` SHALL be a `BrainBase`-seam brain loadable via
  `factory.load_brain` (`police_class = "cipherchase.strategy.apex_cop:ApexCop"`),
  leaving `PoliceBrain`, `HerderCop`, `PoliceExpectimax` byte-identical.
- **AB-2 (candidate set)** L2 SHALL enumerate joint candidates
  `(move m, barrier q)` where `m` ranges over `board.legal_moves` (incl. STAY)
  and `q` over `{None} ∪ disciplined(pos, barriers)`: adjacent placements legal
  per `can_place_barrier`, `q ≠ m`, passing the WB hold-fire discipline
  (`d(pos, t̂) ≤ fire_dist ∧ wall_dist(t̂) ≤ fire_wall_k`), no self-trap
  (cop's region still touches `reach(t̂)` after `q`), ranked by reach-gain and
  capped at the top `apex_barrier_topk` (default **3**). Worst case
  5 × 4 = 20 candidates.

### 3.1 Opponent reply prediction — evaluate THEIR rule, not ours (`strategy/opponent_model.py`)

- **AB-3 (exact models)** For each candidate `(m, q)` with next barriers
  `B' = barriers ∪ {q}`, the predicted reply set `R(m, q)` SHALL be computed by
  **executing the opponent's own published scoring rule** with cop position `m`:
  - `model="thief_v1"` → `ThiefBrain._score` argmax over its legal moves
    (deterministic; `|R| = 1`);
  - `model="naive_edge" | "random" | "still"` → the archetype's rule
    (`still` ⇒ `R = {t̂}`; `random` ⇒ `R` = all legal replies);
  - the model class is instantiated once via the factory and interrogated
    through a single `predict(reply_context) -> set[Cell]` seam — no duplicated
    scoring code (R2): `opponent_model` calls the real brain's `_score`.
- **AB-4 (EvaderV2 near-ties → minimax)** For `model="evader_v2"`, whose reply
  is a **seeded random choice among near-ties** (`tie_epsilon`), prediction
  SHALL NOT guess the RNG: `R(m, q) = { r : score_v2(r) ≥ max − tie_epsilon }`
  and the candidate's value is the **worst case over R** (minimax over the tie
  set). This is exact w.r.t. the evader's support: the realised reply is always
  in `R`.
- **AB-5 (paranoid default for the league)** Because foreign peers' rules are
  unknown, the shipped league default SHALL be `apex_opponent_model = "paranoid"`:
  `R(m, q)` = **all** legal thief replies (pure depth-1 minimax — conservative,
  never overfits a wrong model). Exact models are lab/benchmark modes selected
  per opponent by `benchmark_lab`. The config key names each mode; unknown
  values raise `ConfigError`.

### 3.2 Escape-value scoring — the formula L2 minimises

For each candidate `(m, q)` and each predicted reply `r ∈ R(m, q)`:

```
E(m, r, B') = apex_w_reach · |reach(r, B' ∪ {m})|        # thief's post-move free region
            + apex_w_dist  · manhattan(m, r)             # gap after both moves
            + apex_w_wall  · wall_dist(r)                # wall proximity is cop equity
value(m, q) = max over r ∈ R(m,q) of E(m, r, B')          # worst-case escape value
special:  m == t̂                     → value = −∞  (immediate co-location capture)
          r has no legal safe reply  → value = −∞  (capture next check)
pick argmin value; ties → prefer q = None (spend no barrier), then
deterministic direction order, then seeded rng (replays stay bit-identical)
```

Defaults (all `game.toml [strategy]` keys): `apex_w_reach = 1.0`,
`apex_w_dist = 0.6`, `apex_w_wall = 0.8`, `apex_lock_mass = 0.5`,
`apex_barrier_topk = 3`. Treating the cop's own next cell `m` as an obstacle in
`reach` is what makes intercept emerge: a candidate that stands on the thief's
best escape crushes `|reach|` even with `q = None`.

- **AB-7 (latency)** Worst case ≈ 20 candidates × ≤5 replies × one 49-cell BFS
  ≈ 5 k cell-ops; the whole L2 turn SHALL complete in **≤ 50 ms** on the target
  M2 (measured by the lab's `--timing` flag; current full-turn budget is
  14.5 ms, live budget 30 s — three orders of margin).

### 3.3 Endgame solver — the corner is a finite game; solve it (`strategy/endgame.py`)

- **AB-8 (trigger)** L3 SHALL activate only when the position is *known and
  small*: `locked ∧ wall_dist(t̂) ≤ endgame_wall_k (default 2) ∧
  manhattan(pos, t̂) ≤ endgame_gap (default 4)`. Decoder-ambiguous turns
  (`locked = False`) NEVER enter L3 — a proof over a guessed position is not a
  proof.
- **AB-9 (exact alpha-beta, proof semantics)** `EndgameSolver.solve` SHALL run
  depth-bounded alpha-beta over **true positions**:
  state = `(cop, thief, barriers, ply)`; cop actions = legal moves ×
  (`None` + ≤4 adjacent legal barrier candidates); **thief actions = ALL legal
  replies** — never the heuristic model, because L3's output is a *guarantee*
  ("forced capture against any play"), not a prediction. Terminal:
  `rules.is_capture` → value `DEPTH_MAX − ply` (prefer the shortest mate);
  survival-threshold reached → loss. Returns the first action of a forced
  line **iff the root proves capture within the horizon against every reply**,
  else `None` → fall through to L2 (never stalls a live turn).
- **AB-10 (caps + memo)** Search SHALL enforce `endgame_depth` (default **8**
  plies) and `endgame_nodes` (default **50_000**) caps — hitting either returns
  "unproven" (= `None` at root), and SHALL memoise on a
  `dict[(cop, thief, barriers, ply)]` transposition table cleared per turn.
  Bound check: ≤25 cop actions × 5 thief replies per ply-pair ⇒ branching ≈ 125
  per full turn; with memoisation on a ≤(2·`endgame_gap`+1)² local region the
  cap is generous, and the cap — not hope — is the safety argument.
- **AB-11 (proof fixtures)** Two committed positions SHALL pin the semantics:
  (i) *forced win*: thief in the 2×2 corner pocket at `(0,0)`, barriers sealing
  `{(2,0),(2,1)}`, cop at the mouth `(0,2)` → `solve` returns a capture line
  (and the follow-up assertion plays it out to `Outcome.CAPTURE` against a
  worst-case reply oracle); (ii) *known escape*: open board, `d = 4`, no
  barriers → `solve` returns `None`. Both deterministic, no RNG.

---

## 4. Bluff-aware belief — hints enter the decision loop (`domain/hint_belief.py`)

Design stance: **fail-safe first**. An unparseable hint does nothing; weight is
capped small; `bluff_weight = 0` reduces the whole subsystem to a no-op.

- **AB-12 (honesty tracker)** `class HonestyTracker` SHALL maintain a per-opponent
  **Beta(α, β)** posterior over "this opponent's hints are true", prior
  `α₀ = β₀ = 1` (config `honesty_prior_a/b`), with `P(honest) = α/(α+β)`.
  Updates at exactly two kinds of moments:
  1. **Audit/claim verification** — the end-of-sub-game mutual audit reveals the
     opponent's true trajectory and sealed intents; every emitted hint is graded
     true/false against it and batch-folded (`α += truths, β += lies`),
     persisting across the sub-games of a series (the F6 audit becomes a
     *learning signal*, not just a tripwire).
  2. **Live cross-check** — when the decoder yields consecutive fixes
     `t̂ₖ₋₁ → t̂ₖ`, the observed movement signs are compared with the hint's
     claimed direction tag: agreement → `α += 1`, contradiction → `β += 1`,
     no fix or no `dir` tag → no update. (The scent channel, which cannot lie
     — F7 — cross-examines the language channel, which can — F6.)
- **AB-13 (parseable-by-construction hints)** The `_PHRASES` banks in
  `infra/llm_provider.py` SHALL be upgraded from `list[str]` to a tagged schema
  — **the new bank contract**:

  ```python
  _PHRASES: dict[role, dict[intent, list[dict]]]
  entry = {"text": str,
           "dir":   "N" | "S" | "E" | "W" | None,   # direction the TEXT asserts
           "claim": "lost" | "close" | "cornered" | None}
  # e.g. {"text": "Heading north, promise.", "dir": "N", "claim": None}
  #      {"text": "I've lost your trail completely.", "dir": None, "claim": "lost"}
  ```

  `TemplateProvider.generate` returns `entry["text"]` (behaviour unchanged);
  a pure helper `hint_tags(text) -> Tags` matches an *incoming* hint against
  **all** banks (both roles, both intents) by normalised exact text. We authored
  the banks, so our own league ecosystem is parseable by construction; a foreign
  free-text hint matches nothing → tags all-`None` → **no belief effect and no
  tracker update** (fail-safe, never a crash — mirrors lenient-parse policy).
- **AB-14 (belief nudge)** When a hint carries a `dir` tag, the opponent-belief
  grid SHALL be nudged multiplicatively over the hinted half-plane cone
  (cells strictly on the `dir` side of the current belief peak):

  ```
  p(c) ← p(c) · (1 + bluff_weight · (2·P(honest) − 1))   for c ∈ cone(dir)
  then renormalise
  ```

  The sign flips automatically for liars: `P(honest) < 0.5` down-weights the
  hinted cone (an established liar's "north" is evidence of not-north).
  `claim` tags feed only the tracker/statistics, never the grid (kept minimal).
  `bluff_weight` default **0.15**; `0` disables (kill switch, PLAN §5 risk).
- **AB-15 (measure before default-on)** `benchmark_lab` SHALL run the affected
  cells with `bluff_weight ∈ {0, default}` against a truthful-config and a
  lying-config opponent and print the paired Δ. The shipped default is
  non-zero **only if the measured net Δ ≥ 0**; either way the number lands in
  RESEARCH-REPORT §5 (the honesty rule of §8 applies).

---

## 5. Strategic deception — our lies get a reason (`strategy/deception.py`)

- **AB-16 (algorithmic intent policy)** `class DeceptionPolicy` SHALL replace
  the coin-flip when `deception_policy = "adversarial"` (config; `"random"`
  keeps today's behaviour). The rule — pure Python, zero LLM (F8-safe: words
  are *selected by rule*, never composed by a model deciding strategy):
  - **cop**: `lie` iff estimated gap `manhattan(pos, t̂) ≤ lie_gap (default 3)`
    — misinformation is most valuable exactly when contact is imminent;
    `truth` when far — deliberately **building honesty credit** that the
    opponent's own Beta tracker (or any rational listener) will later mis-spend
    on our endgame lie.
  - **thief**: `lie` iff cornered — `wall_dist(pos) ≤ 1` or
    `|reach(pos, barriers)| < reach_floor`; else `truth`.
- **AB-17 (adversarial lie content)** When lying with a known true heading, the
  bank entry SHALL be chosen by rule from the tagged bank (AB-13): pick the
  `lie` entry whose `dir` tag is the **opposite axis-direction of the actual
  chosen move** (heading N → emit the S-tagged lie); no matching tag → fall
  back to the cadence index. Truthful turns pick the entry whose `dir` matches
  the real move when one exists.
- **AB-18 (composition — F6 intact)** `TrashTalk` cadence (`every_n_steps`),
  provider fallback, and the sealing order are **unchanged**: the policy only
  substitutes `choose_intent` (fed a minimal context: role, gap estimate,
  wall-dist, reach) and the bank index. The chosen intent is still bound into
  the move commit *before* the hint leaves the process, and the mutual audit
  still verifies intent-vs-record exactly as today — lying stays legal,
  *undeclared* lying stays fatal. A guard test asserts byte-identical seal
  payload shape.

---

## 6. QBrain — the learning baseline, measured against engineering (`strategy/qbrain.py` + `scripts/train_qbrain.py`)

- **AB-19 (state/action/table)** Tabular Q over hand-crafted features
  `(sign(Δr), sign(Δc), L1-gap bucket {1,2,3,4–5,6+}, own wall-dist bucket
  {0,1,2,3+}, barriers-left bucket {0,1–4,5–9,10–14})` — 3·3·5·4·4 = **720
  states**; actions = the 5 moves, ×2 for the cop (`place_barrier` flag: if
  set, the disciplined best barrier of §3 AB-2 is placed) → ≤10 actions.
  Δ is measured to the believed opponent (decoder output — same legal
  information as every other brain).
- **AB-20 (training)** `scripts/train_qbrain.py` SHALL train
  `Q(s,a) += q_alpha·(r + q_gamma·max Q(s′,·) − Q(s,a))` with reward
  `+1` capture / `−1` survival / `−0.005` per step (role-mirrored for the
  thief variant), ε-greedy linearly annealed `0.3 → 0.02`, against the seeded
  archetype mixture `{NaiveEdge, Random, Still, ThiefBrain}` through the REAL
  `sdk/game_loop` (no second engine, R2). All of `q_alpha` (default 0.2),
  `q_gamma` (0.95), episode cap (default 20_000), ε schedule, mixture weights
  and seed are config/CLI; a full run completes **≤ 5 min wall** on the M2 and
  is bit-reproducible from its seed.
- **AB-21 (artifact + seam)** The trained policy SHALL be committed as
  `analysis/qbrain_policy.json` (`{"features_version": 1, "q": {state_key:
  [action values]}, "meta": {...training params...}}`). `QBrain` is a pure
  inference `BrainBase` subclass loading the JSON from `qbrain_policy_path`
  (missing/mismatched `features_version` → typed `ConfigError`), greedy argmax
  with deterministic tie order — factory-loadable, 0 tokens, F8-clean, and a
  legal `thief_class`/`police_class` for anyone.
- **AB-22 (learning curves — the professor chart)** Training SHALL emit a
  per-window capture-rate series (JSON) that the executed notebook plots as
  **learning curves**, alongside an *engineering vs learning* section: QBrain's
  final matrix row vs `PoliceBrain+decoder` and `ApexCop`, with the honest
  conclusion the numbers dictate (the rubric names RL curves explicitly;
  the comparison is the point, not the winner).

---

## 7. Statistics upgrade — claims become inference (`scripts/benchlib.py` + `benchmark_lab.py`)

- **AB-23 (Wilson 95% CI)** Every rate the lab prints SHALL carry a Wilson
  score interval:
  `center = (p̂ + z²/2n)/(1 + z²/n)`,
  `half = z·√(p̂(1−p̂)/n + z²/4n²)/(1 + z²/n)`, `z = 1.96`
  — rendered as `55.0 % [46.1, 63.6]`. (Wilson, not Wald: correct behaviour at
  0%/100% cells, which our matrix actually contains.)
- **AB-24 (Elo ladder)** The lab SHALL play a seeded round-robin over **all**
  brains — `{PoliceBrain, HerderCop, PoliceExpectimax, ApexCop, QBrain-cop} ×
  {ThiefBrain, EvaderV2, NaiveEdge, Random, Still, QBrain-thief}` — and compute
  Elo: base **1000**, `E_a = 1/(1 + 10^((R_b − R_a)/400))`,
  `R_a += elo_k·(s − E_a)` with `elo_k = 16` (config), `s = 1` to the game
  winner (capture → cop, survival → thief), updates applied in the seeded game
  order (deterministic ladder).
- **AB-25 (outputs)** The lab SHALL print report-ready markdown (matrix with
  CIs + Elo table) and an optional `--json` blob for the notebook; `--fast`
  stays CI-runnable **< 60 s** (N = 8, brain subset). New rows are added to
  RESEARCH-REPORT §5 and the notebook re-executed.
- **AB-26 (incumbent protection)** The baseline matrix rows (PoliceBrain,
  HerderCop) SHALL be reproduced within ±3 pts (regression anchor, WB A9), and
  the shipped champion config changes **only** on a measured full-matrix win.

---

## 8. Acceptance targets (binary, measured by `benchmark_lab.py` full mode)

| # | Target | Threshold | Baseline today |
|---|---|---|---|
| AT-1 | ApexCop capture vs **EvaderV2** (matched model, AB-4) | **≥ 55%** | 23.3% |
| AT-2 | ApexCop capture vs **ThiefBrain** (matched model) | **≥ 55%** | 26.7% |
| AT-3 | ApexCop capture vs **each archetype** (NaiveEdge/Random/Still) | **≥ 95%** | 85.0 / 96.7 / 100.0% |
| AT-4 | Paranoid-mode ApexCop (shipped league default) vs the full thief column | reported (no silent model-cherry-picking) | n/a |
| AT-5 | Endgame solver proof fixtures (forced win found; known escape → None) | green | n/a |
| AT-6 | Per-decision wall time, ApexCop worst turn, offline M2 | **≤ 50 ms** | 7 ms (champion) |
| AT-7 | Bluff-aware belief: paired Δ with `bluff_weight ∈ {0, default}` measured & reported; **default-on only if net-positive** | reported | n/a |
| AT-8 | QBrain: committed policy JSON + learning curves in the executed notebook | present | n/a |
| AT-9 | Elo ladder + Wilson CIs published (report §5 + notebook) | present | n/a |
| AT-10 | Thief survival vs ApexCop (our own thief's number) | reported honestly, whatever it is | 73.3–76.7% vs champion |
| AT-11 | Baseline rows reproduced ±3 pts; existing brains byte-identical | green | — |

**Honesty rule (contractual):** if any target is missed, the RESEARCH-REPORT
states the measured number next to the target — **targets are never silently
edited** (precedent already set: WB's ≥30% target is published beside the
measured 26.7%, and HerderCop's 3.3% negative result is in §5).

---

## 9. TDD plan, edge cases, risks, traceability, budgets

### 9.1 TDD (red→green→refactor; all seeded; zero LLM/network/Gmail anywhere)

- **`test_apex_cop.py`** — layered dispatch: unlocked belief → PoliceBrain path
  (spy); locked + trigger → solver consulted first; solver `None` → L2 ·
  candidate set respects hold-fire/self-trap/topk · joint (move, barrier)
  beats any same-position move-only choice on a constructed intercept position ·
  tie-break prefers `q = None` · seeded determinism: same seed ⇒ identical
  game transcript.
- **`test_opponent_model.py`** — per archetype: predicted reply equals the real
  brain's actual reply on 20 random seeded positions (`still` ⇒ STAY-locked
  `R = {t̂}`) · EvaderV2: realised reply ∈ predicted near-tie set on every
  turn of a seeded game (support-exactness) · paranoid ⊇ every model's set ·
  unknown model name → `ConfigError`.
- **`test_endgame.py`** — the two AB-11 proof fixtures · depth cap: forced win
  at depth 10 with `endgame_depth = 8` → `None` · node cap short-circuit
  (counter spy) · memo hit-count > 0 on the win fixture · trigger boundary
  values (`wall_dist = 2` in, `3` out; `gap = 4` in, `5` out) · ambiguous
  decoder ⇒ L3 never invoked.
- **`test_hint_belief.py`** — Beta math: (α,β) sequences give exact
  `P(honest)` fractions · audit batch-fold arithmetic · live cross-check:
  decoded S-movement vs "N" hint increments β; no fix → no update · cone
  nudge: `P=1` boosts, `P=0` inverts, `P=0.5` is a no-op; `bluff_weight=0`
  leaves the grid bit-identical · foreign text → all-None tags, zero effect ·
  every bank entry round-trips through `hint_tags`.
- **`test_deception.py`** — cop lies iff `gap ≤ lie_gap` (boundary sweep) ·
  thief lies iff cornered · opposite-direction lie selection (heading N ⇒
  S-tagged text) · truthful turn picks matching-dir entry · cadence and seal
  payload shape unchanged (guard) · `"random"` mode reproduces today's
  distribution.
- **`test_qbrain.py`** — one Q-update by hand-computed arithmetic · ε schedule
  endpoints · feature bucketing boundaries (gap 5 → "4–5", 6 → "6+") · policy
  JSON round-trip; missing file / bad `features_version` → `ConfigError` ·
  factory loads QBrain (seam proof) · 50-episode micro-train is seeded-
  reproducible and improves vs `Still` (CI-fast smoke, seconds not minutes).
- **`test_benchlib.py`** — Wilson against published reference values (incl.
  n=60, p̂∈{0,1} edges) · Elo: hand-computed 3-game sequence · ladder
  determinism from seed · `--fast` lab end-to-end well-formed.
- Existing **F8 guard** (`test_f8_no_llm`) extends over every new brain; a new
  guard asserts `deception.py` imports nothing from `infra/`.

### 9.2 Edge cases

| Case | Handling |
|---|---|
| Decoder ambiguous / belief unlocked | L3 forbidden (AB-8); L2 skipped; PoliceBrain L1 fallback (AB-6) |
| No legal barrier candidate / `max_barriers` exhausted | candidate set = `{None}` only; L2 degrades to move-only best response |
| STAY-locked thief (`still` model) | `R = {t̂}` — L2 collapses to deterministic shortest intercept; solver still proof-checks |
| Predicted reply cell becomes illegal (fresh barrier) | prediction recomputed against `B'` per candidate — never stale |
| Solver cap hit mid-search | root returns `None`; L2 answers the turn (never a stall — PLAN §5) |
| Opponent emits free text / silence | `hint_tags` → all-None; no nudge, no tracker update, no crash |
| Tracker with zero evidence | prior Beta(1,1) ⇒ `P = 0.5` ⇒ nudge factor exactly 1 (no-op by algebra) |
| `bluff_weight = 0` | grid math provably unchanged (bit-identical test) |
| QBrain unseen state key | uniform-zero row ⇒ deterministic first-action tie-break, `fallback=True` noted |
| Policy artifact absent in a fresh clone | typed `ConfigError` naming the path + the train command |

### 9.3 Risks

| Risk | L×I | Mitigation |
|---|---|---|
| ApexCop overfits lab models, league opponents differ | M×M | paranoid default shipped (AB-5); AT-4 reports the unmatched number; archetype spread in the matrix |
| Endgame search blow-up on a live turn | L×H | hard depth+node caps, per-turn memo, `None` fallback — worst case is exactly today's L2 |
| Bluff-belief backfires vs adaptive liars | M×M | capped weight, kill switch, AB-15 measured-before-default-on, cone-only effect |
| Q-training time/quality on 8 GB M2 | M×L | 720-state table, episode+wall caps, seeded; QBrain is a *baseline exhibit*, never the shipped champion unless it wins AB-26 |
| ≤150 / 100%-cov erosion across 8 new files | M×M | responsibilities pre-split per module (§9.4); TDD cadence; `check_file_lines.py` already in CI |
| Champion regression | L×H | AB-26 anchor ±3 pts; incumbent config untouched until the full matrix says otherwise |

### 9.4 File budget (≤150 raw AND logical each — `check_file_lines.py` gates CI)

| File | Responsibility | Est. logical |
|---|---|---|
| `strategy/apex_cop.py` | layered dispatch + L2 scoring/argmin | ~110 |
| `strategy/opponent_model.py` | model registry + `predict` seam (delegates to real brains) | ~80 |
| `strategy/endgame.py` | trigger + alpha-beta + memo + caps | ~120 |
| `domain/hint_belief.py` | Beta tracker + `hint_tags` + cone nudge | ~100 |
| `strategy/deception.py` | intent rules + tagged-entry selection | ~70 |
| `strategy/qbrain.py` | policy load + feature encode + argmax | ~90 |
| `scripts/train_qbrain.py` | training loop + curves JSON | ~130 |
| `scripts/benchlib.py` | Wilson + Elo + markdown render | ~90 |
| `infra/llm_provider.py` (edit) | tagged `_PHRASES` schema | stays ≤150 |
| `scripts/benchmark_lab.py` (edit) | new rows/modes; overflow shared into `benchlib` | stays ≤150 |

### 9.5 Traceability

| Source | Design | Verified by |
|---|---|---|
| PLAN-PHENOMENAL §1 #1 / §2 best-response | §3.1–3.2 (AB-2..AB-5) | `test_apex_cop`, `test_opponent_model`, AT-1..AT-4 |
| PLAN §1 #2 endgame solver | §3.3 (AB-8..AB-11) | `test_endgame`, AT-5 |
| PLAN §1 #3 bluff-aware belief · F6-into-the-brain | §4 (AB-12..AB-15) | `test_hint_belief`, AT-7 |
| PLAN §1 #4 strategic deception · F8 | §5 (AB-16..AB-18) | `test_deception`, F8 guard |
| PLAN §1 #5 RL + curves (rubric-named) | §6 (AB-19..AB-22) | `test_qbrain`, AT-8 |
| PLAN §1 #6 tournament statistics | §7 (AB-23..AB-25) | `test_benchlib`, AT-9 |
| WB §2 parity stall, measured | §2(a) math + §3 intercept/boxing | AT-1/AT-2 vs the 26.7/23.3 baseline |
| F7 intensity-only | all inputs via decoder/belief; tracker cross-checks scent-vs-words | existing decoder tests + `test_hint_belief` |
| FR-C4 seam / R2 no-dup | every new brain via factory; models delegate to real scorers | seam-proof tests |
| PLAN §3 cut order & champion rule | header + AB-26 | AT-11 |

**Definition of Done:** all AB-1..AB-26 implemented test-first · every file in
§9.4 within budget · ruff 0 · coverage 100% · existing brains byte-identical ·
full-mode lab run pasted into RESEARCH-REPORT §5 (with CIs + Elo) · notebook
re-executed with learning curves · champion config re-decided by AB-26 ·
`docs/PROMPTS.md` updated.
