# PRD_language_scent — Stage 4: Natural-Language Hints + Scent/Stigmergy + Trash-Talk

| | |
|---|---|
| **Mechanism** | Language & Scent — the deception layer (NL hints that may bluff) over an incorruptible physical-truth substrate (scent, board) |
| **Stage** | 4 of 7 (bottom-up build) — *the hardest stage* |
| **Chapters** | Ch4 (natural-language / stigmergy) + Ch6 (belief-driven decisions) |
| **Gates** | **F6** (free NL hints MAY bluff; board/barriers/captures MUST be truthful) · **F7** (scent 5×5 decay 0.10 + Bayesian belief drive decisions; only intensity field on the wire) |
| **FRs** | FR-D1 (scent/stigmergy) · FR-D2 (bluffing hints, truthful board) · FR-D3 (`Intent∈{truth,lie}` bound into commit) · FR-D4 (trash-talk provider seam) · NFR-3 (gatekeeper) · NFR-11 (zero hardcoding) |
| **Modules** | `domain/smell.py` · `domain/belief.py` (shared w/ PRD_strategy) · `strategy/trash_talk.py` · `strategy/talk_providers.py` · `infra/llm_provider.py` |
| **Version** | 1.00 (single-source `shared/version.py`) |
| **Status** | Gate-2 draft — approve with the full docs package before code |

---

## 1. Purpose & scope

Stage 4 layers **communication** onto the working engine (Stage 1) + P2P transport (Stage 2) + algorithmic brain (Stage 3). It draws the project's central line between two kinds of information:

- **Physical truth (incorruptible).** The scent field is a *physical* deposit — it cannot lie. Barrier placements, capture claims, and moves are physical facts that **MUST** be reported truthfully; lying about them is not gameplay, it is **severe disqualification** (auto-`tamper_forfeit` 0/0 at audit, cross-ref PRD_crypto).
- **Free speech (may deceive).** The natural-language `hint` string attached to a turn **MAY be a deliberate lie** — that is a legal, encouraged strategy (bluffing). Every move commits an `Intent∈{truth,lie}` declaring, up front and under the commit hash, whether *this* hint lies; the reveal + end-game audit make the bluff self-honest (you cannot later deny you meant to lie).

In scope: the `SmellField` physics + its wire format; the hint/`Intent` model + how truth/lie is chosen and later audited; the trash-talk provider seam (4 providers, template default = 0 tokens, `every_n_steps` throttle); `BeliefGrid.observe_smell` as the read side (definition shared with PRD_strategy, which owns diffusion/most_likely).

Out of scope: the pursuit/evasion policy that consumes belief (PRD_strategy · FR-C3); the commit/reveal/audit machinery itself (PRD_crypto · FR-F); the `TurnMessage` transport (PRD_mcp_infra). This PRD **produces** the `hint`, `intent`, and `smell_grid` fields those PRDs carry.

**The Stage-4 invariant:** the LLM is *entirely absent* on the critical path. It writes hint text only; it never decides a move. A full game completes at **0 tokens** with `provider=template`.

---

## 2. Requirements

### Scent / stigmergy — FR-D1 (→ F7)
- **FR-D1.1** `SmellField` is a **5×5** intensity field (`grid_size` from `game.json.pheromones`, not literal).
- **FR-D1.2** A fresh deposit sets the **center intensity to 0.9** (`deposit_intensity`); radial falloff to neighbors per `pheromones` (Chebyshev/Manhattan kernel from config).
- **FR-D1.3** Per-turn global decay with `rho=0.10` (`decay_rate`): `tau ← max(0, (1−rho)·tau + delta_tau)`.
- **FR-D1.4** The **thief DEPOSITS** at its own current cell each turn (stigmergic trail). The **cop deposits nothing** (asymmetric — evader marks, pursuer sniffs).
- **FR-D1.5** **Each side reads ONLY the opponent's field.** The cop absorbs the thief's transmitted field into belief; neither reads its own for decisions.
- **FR-D1.6** On the wire the field is an **intensity map `"r,c"→float`, NEVER coordinates** (F7 / FR-B5). Scent leaks *proximity*, never position — that is the whole point of stigmergy.
- **FR-D1.7** All pheromone numbers (`grid_size`, `deposit_intensity`, `decay_rate`, falloff, `absorb_gain`) come from `game.json.pheromones`; **zero hardcoding** (NFR-11).

