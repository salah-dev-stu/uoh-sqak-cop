# PRD — Integrity & Rubric Hardening (Championship P0)

| | |
|---|---|
| **Mechanism** | Integrity & Rubric Hardening — close every audit finding; make every documented claim true in the runnable path |
| **Phase** | **P0** (Jul 19–24) — first, because every later diff (P1 league runtime, P2 winning brain) builds on truthful foundations |
| **Parent** | `docs/PLAN-CHAMPIONSHIP.md` §2.3 (canonical finding list) |
| **Rubric touched** | **R2** (no duplication) · **R3** (gatekeeper wired) · **R4** (limits/values in config) · **R6** (version single-source + compat check) · **R11** (zero hardcoding) |
| **Gates touched** | **F5** (signed Step-0 declaration in the emitted artifact) · **F6** (NL hints/bluffs actually occur) · **F11** (auto-email of the 4 JSON) |
| **Exit criterion (binary)** | Re-run of the four audits yields **zero open findings**; every README/PLAN/TODO claim is **demonstrably true** in the runnable path |
| **Doc status** | Awaiting approval — no code until approved (lifecycle gate 2) |

**Principle:** *docs tell the truth, and the truth is impressive.* Every requirement below is one audit finding turned into (a) a fix design with the exact file, (b) a test that fails today, (c) a traceability ID `IH-n` for `docs/TODO.md` §Championship.

Scope guard: this PRD changes the **offline runnable path** (`cli → sdk → game_loop`) and the docs. Wire choreography (sealed single-message turns, per-turn reveal removal) is **P1** (`PRD_league_runtime.md`); chase-policy strength is **P2** (`PRD_winning_brain.md`). Where an IH fix touches a seam P1/P2 will rework, the test asserts **engine truth**, not wire shape, so it survives the rework.

---

## 2. Integrity fixes (real bugs in the integrity project)

### IH-1 — Sealed payloads must carry the mover's REAL barrier view 🔴
- **Finding** (§2.3-1): `game_loop.run_game` keeps `barriers` in a local frozenset and never threads it into `OwnState`, so `move_payload()` (`peer/sealing.py:17`) serializes `state.barriers == frozenset()` → **every committed payload says `barriers: []`** while the board has up to 14. Our own audit "verifies" a wrong board. `OwnState.with_barrier` (`domain/own_state.py:27`) exists and has **zero production callers**.
- **Fix** — `src/cipherchase/sdk/game_loop.py` (+ tiny addition to `domain/own_state.py`):
  - Add `OwnState.with_barriers(barriers: frozenset[Cell]) -> OwnState` (a `dataclasses.replace` view-sync; keeps `with_barrier` for incremental placement, which the cop now actually calls on a successful placement).
  - Both movers seal against the barrier set **in effect at decision time**: `book.seal(move_payload(step, state.with_barriers(barriers), decision))`. Barriers are physical/public — both peers observe them — so the thief's sealed view carries them too (docstring of `own_state.py` updated: "own position + observed physical barriers").
  - The engine's `barriers` local remains the single truth; states are synced views (no dual bookkeeping).
- **Test** (`tests/sdk/test_game_loop.py`) — *regression, fails today*: replay `result.records` alongside a reference simulation; assert **for every sealed record, `payload["state"]["barriers"]` equals the engine barrier set at that step**, and that at least one cop record has a non-empty barrier list in a game where a barrier was placed.

### IH-2 — Fresh deposit decayed the same turn
- **Finding** (§2.3-8a): `run_game` calls `smell.deposit(thief.position)` **then** `smell.decay_all()` — the newest scent is instantly decayed, so the observed peak is `0.9·(1−0.1)=0.81`, never `center_intensity`, and the field's semantics drift from the documented model.
- **Fix** — `src/cipherchase/sdk/game_loop.py` (and the replay capture once IH-16 unifies it): order becomes **`decay_all()` then `deposit()`**. This is also the ordering the P2 delta-decoder (`Δ = τ_t − (1−ρ)·τ_{t−1}`) assumes — fixing it here prevents a P2 landmine. Documented in `smell.py` docstring as the canonical turn order.
- **Test** (`tests/sdk/test_game_loop.py` + `tests/domain/test_smell.py`): after a turn, `intensity_at(thief_pre_move_cell) == min(1.0, center_intensity + residue)` with the fresh deposit **undecayed**; a pure-domain test pins the decay→deposit sequence result exactly.