### Belief read side — FR-C2 (shared w/ PRD_strategy)
- **FR-D1.8** `BeliefGrid.observe_smell(smell_map)` folds the opponent's transmitted intensity map into the 7×7 posterior (likelihood ∝ received intensity, weighted by `absorb_gain`). Diffusion / exclusion / `most_likely` are specified by **PRD_strategy**; this PRD fixes only the smell→belief update contract.

### Natural-language hints — FR-D2 (→ F6)
- **FR-D2.1** Each `TurnMessage` carries a free-text `hint: str`. Its content is **unconstrained** and **MAY be false**.
- **FR-D2.2** The **physical fields are truthful, always**: `barrier_placed`, `capture_claim`, `win_claim`, the revealed `move`, and the `smell_grid` reflect real state. Divergence between a physical field and reality = tamper (PRD_crypto → 0/0).
- **FR-D2.3** The engine never *acts* on an opponent's hint text; hints inform **belief only as untrusted evidence** (a lie costs the liar nothing mechanically but may mislead a naive reader — and is on-record post-audit).

### Intent (declared bluff) — FR-D3 (→ F6, cross-ref PRD_crypto)
- **FR-D3.1** Every move produces `Intent∈{"truth","lie"}` stating whether **this turn's hint** lies.
- **FR-D3.2** `Intent` is part of the **committed payload** `{State,Move,Intent,Nonce}` → bound into `commit` (PRD_crypto FR-F1) and revealed with the move; the **nonce** stays hidden until the end-game reveal.
- **FR-D3.3** At the mutual audit, `Intent` is re-hashed with the rest of the payload. A peer cannot retroactively change whether it claimed to be lying — self-consistent deception is enforced by math, not trust.
- **FR-D3.4** `Intent` labels only the **hint**. It NEVER excuses a false physical field; `intent="lie"` about a barrier is still disqualification (F6 line: bluff speech ≠ tamper facts).

### Trash-talk provider seam — FR-D4 (→ D2)
- **FR-D4.1** A single `TalkProvider` interface: `.generate(context: TalkContext) -> str`. `TurnMessage.hint` is the return value.
- **FR-D4.2** Four providers behind the interface: `template` (default, **0 tokens**, pure-Python phrase templates), `claude_cli` (reuse HW6 `ClaudeCliProvider`, API-key-stripped subscription), `ollama` (local small M2 model), `claude_api` (Haiku). Selected by `[trash_talk].provider` / `[llm]` in `game.toml`; **factory in `infra/llm_provider.py`** (`build_provider(cfg)`).
- **FR-D4.3** `every_n_steps` throttle from `[trash_talk]`: on off-steps `generate` returns the deterministic template line (no LLM call), bounding cost/RPM.
- **FR-D4.4** The game **completes with the LLM entirely absent** — `provider=template` needs no keys, binary, or network. The LLM **never decides a move** (FR-C1 / N2): `generate` receives read-only context and returns *only text*.
- **FR-D4.5** Every LLM call (`claude_cli` subprocess, `ollama`/`claude_api` HTTP) is routed through `ApiGatekeeper.execute(callable, service=..., action=...)` (**NFR-3**); template makes no external call and is not gatekept.

---

## 3. Design

### 3.1 `domain/smell.py` — `SmellField` (pure, no I/O · ≤150 lines)

```
class SmellField:
    def __init__(self, cfg: PheromoneConfig) -> None      # grid_size, deposit_intensity, decay_rate, falloff, absorb_gain
    def deposit(self, center: Cell, intensity: float | None = None) -> None
    def decay_all(self) -> None
    def absorb(self, smell_map: dict[str, float]) -> None          # fold a received field in (read side)
    def intensity_at(self, cell: Cell) -> float
    def strongest_cell(self) -> Cell                              # argmax intensity (ties → deterministic first)
    def snapshot(self) -> dict[str, float]                        # {"r,c": float} wire form; drops ~0 cells
```

**Physics.**
- Internal store: `dict[Cell, float]` (sparse) over the 5×5 window centered on the depositor, values in `[0, deposit_intensity]`.
- **Deposit:** center ← `deposit_intensity` (0.9); each ring cell ← `deposit_intensity · falloff^d` for Chebyshev distance `d` (falloff from config), accumulating onto existing intensity.
- **Decay (per turn, FR-D1.3):** for every cell, `tau ← max(0, (1−rho)·tau + delta_tau)` with `rho=decay_rate=0.10`. In the common no-reinforcement case `delta_tau=0`, giving geometric fade `tau←0.9·tau`. The `max(0,·)` **clamps underflow to 0** (a negative `delta_tau` or float drift can never make intensity negative — FR edge case §5).
- **Wire (FR-D1.6):** `snapshot()` emits `{"r,c": round(tau, 6)}` for cells above an epsilon (`min_emit` from config); **keys are the string `"row,col"`, values are floats — never a coordinate tuple, never the depositor's cell as a datum.** `absorb()` on the reader parses the same map. This is the ONLY smell representation crossing the trust boundary.

Wire example (thief→cop, one turn): `{"2,2": 0.9, "1,2": 0.63, "2,3": 0.63, "3,3": 0.44}` — the reader infers "somewhere hot near row 2" but is never handed `[2,2]`.

### 3.2 `domain/belief.py` — read contract (full class in PRD_strategy)

This PRD fixes only:
```
def observe_smell(self, smell_map: dict[str, float]) -> None
    # posterior[cell] *= (1 + absorb_gain * smell_map.get("r,c", 0.0)); then renormalize
```
Higher received intensity at a cell raises that cell's belief mass; absence lowers it relatively via renormalization. Diffusion, `exclude`, `most_likely`, `as_matrix` are PRD_strategy's (FR-C2). **Assumption PRD_strategy must honor:** `observe_smell` is called once per received turn *before* `diffuse()`, and consumes the exact `snapshot()` dict shape above.

### 3.3 Hint / Intent model

`brain.decide(...)` (PRD_strategy) returns a `Decision` whose `hint` and `verdict` fields this stage fills:
- **`Decision.hint: str`** ← `TalkProvider.generate(context)`.
- **`Decision.verdict` / `intent: "truth"|"lie"`** ← chosen by a small, config-driven policy in `strategy/trash_talk.py`:
  - `choose_intent(rng, cfg) -> Literal["truth","lie"]`: lie with probability `[trash_talk].lie_probability` (e.g. 0.4), gated so a bluff is only emitted when there is *something to hide* (e.g. thief near an escape it wants to mask). Default template policy is a seedable Bernoulli for determinism in tests.
  - When `intent=="lie"`, the template composer picks a *misdirecting* phrase (points away from truth); when `"truth"`, an honest-but-vague phrase. **Neither ever encodes a physical field** — hint text is opaque to the engine.
- **Binding:** the peer's `turn_sender` (PRD_crypto) places `intent` into the committed payload `{State,Move,Intent,Nonce}`. This PRD guarantees the *value*; PRD_crypto guarantees the *hashing*.
- **Audit:** at end-game, `intent` re-hashes as part of each step; a peer that reveals a different `intent` than it committed fails `audit_records` → `tamper_forfeit`. Thus "I declared truth but the hash says lie" is impossible to forge.

### 3.4 Trash-talk provider seam

`strategy/talk_providers.py` — the interface + concrete providers (thin wrappers; ≤150 lines each):

```
@dataclass(frozen=True)
class TalkContext:            # read-only view — NO mutation hooks, NO move authority
    role: str; step: int; belief_summary: str; intent: str; recent: tuple[str, ...]

class TalkProvider(Protocol):
    def generate(self, ctx: TalkContext) -> str: ...

class TemplateProvider:       # 0 tokens, pure Python, deterministic given seed
class ClaudeCliProvider:      # reuse HW6 subprocess provider (API-key-stripped)
class OllamaProvider:         # local small model over HTTP
class ClaudeApiProvider:      # Haiku over HTTP
```

`infra/llm_provider.py` — `build_provider(cfg) -> TalkProvider` factory maps `[llm].provider`/`[trash_talk].provider` → class; unknown value → preflight `ConfigError`. Non-template providers receive the `ApiGatekeeper` and wrap their one external call in `gatekeeper.execute(...)`.

`strategy/trash_talk.py` — orchestrates: holds the provider + `every_n_steps` throttle + `choose_intent` + template fallback. Public `talk(step, ctx) -> str`:
1. compute `intent`;
2. if `step % every_n_steps != 0` → return a template line (no LLM);
3. else `try: provider.generate(ctx)`; on any failure/timeout → **fall back to the template line** (never blocks the move — §5).

**Template phrase design.** Two curated banks keyed by role and `intent`: `HONEST[role]` (vague truths: *"You'll never corner me on the east side."*) and `BLUFF[role]` (misdirection: *"Heading straight for the north wall — catch me if you can."*). Selection = seedable `rng.choice` → fully deterministic, byte-stable in tests, 0 tokens. Phrases are pure flavor; the engine ignores them.