### IH-3 — `run_game` outcome default when `max_moves < survival_threshold`
- **Finding** (§2.3-8, audit): `outcome` is pre-initialized to `Outcome.SURVIVAL` (`game_loop.py:55`). If a (mis)configured `max_moves < survival_threshold`, the loop exhausts without any terminal from `rules.outcome` and the thief is **awarded survival it never earned**.
- **Fix** — `src/cipherchase/sdk/game_loop.py` + `src/cipherchase/shared/config.py`:
  - Loop default becomes `Outcome.TIE` (nothing was decided ⇒ tie score, honest).
  - Belt-and-braces: `ConfigManager.load` validates `movement_and_barriers.max_moves >= survival_threshold`, raising `ConfigError` otherwise (a signed config that can't decide a game is a contract bug both peers must see at startup).
- **Test**: a fixture config with `max_moves=3, survival_threshold=35` injected past validation → `run_game` returns `TIE`; `ConfigManager.load` on such a config dir → `ConfigError`.

### IH-4 — `SmellField.absorb` bounds / malformed-key tolerance
- **Finding**: `absorb` (`domain/smell.py:47`) is the **wire-facing** ingestion point (the opponent's `smell_grid` lands here), yet a malformed key (`"x"`, `"1,2,3"`) raises `ValueError`, out-of-board cells pollute the field, and negative/huge values are accepted — a hostile peer can crash or poison us.
- **Fix** — `src/cipherchase/domain/smell.py`: `absorb` uses the IH-17 codec's `parse_cell_key`; **skips** malformed keys and out-of-board cells; clamps each value to `[0, 1]` before applying; multiplies by config `pheromones.absorb_gain` (IH-12). Never raises on foreign data — bad input is silently dropped (zero-trust: our belief, our rules).
- **Test** (`tests/domain/test_smell.py`): `absorb({"bad": 1, "9,9": 0.5, "1,1": -3, "2,2": 99, "3,3": 0.4})` on a 7-board → only `(2,2)→1.0` (clamped) and `(3,3)→0.4·gain` land; no exception.

---

## 3. Wire the truth — F6 / F11 / F5 become real in the runnable path

### IH-5 — TrashTalk + intent actually run in every game (F6) 🔴
- **Finding** (§2.3-3): `strategy/trash_talk.py` is fully tested but has **zero production callers**; no real run ever produces a hint or an `intent="lie"` — F6 is hollow and the committed `intent` is always the dataclass default `"truth"`.
- **Fix** — `src/cipherchase/sdk/game_loop.py` (helper module `src/cipherchase/sdk/loop_support.py` if the ≤150 budget demands, see Risks):
  - Build once per game: `provider = build_provider({**cfg.private["llm"], **cfg.private["trash_talk"]}, gate)` (gate from IH-9) and `talk = TrashTalk(provider, TemplateProvider(), every_n_steps=…, lie_probability=…, rng=rng)` — all knobs from `[trash_talk]`, nothing literal.
  - Each mover turn: `intent = talk.choose_intent()`; `hint = talk.maybe_generate(TalkContext(role, step, own_move=decision.direction.value, intent=intent))` (cadence = `every_n_steps`, empty off-cadence).
  - `decision = dataclasses.replace(decision, intent=intent, hint=hint)` **before sealing**, so `move_payload` commits the real intent (§8.1 payload spec unchanged: `{step, state, move, intent}` — the hint rides **outside** the hash, as on the wire).
  - `SealBook.seal` gains an optional `extra` mapping merged into the stored record (not the hashed payload): `{"hint": hint}` — so the emitted log shows the bluffs the README/spec promise.
- **Test** (`tests/sdk/test_game_loop.py`): run with `every_n_steps=3` → records at steps 3, 6, … carry a non-empty `hint`, others `""`; with `lie_probability=1.0` every committed `intent == "lie"`, with `0.0` every `intent == "truth"`; template provider ⇒ still 0 tokens (no subprocess spawned — assert via a spy provider).

### IH-6 — Seeded determinism from `[play].seed`
- **Finding** (§2.3-5): `play.seed = 12345` is read by nothing, yet docs claim reproducible runs; `TrashTalk` defaults to an unseeded `random.Random()`.
- **Fix** — `src/cipherchase/sdk/game_loop.py`: `rng = random.Random(cfg.private["play"]["seed"])`, passed to `TrashTalk` (IH-5) and forwarded into brain params as `rng` for the P2 seeded tie-randomization (brains ignore it until P2 — the plumbing lands now so the config key is truthfully consumed).
- **Test**: two `run_game(cfg)` calls with the same config produce **byte-identical** `records` (including intents/hints, template provider); changing the seed changes at least one intent draw across a long game.
- **Honesty note**: the determinism claim is scoped to `provider="template"` (the graded/default mode); README wording updated accordingly (IH-20).

### IH-7 — Auto-email step honoring `[email].enabled` (F11) 🔴
- **Finding** (§2.3-6): README/PLAN claim the 4 artifacts are auto-emailed; `report/emit.py` only writes files, `GmailSender` has no production caller, and `[email].enabled/subject_template` are read by nothing. (TODO T330 is a false `[x]` — see IH-24.)
- **Fix** — `src/cipherchase/sdk/sdk.py`:
  - `SimulationSdk.write_reports(cfg, directory, *, generated_at, email_backend=None)` → after `emit.write_all`, if `cfg.private["email"]["enabled"]`: construct `GmailSender(gate, recipient=…, sender=…, backend=email_backend)` and `send(subject, paths)` with `subject = cfg.private["email"]["subject_template"].format(game_id=gid)`. Gate is the IH-9 instance (`service="gmail"` — already routed inside `GmailSender.send`).
  - `enabled=false` (default, committed config) ⇒ no send — CI/grader path untouched. Real backend is injected only by `scripts/send_sample_report.py` (built from `token.json` via the HW6 OAuth flow); `enabled=true` with no backend surfaces `GmailSender`'s existing `ConfigError`.
- **Test** (`tests/sdk/test_sdk.py`): fake backend + `enabled=true` → exactly one gated send whose MIME carries **4 JSON attachments** with the canonical filenames and the templated subject; `enabled=false` → backend never called; gatekeeper ledger shows the `gmail/send` event (ties into IH-11).

### IH-8 — Emitted declaration embeds the SIGNED Step-0 body (F5) 🔴
- **Finding** (§2.3-6): the emitted `declaration_*.json` (built by `report/artifacts.build_declaration`) contains groups/tokens/links but **not** the signed hardware/LLM/git-commit body that `peer/declaration.build_declaration` produces — the artifact doesn't match what the docs (and F5) describe, and `peer/declaration.py` + `shared/sysinfo.py` have no production callers.
- **Fix** — `src/cipherchase/sdk/sdk.py` + `src/cipherchase/report/artifacts.py`:
  - `_assemble` builds `signed = peer_declaration.build_declaration(team=game["group_id"], players=game["members"], role=cfg.role, git_commit=git_commit, llm=cfg.private["llm"], system=system_info(), version=VERSION)`.
  - `git_commit` resolution: `CIPHERCHASE_GIT_COMMIT` env var if set (league/CI), else one `git rev-parse HEAD` **through the gatekeeper** (`service="subprocess"`), else `"unknown"` — never a crash offline.
  - `artifacts.build_declaration` gains a `signed_declaration: Json` keyword and nests it in the artifact.
- **Test** (`tests/sdk/test_sdk.py`, `tests/report/test_artifacts.py`): the emitted declaration artifact contains `signed_declaration` whose `verify_declaration(...)` is `True`, whose `system` has the sysinfo keys, and whose `version == VERSION`; subprocess path mocked, ledger records it.
- **Follow-up**: regenerate `docs/sample-run/` with the new artifact shape (same commit), so the committed proof matches the code again.

---

## 4. Gatekeeper for real (R3) 🔴

### IH-9 — The runnable path constructs and uses `ApiGatekeeper`
- **Finding** (§2.3-2): `cli → sdk → game_loop` constructs **no** gatekeeper; `ApiGatekeeper.from_config` has zero production callers; `ClaudeCliProvider(gate=None)` silently bypasses the gate — R3's "wired, not decorative" is currently false in the only path that runs.
- **Fix**:
  - `src/cipherchase/sdk/sdk.py`: `gate = ApiGatekeeper.from_config(cfg, now=time.monotonic)` built once per match; threaded into `run_game(cfg, gate=…)` (LLM provider, IH-5), `GmailSender` (IH-7), git-commit probe (IH-8), and — when P1 lands — the `McpTransport` factory (IH-10).
  - `src/cipherchase/infra/llm_provider.py`: **drop the `gate: Any = None` default and the ungated branch** in `ClaudeCliProvider` — the gate is a mandatory constructor arg; `build_provider` requires it for any non-pure provider. `TemplateProvider` stays gate-free (pure Python, no external call — documented rationale, not an exemption).
- **Test** (`tests/infra/test_llm_provider.py`, `tests/sdk/test_sdk.py`): `ClaudeCliProvider` without a gate → `TypeError`; a self-match with a spy gate shows every external call (llm subprocess when configured, gmail send when enabled, git probe) passing through `execute()`.

### IH-10 — `_http_caller` gated (MCP sends)
- **Finding**: `McpTransport._send` calls the wire directly; the `mcp` bucket in `rate_limits.json` gates nothing.
- **Fix** — `src/cipherchase/infra/mcp_client.py`: `McpTransport(opponent_url, inboxes, *, gate, caller=None, timeout)` — gate mandatory; `_send` becomes `self.gate.execute(lambda: self._caller(tool, message), service="mcp", action=tool)`. `timeout` is supplied from `network.rpc_timeout_s` by the construction site (IH-12; production factory arrives with P1's `PeerRuntime`, tests construct directly).
- **Test** (`tests/infra/test_mcp_client.py`): stub caller + real gate over a fake clock → each send appends an `mcp/<tool>` ledger event; exhausting the bucket raises `GateLimitError` after the configured retries (queue-not-drop backoff observed via the injected `sleep`).

### IH-11 — Ledger flushed into the log artifact (auditability bonus)
- **Fix** — `src/cipherchase/sdk/sdk.py` + `report/artifacts.build_log`: the log artifact gains `"gatekeeper_ledger": gate.ledger` (list of `{service, action, status}`) — the grader can *see* R3 working in the committed sample run.
- **Test**: log artifact contains the ledger; entry count equals the spy-counted external calls; template-provider offline run yields a small but non-absent ledger (e.g., the git probe), proving the field is live.

---

## 5. Config truth (R4 / R11) — every key read or removed

### IH-12 — Key→consumer table; no silent keys, no shadowing literals 🟡
Every currently-ignored key gets exactly one of: a **consumer** (this PRD/PRD-referenced), or **removal** with a doc note. Code literals that shadow config die with the wiring.

| Config key | Today | Disposition (consumer) |
|---|---|---|
| `[belief].alpha` | ignored; `BeliefGrid` default `0.85` literal | `game_loop`/`make_replay` construct `BeliefGrid(size, trust, alpha=cfg.private["belief"]["alpha"])`; constructor default removed |
| `pheromones.min_center_intensity` | ignored; `SmellField` default `1e-3` | passed as `min_center` at both `SmellField` construction sites; default removed |
| `pheromones.absorb_gain` | ignored | `SmellField.absorb` gain factor (IH-4); stored on the field at construction |
| `[llm].step_deadline_seconds` | ignored; `ClaudeCliProvider` default `8.0` | `build_provider` passes it as `timeout`; default removed |
| `[network].rpc_timeout_s` | ignored; `McpTransport` default `30.0` | construction sites pass it (IH-10); default removed |
| `[gui].cell_px` | ignored | `gui/window.py` cell rendering size reads it via the cfg it already receives |
| `[paths].logs_dir` | ignored; CLI default `"logs"` literal | `cli.py`: `--out` default becomes `cfg` `[paths].logs_dir` (resolved after config load) |
| `[paths].log_filename` | ignored; `report/emit.filename` is canonical | **REMOVE** from both `game.toml` — two filename sources is the bug; `emit.py` stays the single authority (noted in PLAN §3) |
| `[play].seed` | ignored | seeded `rng` → TrashTalk now, brains at P2 (IH-6) |
| `[play].step_speed_seconds` | ignored offline | consumed by the GUI live loop; verified read or removed alongside the GUI truth pass (IH-21 disposition) |
| `[email].enabled` / `subject_template` | ignored | `SimulationSdk` email step (IH-7) |
| `rate_limiter_gatekeeper.concurrent_requests` / `queue_depth` (+ per-service copies in `rate_limits.json`) | ignored | **implement** semaphore + bounded queue (IH-13) — honoring `PRD_reporting_gui.md` §3.3 as written rather than amending it |
| `movement_and_barriers.max_barriers` (as brain input) | shadowed by `params.get("max_barriers", 14)` literal in `PoliceBrain` | threaded into brain params (IH-15) |
| strategy weights (`w_*`, `lambda_barrier`, `min_gain`, `horizon`) | config exists but code re-defaults each key | single source = config with validation (IH-14) |

- **Test** (`tests/test_config_files.py`): a "no dead keys" test — walk both `game.toml`/`game.json`/`rate_limits.json` against an explicit allowlist of consumed keys maintained beside the test; any new unconsumed key fails CI. Plus one targeted test per wiring above (e.g., `alpha=1.0` config ⇒ `diffuse` is identity; `step_deadline_seconds=0.1` ⇒ provider timeout observed by a slow fake).

### IH-13 — Gatekeeper concurrency semaphore + bounded queue (per PRD_reporting_gui §3.3)
- **Finding**: §3.3 promises `max_concurrent = 2` (semaphore) and `queue = 100` with DOS rejection; TODO T309 is checked; **neither exists** in `shared/gatekeeper.py`.
- **Fix** — `src/cipherchase/shared/gatekeeper.py`: add `threading.BoundedSemaphore(concurrent_requests)` acquired around `fn()`, and a waiting-count guard — if callers waiting ≥ `queue_depth`, raise `GateLimitError("queue overflow")` immediately (reject the burst; those admitted queue FIFO, never dropped). `from_config` reads both keys from `rate_limiter_gatekeeper`. File is 75 lines today; fits ≤150.
- **Test** (`tests/shared/test_gatekeeper.py`): with `concurrent_requests=1`, two threads through a blocking `fn` never overlap (event-flag assertion); with `queue_depth=1`, a third simultaneous caller gets `GateLimitError`; single-threaded behavior unchanged (existing suite green).

### IH-14 — Brain weights: single source = config, schema-validated
- **Finding**: `PoliceBrain._w` / `ThiefBrain._weight` each re-declare defaults (`1.0`, `0.5`, `0.3`…) — a second source of truth silently masking config typos (`w_beleif = …` would be ignored); `NaN` passes straight into scores.
- **Fix** — `src/cipherchase/domain/brains.py` + both heuristics: one `BrainBase.param(key) -> float` (no default arg). `load_brain` (`strategy/factory.py`) validates at construction against the class's declared `PARAM_KEYS` (e.g., `PoliceBrain.PARAM_KEYS = ("w_dist", "w_center", "w_belief", "lambda_barrier", "min_gain", "max_barriers")`): missing key, non-numeric, `NaN`/`±inf` → `ConfigError` naming the key. Committed configs already carry every key, so no behavior change on the happy path.
- **Test** (`tests/strategy/test_factory.py`): config missing `w_dist` → `ConfigError("w_dist")`; `w_dist = nan` → `ConfigError`; valid config loads with identical decisions to today (golden-game regression).

### IH-15 — `max_barriers` threaded from `movement_and_barriers`
- **Fix** — `src/cipherchase/sdk/game_loop.py` (and IH-16's unified capture path): `load_brain(strat["police_class"], board, params={**strat, "max_barriers": mb["max_barriers"], "rng": rng})`; `PoliceBrain._candidates` uses `self.param("max_barriers")` — the `14` literal dies.
- **Test**: config with `max_barriers=0` ⇒ brain never proposes a barrier and the engine never places one; `PARAM_KEYS` validation covers absence.

---

## 6. Duplication (R2)

### IH-16 — `make_replay_data` reuses `run_game` via a frame-callback hook
- **Finding** (§2.3-7): `scripts/make_replay_data.py` is a ~35-line **clone of the engine** (already drifted: different termination handling, no survival outcome path, pre-IH ordering) — the replay could silently diverge from the game it claims to depict.
- **Fix** — hook design, `src/cipherchase/sdk/game_loop.py`:
  ```python
  OnFrame = Callable[[dict[str, Any]], None]
  def run_game(cfg: Any, *, gate: Any = None, on_frame: OnFrame | None = None) -> GameResult: ...
  ```
  Once per step, immediately after the cop belief is computed (pre-move — the same instant the current script captures), emit `{"turn": step, "cop": [r,c], "thief": [r,c], "barriers": [...], "scent": smell.snapshot(), "belief": cop_belief.as_matrix()}`. `None` costs nothing. `scripts/make_replay_data.py` collapses to: load config → `frames = []` → `run_game(cfg, on_frame=frames.append)` → write `{"size", "outcome": result.outcome.value, "frames"}`. The cloned engine block is **deleted**.
- **Test** (`tests/sdk/test_game_loop.py`): frame count == `result.turns`; each frame's cop/thief/barriers agree with the sealed records of the same step (cross-check — doubles as another IH-1 witness); `on_frame=None` output unchanged.
- Regenerate `docs/sample-run/replay3d.json` from the unified engine (same commit as IH-2, since ordering shifts the scent values).

### IH-17 — One `"r,c"` codec in `domain/`
- **Finding**: the `f"{r},{c}"` encode and `key.split(",")` decode appear at 4+ sites (`smell.snapshot`, `smell.absorb`, `belief.observe_smell`, `game_loop._thief_belief_of_cop`, `make_replay_data`).
- **Fix** — `src/cipherchase/domain/canonical.py` (the canonical-encoding home): `cell_key(cell: Cell) -> str` and `parse_cell_key(key: str) -> Cell` (raises `ValueError` on malformed input; `absorb` catches it per IH-4). All listed sites switch to the helpers; a ruff-friendly grep in the line-check script is unnecessary — the unit tests + review own it.
- **Test** (`tests/domain/test_canonical.py`): round-trip property over the board; malformed inputs (`"x"`, `"1"`, `"1,2,3"`, `"a,b"`) raise `ValueError`; snapshot/observe_smell interop unchanged (existing suites stay green through the swap).

### IH-18 — Merge `_w` / `_weight` into `BrainBase.param()`
- **Fix**: subsumed by IH-14's `BrainBase.param` — both private copies are deleted; kept as its own ID so the TODO can tick the R2 half independently of the validation half.
- **Test**: existing brain suites green via `param`; `grep -r "_weight\|def _w(" src` finds nothing (asserted in review, not CI).

---

## 7. Version check live (R6)

### IH-19 — `check_compatible` invoked at startup
- **Finding** (§2.3-4): `shared/version.py:check_compatible` is documented as "the startup guard" and has **zero production callers** — R6 decorative.
- **Fix** — `src/cipherchase/shared/config.py`: `ConfigManager.load` calls `check_compatible(shared["version"])` and `check_compatible(private["version"])` right after parsing (every entry — CLI, SDK, scripts, future `peer` command — flows through `load`, so one wiring point covers all). `IncompatibleVersionError` propagates to the CLI as a clean non-zero exit.
- **Test** (`tests/shared/test_config.py`, `tests/test_cli.py`): a config dir with `"version": "2.00"` → `ConfigManager.load` raises `IncompatibleVersionError`; CLI run against it exits non-zero with the message; happy path unchanged.

---

## 8. Doc-truth reconciliation — every claim demonstrably true

### IH-20 — README numbers & claims corrected
- **File**: `README.md`. Fixes: **"195 tests" → the verified current count (205 collected today)**, kept honest by the IH-28 CI guard; determinism wording scoped to template mode (IH-6); §2's "every external call … through `ApiGatekeeper`" becomes true via IH-9/10 (no wording change needed once code lands — verify, don't soften); §5's per-turn "committed → revealed" sentence gets a footnote that the wire flow is being aligned to the reference choreography (P1) while the audit semantics described remain exact.
- **Test**: IH-28 CI step; manual claim-by-claim pass recorded in the P0 closing commit message.

### IH-21 — Ghost modules: build (P1) or amend — explicit dispositions
| Claimed (PLAN §3 / TODO / README) | Exists? | Disposition |
|---|---|---|
| `peer/runtime.py` (`PeerRuntime`) · `sdk` `run_peer`/`run_series` · `peer/controls.py` · `peer/control_link.py` | no | **P1 builds them** (`PRD_league_runtime.md`); PLAN §3 rows annotated "(P1)" until then |
| `strategy/talk_providers.py` | no — providers live in `infra/llm_provider.py` | **amend** PLAN §3 + TODO T231 wording to the real module |
| `strategy/qlearning.py` | no | **amend**: PLAN marks it "designed, not shipped"; README §4 already phrases it as future — keep |
| `strategy/reach.py` (TODO T183) | no — BFS lives in `domain/rules.reachable_cells` | **amend** TODO (see IH-24); no extraction needed (single implementation already) |
| `gui/board_view.py`, `live_apply.py`, `live_controls.py`, `replay_controls.py` | no — folded into `window.py`/`replay.py` | **amend** PLAN §3 to the real 4-module gui layout |
| `py.typed` | no | **ship it** — one empty marker file + hatchling package-data line (cheap truth) |
- **Test**: IH-23's inventory test (below) prevents regression.

### IH-22 — Deploy-tunnel commands must parse
- **Finding**: `docs/deploy-tunnel.md` step 1 runs `uv run cipherchase --role police --config config/police` — the current CLI has a required positional `command` and **no `--role`**; the documented command errors out.
- **Fix** — `docs/deploy-tunnel.md`: rewrite the command to the real P1 CLI (`cipherchase peer --role police --config config/police`) **in the same commit that lands the P1 `peer` subcommand**; until then the doc carries the truthful interim line (`# peer subcommand ships with the league runtime (PRD_league_runtime)`) so no committed doc shows a non-parsing command at any point.
- **Test** (`tests/test_cli.py`): a doc-truth test extracts every fenced `cipherchase …` invocation from `README.md` + `docs/deploy-tunnel.md` and asserts `_parser().parse_args` accepts it (or the line is explicitly marked future). Executable documentation — a grader-visible flourish.

### IH-23 — PLAN §3 inventory updated to the real tree
- **Fix** — `docs/PLAN.md` §3: module tables regenerated to match `src/cipherchase/**` exactly (add `police_expectimax.py`, `domain/brains.py` seam notes, real gui/peer layouts, `[paths].log_filename` removal note, IH-21 dispositions).
- **Test** (`tests/test_config_files.py` or a new `tests/test_docs_truth.py`): parse PLAN §3's backticked module names; assert each exists on disk (allowlist for explicitly "(P1)"-tagged rows); assert no `src/cipherchase/**/*.py` module is absent from the inventory.

### IH-24 — TODO.md false-`[x]` corrections
Uncheck (or re-scope with a pointer) each item the audit proved untrue; every one maps to a real fix or an honest deferral:

| Task | Why false today | Correction |
|---|---|---|
| T164 (seeded tie-break in `most_likely`) | argmax uses plain sorted order, no seed | uncheck → P2 (seeded tie-randomization is a winning-brain feature); wording fixed |
| T183 (`strategy/reach.py` extraction) | module doesn't exist | re-scope: "BFS single-sourced in `domain/rules.py`" → check only after wording fix |
| T184 (`cut_bonus` + self-trap guard) | neither term in `police_heuristic` | uncheck → P2 (barrier discipline rework) |
| T192 (thief `w_scent` term) | `w_scent` read by nothing | uncheck → P2 thief hardening consumes it (or the key is removed there); listed in IH-12 as P2-owned |
| T225 (seeded `rng.choice` over HONEST/BLUFF banks) | provider indexes `step % len(phrases)` | re-scope to actual design; seeding arrives via IH-6 at the TrashTalk level |
| T234 (gatekeeper wiring "asserted") | wired in tests only, not the runnable path | check stays, but annotated "runtime wiring = IH-9" |
| T236 ("gated to something-to-hide") | `choose_intent` is a plain Bernoulli | wording fixed to match code |
| T309 (semaphore + queue in gatekeeper) | not implemented | uncheck → re-check when IH-13 lands |
| T330 (`emit.py` hands to email via gatekeeper) | emit only writes files | uncheck → re-check when IH-7 lands (design note: the email step lives in `sdk.py`, not `emit.py` — wording fixed) |
- **Test**: none automatable beyond IH-23's spirit; the P0 exit audit re-reads TODO against code.

### IH-25 — `viz/index.html` and the ≤150 rule (R8 stance: SPLIT)
- **Finding**: 265 lines, outside `check_file_lines.py`'s `*.py` glob — a pedant's "you hid your biggest file from your own checker". *(RESOLVED: P4 split it into ES modules — index.html is 80 lines and the checker now covers `viz/`.)*
- **Fix** (recommended and chosen: **split**, not exemption): extract the inline JS into `viz/js/scene.js`, `viz/js/frames.js`, `viz/js/controls.js` (each ≤150 lines, single purpose: Three.js scene/board build · frame data + tween state · UI/timeline/new-match fetch), leaving `index.html` ≤150 as markup + module imports. Extend `scripts/check_file_lines.py` to include `viz/*.html` and `viz/js/*.js` (raw-line rule; `viz/vendor/` + `node_modules/` excluded as third-party). The checker script itself stays ≤150.
- **Test**: line-checker run in CI covers the new globs; a manual browser smoke of the 3D arena before/after (no behavior change).

---

## 9. CI hardening

### IH-26 — `uv sync --frozen`
- **Fix** — `.github/workflows/ci.yml`: `uv sync --dev` → `uv sync --dev --frozen` (lockfile is the truth; CI can't silently resolve new versions). Commit `uv.lock` if not already tracked.

### IH-27 — Self-match smoke step (the runnable path, proven on every push)
- **Fix** — `.github/workflows/ci.yml`, after tests:
  ```yaml
  - name: Self-match smoke — the 4 artifacts exist (R-proof of the runnable path)
    run: |
      uv run cipherchase self-match --config config/police --out /tmp/smoke
      test "$(ls /tmp/smoke/*.json | wc -l)" -eq 4
  ```
  After IH-5/7/8/9/19 this one step also exercises: version check, gatekeeper construction, live hints, signed declaration, ledger-in-log. Cheap, loud, and exactly what a grader would type.

### IH-28 — Tests-count honesty guard
- **Fix** — CI step comparing the README's stated test count with reality: `n=$(uv run pytest --collect-only -q | tail -1 | grep -o '^[0-9]*')` vs the number in README's quick-start line; mismatch fails the build. README's count can never rot again (the root cause of the "195 vs 205" finding).

---

## 10. TDD plan · Milestone · Traceability · Risks

### TDD order (each: red test → minimal fix → ruff/lines/cov gate → commit)
1. Pure-domain first: IH-17 codec → IH-4 absorb → IH-2 ordering (domain test) → IH-14/18 param+validation → IH-15.
2. Engine: IH-1 barriers-in-payload (the headline regression test) → IH-3 outcome default → IH-16 frame hook → IH-2 engine test → IH-6 seed → IH-5 trash-talk wiring.
3. Cross-cutting: IH-13 semaphore/queue → IH-9/10 gate wiring → IH-11 ledger → IH-19 version check → IH-7 email → IH-8 signed declaration.
4. Truth pass: IH-12 dead-key test + wirings · IH-20–25 docs · regenerate `docs/sample-run/` · IH-26/27/28 CI.
   All new/changed files stay **≤150 lines raw+logical** (markdown exempt by rule); coverage floor ≥85% held (project actual: 100% — keep it).

### Milestone M-IH (binary)
> **A re-run of the four audits yields zero open §2.3 findings, and every claim in README / PLAN / TODO / deploy-tunnel is demonstrably true in the runnable path** — witnessed by: the IH-1 regression test green; a self-match log containing non-empty hints, real intents, `barriers` in sealed payloads, a verifying `signed_declaration`, and a non-empty `gatekeeper_ledger`; the IH-27 CI smoke green; the dead-key test green.

### Traceability
| Req | Rubric/Gate | | Req | Rubric/Gate |
|---|---|---|---|---|
| IH-1..3 | Integrity metric, F3/F4 soundness | | IH-13 | R3/R4, NFR-4/5, PRD_reporting_gui §3.3 |
| IH-4 | zero-trust ingestion (F7) | | IH-14/15/18 | R2/R4/R11 |
| IH-5/6 | **F6**, R11 (`[play].seed`) | | IH-16/17 | **R2** |
| IH-7 | **F11**, R3 | | IH-19 | **R6** |
| IH-8 | **F5** | | IH-20..25 | docs≡code (Architecture metric), R8 (IH-25) |
| IH-9..11 | **R3** | | IH-26..28 | R13 CI, grader-auth path |
| IH-12 | **R4/R11** | | | |

### Explicitly deferred (with rationale — not silently dropped)
- **Thief sees the cop's true position** (§2.3-8b): the fix is the same delta-belief mechanism the cop gets — owned by **P2** (`PRD_winning_brain.md`); `game_loop`'s docstring already discloses the simplification honestly, so it is not a doc-truth violation today.
- **Per-turn commit→reveal wire flow** (§2.1): replaced wholesale by **P1**; IH tests deliberately target engine truth (sealed payload contents), not message shape, to survive that rework.
- **`[paths].log_filename`**: judged **not worth implementing** — a second filename authority beside `report/emit.py` is itself a defect; removal (IH-12) is the fix.

### Risks
| Risk | Mitigation |
|---|---|
| `game_loop.py` (93 lines) breaches ≤150 with talk + gate + frames + seed | pre-emptive split: `sdk/loop_support.py` (talk/belief/frame helpers), designed in IH-5; both files ≤150 |
| P1 sealing rework invalidates IH-1/5 tests | tests assert record *content* vs engine truth, never wire choreography |
| Regenerated `docs/sample-run/` breaks README screenshots | regenerate artifacts + screenshots in one commit; replay-verify before committing |
| IH-13 threading flakiness in CI | event-flag synchronization (no sleeps); deterministic injected clock |
| Determinism claim vs live LLM provider | claim scoped to template mode (IH-6/IH-20); live provider hints are non-hashed extras so audits stay deterministic |