**every_n_steps throttle.** From `[trash_talk].every_n_steps` (e.g. 3): the expensive provider fires at most once per N steps; all other steps use the free template line. Bounds token spend and gatekeeper RPM directly.

---

## 4. Edge cases & error handling

| Case | Handling |
|---|---|
| **LLM timeout / non-zero exit / empty output** | `trash_talk.talk` catches, logs once, **returns the template line**. The move proceeds regardless — the LLM is never on the move's critical path (FR-D4.4). |
| **Provider binary/model missing** (`claude` CLI or ollama not installed) | **Preflight** check in `build_provider` (or first call) raises a clear `ProviderUnavailable` at startup, not mid-game; docs tell the grader to leave `provider=template`. |
| **Missing API key for `claude_api`** | Preflight error; never silently degrade to a paid path. Default config ships `provider=template`. |
| **Scent underflow / negative delta** | `decay_all`/`deposit` **clamp to `max(0, ·)`**; intensity is always `∈[0, deposit_intensity]`. |
| **Received smell_map malformed** (bad key, NaN, out-of-range value) | `absorb`/`observe_smell` validate keys as `"int,int"` in-bounds and coerce values to `[0,1]`; a malformed field is dropped (treated as no observation), never crashes the turn. It is *not* itself tamper (scent isn't committed), but a peer sending garbage simply forfeits its own signal. |
| **Cop tries to deposit** | `SmellField.deposit` is only invoked by the thief brain; cop runtime never calls it (asymmetry enforced by wiring, tested). |
| **Hint tries to smuggle a coordinate** | Irrelevant to correctness — the engine never parses hint text; only `smell_grid`/physical fields inform state. A "coordinate in the hint" is just more (possibly false) speech. |
| **`intent="lie"` paired with a false physical field** | Detected at audit as tamper → 0/0. `Intent` covers speech only; it can never launder a physical lie (FR-D3.4). |

---

## 5. TDD test plan (Red→Green→Refactor · externals mocked · ≤150 lines/test file)

**`tests/domain/test_smell.py`**
- `deposit` sets center to `deposit_intensity` (0.9) and rings to `0.9·falloff^d`.
- `decay_all` gives `tau←0.9·tau` when `delta_tau=0`; N decays → `0.9^N·tau` within float tol (**decay-formula correctness**).
- Underflow: repeated decay and a negative `delta_tau` never yield `< 0` (clamp).
- `snapshot()` returns only `"r,c"→float` string keys, drops sub-epsilon cells, and contains **no tuple/coordinate value**; `absorb(snapshot())` round-trips within tolerance.

**`tests/domain/test_belief_observe.py`**
- `observe_smell` raises mass on hot cells and renormalizes to sum 1; malformed/out-of-range maps are ignored (no throw).

**`tests/strategy/test_template_provider.py`**
- `TemplateProvider.generate` is **deterministic** given a fixed seed; returns a non-empty `str`; `intent="lie"` draws from `BLUFF`, `"truth"` from `HONEST`.
- `choose_intent` respects `lie_probability` over many seeded draws (statistical band).

**`tests/strategy/test_trash_talk_throttle.py`**
- On off-steps (`step % every_n_steps != 0`) the LLM provider is **not** called (assert mock `generate` uncalled); template line returned.
- On on-steps the provider is called via `gatekeeper.execute` (assert gatekeeper invoked — **NFR-3 wiring**).

**`tests/infra/test_llm_provider.py`**
- `ClaudeCliProvider` mocked by patching `subprocess.run` (HW6 pattern) — returns stub stdout; no real process.
- Provider timeout/non-zero exit → `trash_talk.talk` returns the template fallback (move never blocked).
- `build_provider` with unknown provider name → `ConfigError`.

**`tests/e2e/test_zero_token_game.py`** (loopback via `FakeTransport`)
- Full cop-vs-thief game with `provider=template` runs to a terminal state and **asserts 0 LLM calls / 0 tokens** (mock provider counter stays 0). (**Milestone**.)
- Scent map is non-empty and **updates each step** (thief's transmitted `snapshot()` differs turn-to-turn).
- A step with `intent="lie"` still has **truthful physical fields**: assert the revealed `move`, `barrier_placed`, `capture_claim` match the engine's real state and the step re-hashes clean in `audit_records` (cross-check PRD_crypto). (**Board-truth-under-bluff**.)

Coverage target contribution ≥85% for all Stage-4 modules; LLM + MCP + Gmail mocked throughout (NFR-10).

---

## 6. Milestone (binary) + Definition of Done

**Milestone (must pass, binary):** *Scent map updates each step; the LLM emits a truth-or-lie hint; a full game runs at 0 tokens with `provider=template`.*

**Definition of Done:**
- `SmellField` deposit/decay/absorb/snapshot implemented; decay formula `tau←max(0,(1−rho)τ+Δτ)` with `rho=0.10` from config; wire form is `"r,c"→float` only (F7).
- `BeliefGrid.observe_smell` consumes the snapshot (contract fixed; class completed in PRD_strategy).
- `Intent∈{truth,lie}` produced per move, fed to the committed payload (binding verified in PRD_crypto), audited at end-game.
- 4-provider seam with `template` default; `every_n_steps` throttle; LLM timeout/missing-binary → template fallback; all LLM calls via `gatekeeper.execute` (NFR-3).
- All Stage-4 tests green; `ruff check` = 0; every file ≤150 raw+logical lines (`check_file_lines.py`); coverage contributes to ≥85%.
- No hardcoded pheromone/provider constants — all from `game.json.pheromones` / `game.toml.[trash_talk]/[llm]` (NFR-11).

---

## 7. Traceability

| Gate / FR / NFR | Satisfied by (section) |
|---|---|
| **F6** — hints may bluff; board/barriers/captures truthful | §1, §2 FR-D2, §3.3, §5 board-truth-under-bluff test |
| **F7** — 5×5 scent, decay 0.10, belief-driven; only intensity on wire | §2 FR-D1.1–1.8, §3.1 physics + wire, §3.2 |
| **FR-D1** — scent/stigmergy field | §3.1 `SmellField` |
| **FR-D2** — bluffing hints / truthful physical facts | §2 FR-D2, §3.3, §4 |
| **FR-D3** — `Intent∈{truth,lie}` committed + audited | §3.3, §2 FR-D3.1–3.4 (cross-ref PRD_crypto) |
| **FR-D4** — trash-talk provider seam, template default, throttle | §3.4, §2 FR-D4.1–4.5 |
| **FR-C2** (read side) — belief from smell | §3.2 (shared w/ PRD_strategy) |
| **NFR-3** — every external call via gatekeeper | §3.4, §2 FR-D4.5, §5 throttle test |
| **NFR-11** — zero hardcoding | §2 FR-D1.7, §6 |
| **NFR-7/10** — TDD, ≥85% cov, externals mocked | §5 |
| **NFR-8** — ≤150 lines/file | §3 (each module noted) |

---

## 8. Dependencies / open questions

- **→ PRD_crypto (FR-F).** Owns the commit/reveal/audit. **This PRD assumes:** the committed payload is exactly `{State, Move, Intent, Nonce}` (`Intent` is a first-class committed field, not an appendix), the nonce stays hidden until end-game, and `audit_records` re-hashes `Intent` per step so a mismatch → `tamper_forfeit` 0/0. PRD_crypto must accept an `intent: "truth"|"lie"` string in the payload dict.
- **→ PRD_strategy (FR-C).** Owns `BeliefGrid` (diffuse/exclude/most_likely/as_matrix) and the move policy. **This PRD assumes:** `BeliefGrid.observe_smell(smell_map)` is called once per received turn before `diffuse()`, consumes the exact `snapshot()` dict `{"r,c":float}`, and that `Decision` exposes writable `hint` + `intent`/`verdict` fields this stage fills. The thief brain calls `SmellField.deposit(own_cell)` each turn; the cop brain never deposits.
- **→ PRD_mcp_infra (FR-B).** `TurnMessage` must carry `hint: str`, `intent: str`, and `smell_grid: dict[str,float]` (the snapshot). Scent crosses the wire as intensity only (FR-B5/F7).
- **← shared/gatekeeper, HW6 reuse.** `ClaudeCliProvider` reused from HW6 (API-key-stripped); `ApiGatekeeper.execute` façade (ADR-004) wraps LLM subprocess/HTTP calls.
- **Open question (D2 config numbers):** `lie_probability`, `every_n_steps`, `falloff`, `min_emit`, `absorb_gain` need default values pinned in `game.toml`/`game.json` — proposed defaults 0.4 / 3 / 0.7 / 1e-3 / 1.0, to confirm at TODO time (not blocking; all config-driven).
