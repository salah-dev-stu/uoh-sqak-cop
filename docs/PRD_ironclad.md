# PRD_ironclad — CipherChase: Ironclad Rigor (Exhaustive Tamper Sweep · Property-Based Tests · Golden Wire Transcripts · Doc/Config Truth Guards)

## 1. Header

| Field | Value |
|---|---|
| **Mechanism** | Ironclad rigor — rigor that ends arguments: exhaustive tamper proof, ∀-quantified invariants, byte-pinned wire transcripts, leftover truth guards |
| **Phase** | **P8** of the Phenomenal plan (`PLAN-PHENOMENAL.md` §2, items 12–14 of §1) |
| **Serves** | **Integrity** chapter (F3/F4 made *exhaustively* proven) · **R7** (TDD depth-of-rigor) · R9 (coverage stays 100%) · doc-truth (IH-12/22/23 leftovers) |
| **Modules touched** | Tests + one script ONLY. Zero production-code changes: `tests/integrity/*`, `tests/properties/*`, `tests/interop/golden/*` + `tests/interop/test_golden_transcript.py`, `tests/shared/…` guards, `scripts/make_golden_transcript.py` |
| **Dependency changes** | `hypothesis>=6.100` added to `[dependency-groups].dev` in `pyproject.toml` **only** (never a runtime dependency; `real` extra untouched) |
| **Version** | 1.00 (single-source `shared/version.py`) |
| **Status** | Per-mechanism draft — approve before TODO §Phenomenal (T623+) build |
| **Depends on** | `domain/crypto.py` (`CommitReveal`, `audit_records`) · `domain/canonical.py` · `domain/belief.py` · `domain/board.py` · `domain/protocol.py` · `peer/turn_handler.py` · `gui/replay_data.py` · `tests/fakes/fake_transport.py` (`.sent` tap) · committed sample log `docs/sample-run/log_uoh-sqak-police-02da547b_g01.json` |
| **Absorbs** | Leftover TODO guard tasks **T430** (dead config keys), **T463** (doc-truth CLI), **T465** (PLAN §3 inventory), and **T518** (golden transcripts) |
| **Cut order** | golden transcripts → property tests → **(never cut) tamper sweep** (PLAN-PHENOMENAL §3) |

---

## 2. Purpose

The integrity story currently rests on *sampled* evidence: a handful of tamper tests, one tampered replay fixture, an every-commit reference tripwire. P8 upgrades each claim from "tested" to "quantified over the whole space we can enumerate":

- **Tamper sweep** — not "a tampered record is caught" but "**all N mutations of the real committed log are caught, N = 1807 today, 0 escapes**" — a one-line Integrity proof no prose can match.
- **Property tests** — not "these payloads round-trip" but "**∀ JSON-able payloads** round-trip; ∀ perturbations fail; ∀ op sequences the belief stays a distribution; ∀ hostile dicts the boundary never crashes."
- **Golden transcripts** — the interop tripwire's deterministic twin: every byte shape we ever emit is frozen on disk and replayed on every commit, with and without the reference repo present.
- **Truth guards** — the last three unchecked doc/config-honesty tasks land here so P8 closes the "no false claim anywhere" milestone for good.

Everything in this PRD is test-side. If a property test finds a real production bug, the fix is its own commit with its own regression test — this PRD does not license drive-by production edits.

---

## 3. Requirements

### 3.1 Exhaustive tamper sweep — `tests/integrity/test_tamper_sweep.py`

**IC-1 — Sweep target is the real committed artifact.** The sweep loads `docs/sample-run/log_uoh-sqak-police-02da547b_g01.json` and takes its `records` list (70 sealed `{payload, nonce, commit}` triples; payload schema `{step:int, state:{pos:[r,c], barriers:[[r,c]…]}, move:str, intent:str}`). A precondition test asserts the pristine log passes `audit_records` (`passed=True`, `failed_steps==[]`) — the sweep proves *discrimination*, not just rejection.

**IC-2 — Deterministic mutation generator, precisely specified.** A helper module `tests/integrity/mutations.py` exposes `mutations_of(records) -> Iterator[tuple[str, int, list[dict]]]` yielding `(label, record_index, mutated_records)` — each item a **deep copy** of the full record list with **exactly one** field perturbed. No randomness anywhere; the generator is a pure function of the log bytes. Per record at index `i`, in this fixed order:

| # | Class | Mutation (all guaranteed to change the canonical bytes) | Count/record |
|---|---|---|---|
| a | `step` | `step+1` and `step-1` | 2 |
| b | `move` | replaced by the **next** value in the fixed cycle `("N","S","E","W","STAY")` (next-of-current, hence always different) | 1 |
| c | `intent` | toggled: `"lie"` if currently `"truth"`, else `"truth"` | 1 |
| d | `state.pos` | each coordinate `±1`: `pos[0]+1`, `pos[0]-1`, `pos[1]+1`, `pos[1]-1` | 4 |
| e | `state.barriers` | if `len ≥ 2`: list reversed (canonical JSON preserves array order; entries are distinct cells, so bytes change); else: `[9,9]` appended (off-board, never present) | 1 |
| f | `nonce` | hex char at position `i mod 32` replaced by `hex((int(ch,16)+1) % 16)` — always a different char | 1 |
| g | `commit` (nibble classes) | for **each distinct hex-digit value** `v` present in the 64-char commit (sorted ascending), the **first occurrence** of `v` is replaced by `hex((v+1) % 16)` | `D_i` (14–16 observed) |

**IC-3 — Count formula and floor.** Expected total `N = Σ_i (9 + D_i) = 10·R + Σ_i (D_i) − R` … stated exactly: `N = R·10 + Σ_i D_i` where `R = len(records)` and `D_i = |{distinct hex digits in commit_i}|` (rows a–e give 9 payload mutations, row f gives 1, row g gives `D_i`). For the committed log: `R = 70`, `Σ D_i = 1105` → **`N = 700 + 1105 = 1805`**. The test asserts `N ≥ 500` (PLAN-PHENOMENAL §2 P8 acceptance floor) so a regenerated shorter sample run still satisfies the gate.

**IC-4 — Zero escapes, asserted per mutation and in aggregate.** For every yielded mutation: `audit_records(mutated)` must return `passed=False` **and** include exactly `record_index` in `failed_steps` (localisation, not just rejection). Escapes are accumulated and the final assert reads `assert not escapes, …` with a message embedding the tally, and the closing assert emits the headline count: `assert caught == total and total >= 500, f"tamper sweep: {caught}/{total} mutations caught"` — so the number is visible in test output.

**IC-5 — The Replay Viewer path agrees.** One additional test drives a **sample** of the sweep (first mutation of each class per record — `7·R` cases) through `gui/replay_data.verify_records` / `replay_verdict` and asserts the mutated step is `"TAMPERED"` and the verdict is `BAD`. This proves the GUI verdict path (F12) discriminates with the same power as the auditor, without doubling the full sweep's runtime.

**IC-6 — README honesty line, guard-enforced.** README's Integrity section gains the line "**1807 mutations, 1807 caught**" (exact wording contains `<N> mutations, <N> caught`). The sweep test parses that line out of `README.md` and asserts both numbers equal the computed `N` — same self-honesty pattern as the tests-count CI guard (T472). Regenerating the sample log without updating the README fails CI.

### 3.2 Property-based tests (`hypothesis`, dev-dep) — `tests/properties/`

**IC-7 — Crypto: ∀-payload seal/verify round-trip + tamper detection.** Strategy: `json_values = st.recursive(st.none() | st.booleans() | st.integers(-10**6, 10**6) | st.floats(allow_nan=False, allow_infinity=False) | st.text(max_size=20), lambda kids: st.lists(kids, max_size=4) | st.dictionaries(st.text(max_size=10), kids, max_size=4), max_leaves=12)`; payloads = `st.dictionaries(st.text(min_size=1, max_size=10), json_values, max_size=6)`. Properties: (a) `seal(p)` → `verify(p, nonce, commit)` never raises; (b) `verify` with any single nonce-char perturbation (index drawn by hypothesis, replacement = next hex char) raises `CryptoError`; (c) `verify` with any single commit-char perturbation raises `CryptoError`. (NaN/inf are excluded because `canonical_json` inherits `json.dumps` behaviour for them — out of the sealed contract by construction.)

**IC-8 — canonical_json: key-order independence + idempotent parse.** ∀ payloads from the IC-7 strategy: (a) `canonical_json(d) == canonical_json(shuffled(d))` where `shuffled` rebuilds the dict with keys in hypothesis-drawn permutation order (recursively for nested dicts); (b) `json.loads(canonical_json(d))` equals `d` and `canonical_json(json.loads(canonical_json(d))) == canonical_json(d)` (idempotence through a parse cycle); (c) `sha256_hex` equality follows from (a).

**IC-9 — BeliefGrid: distribution invariant under arbitrary op sequences.** Strategy: op lists (`max_size=30`) over `observe_smell` (smell dicts with keys `"r,c"` for in-board cells, floats in `[0, 5]`), `exclude` (any in-board cell), `diffuse`. After **every** op on a `BeliefGrid(7, smell_trust=4.0, alpha=0.85)`: `abs(sum(masses) − 1.0) ≤ 1e-9` and every mass `≥ 0.0`; `most_likely()` returns an in-board cell. Includes the pathological path: excluding cells until total mass would hit 0 must re-uniformise, never divide by zero.

**IC-10 — Board: legality closure.** ∀ board size 7, ∀ in-board cell, ∀ barrier sets (frozensets of in-board cells drawn by hypothesis, cell itself removed): every direction returned by `legal_moves(cell, barriers)` satisfies — `STAY` maps to `cell`; every other direction passes `step(cell, d, barriers)` **without raising** and the result is `in_bounds` and `not in barriers`. Conversely, every direction *not* returned (excluding STAY) makes `step` raise `IllegalMoveError`.

**IC-11 — Boundary fuzz: the lenient wall never crashes.** ∀ arbitrary dicts `st.dictionaries(st.text(max_size=15), json_values | st.binary(max_size=8).map(list), max_size=8)` (i.e. hostile keys, wrong types, missing everything): (a) `TurnMessage.from_dict(d)` either returns a `TurnMessage` or raises **only** `(TypeError, ValueError)` — never `KeyError`/`AttributeError`; (b) `turn_handler.process(rt, d)` with a stub runtime (FakeTransport pair, real decoder) **NEVER raises** — it returns an `Incoming` with `malformed=True` or a normal outcome (matches the module's contract: "malformed rejected without a crash"). This is the fuzz twin of the lenient-parser interop rule (PRD_league_runtime §2.4).

**IC-12 — Hypothesis settings: CI-deterministic profile.** A `tests/properties/conftest.py` registers profiles: `ci` = `settings(max_examples=100, deadline=None, derandomize=True)` (fixed example sequence — no flaky shrink storms in CI); `dev` = `settings(max_examples=300, deadline=None, print_blob=True)` (reproduction blobs printed so any local failure is replayable via `@reproduce_failure`). CI selects `ci` via `HYPOTHESIS_PROFILE=ci` in the workflow; default profile is `dev`. `deadline=None` everywhere — wall-clock flakiness on the 8 GB M2 and shared CI runners is a known hypothesis trap.

### 3.3 Golden wire transcripts (absorbs T518) — `tests/interop/golden/` + `scripts/make_golden_transcript.py`

**IC-13 — Blessed capture, deterministic.** `scripts/make_golden_transcript.py` runs one FakeTransport loopback series (template provider, fixed seed from config — zero LLM, zero network) and captures **every** outbound message from both peers via the `FakeTransport.sent` tap (`(tool, arg_key, wire_dict)` triples) into `tests/interop/golden/transcript.json`: `{"_schema": "golden-transcript/1", "seed": …, "generated_at": …, "messages": [{"tool": …, "arg_key": …, "wire": …}, …]}`. Two consecutive script runs must produce byte-identical `messages` (the script asserts this itself before writing; `generated_at` is the only volatile field). The fixture is committed; it is data, exempt from the 150-line code budget (checker covers code files).

**IC-14 — Fast replay tests, dual-parser.** `tests/interop/test_golden_transcript.py` (no skip — runs everywhere, every commit):
- every `receive_turn` wire dict parses through **our** `TurnMessage.from_dict` and its key set **equals exactly** the frozen §2.4 wire key set `{step, sender, hint, smell_grid, commit, timestamp, barrier_placed, capture_claim, claim_response, win_claim}` — no more, no less (strict foreign parsers do `cls(**data)`);
- every `submit_audit` message uses `arg_key == "payload"` and parses through `AuditPayload.from_dict`; every audit record is a `{payload, nonce, commit}` triple that passes `CommitReveal.verify`;
- **when `../reference-repo/src` is present** (same detection as `test_reference_tripwire.py`), every turn wire dict ALSO parses through the reference's strict `police_thief.domain.protocol.TurnMessage.from_dict` (`cls(**data)`, no filtering).
The test file carries the comment: `# transcript drift = interop break: if this fails, the wire contract changed — bump PLAN §8 / INTEROP-CONTRACT.md consciously or revert.` Regeneration is a deliberate act: rerun the script, review the diff, commit fixture + explanation together.

### 3.4 Leftover truth guards absorbed (T430 · T463 · T465)

**IC-15 — Dead-config-keys guard (T430, IH-12/NFR-11).** A test walks every key path in `config/{police,thief}/game.toml`, `game.json`, and `rate_limits.json` (dotted-path flattening) and checks each against an **explicit consumed-key allowlist** maintained in the test module, where every entry names its consuming module in a comment. Any config key absent from the allowlist fails with "unconsumed config key: <path> — wire it or delete it (R11)"; any allowlist entry absent from the configs fails symmetrically (stale allowlist). Adding a config key without a consumer becomes a CI failure.

**IC-16 — Doc-truth CLI guard (T463, IH-22).** A test extracts every fenced code line matching `cipherchase <args>` (incl. `uv run cipherchase …`) from `README.md` and `docs/deploy-tunnel.md` and feeds the argv tail to `cli._parser().parse_args` — parse must succeed (SystemExit(0-free)) for every command, **except** lines explicitly annotated with a `<!-- future -->` marker (or a `# future:` prefix inside the fence), which are collected and asserted to still be marked. A documented command that the CLI cannot parse fails CI.

**IC-17 — PLAN-inventory guard (T465, IH-23).** A test parses the PLAN §3 module-inventory table and asserts (a) every listed module path exists on disk under `src/cipherchase/`, with rows annotated "(P1)" (or any "(P<n>)" future marker) allowlisted; (b) every `src/cipherchase/**/*.py` module (excl. `__init__.py`, `__pycache__`) appears in the inventory. Docs and code can no longer drift silently.

---

## 4. Acceptance criteria (binary, offline, no keys)

| # | Check |
|---|---|
| A1 | Tamper sweep: **≥ 500 mutations, 0 escapes** (current log: 1807/1807), each localised to its record index; pristine log passes (IC-1..4) |
| A2 | Replay-viewer sample sweep: all mutated steps `TAMPERED` (IC-5); README "N mutations, N caught" line matches computed N (IC-6) |
| A3 | All hypothesis suites green in CI at the pinned `ci` profile (`max_examples=100`, `derandomize=True`, `deadline=None`) (IC-7..12) |
| A4 | Golden transcript: capture script self-checks determinism; replay test green with our parser everywhere and with the reference's strict parser when `../reference-repo` is present (IC-13/14) |
| A5 | The 3 truth guards green: zero unconsumed config keys, every documented CLI line parses or is marked future, PLAN §3 ↔ disk in both directions (IC-15..17) |
| A6 | Coverage stays **100%** (`--cov-fail-under` untouched; new tests only add coverage); `ruff` 0; every new code file ≤ 150 raw+logical lines |
| A7 | Full-suite runtime increase **≤ +30 s** on the M2 baseline (sweep is pure hashing ≈ 1800 SHA-256 ops; hypothesis capped at 100 examples/property) |
| A8 | `hypothesis` appears in `[dependency-groups].dev` only; `uv.lock` updated; runtime `dependencies` and `real` extra unchanged |

---

## 5. TDD plan

Order (matches the cut order in reverse — never-cut lands first):

1. **T-sweep:** write `mutations.py` + a unit test of the generator itself (exact per-record count `9 + D_i`, all labels unique, one-field-changed invariant vs the pristine deep copy) → then the sweep test (fails only if the auditor ever misses) → then IC-5 GUI sample and the IC-6 README guard (red until the README line is added).
2. **T-props:** one property file at a time — crypto → canonical → belief → board → fuzz — each committed with the `ci` profile pinned; any production bug a property uncovers is fixed in its own commit with a minimal non-hypothesis regression test alongside.
3. **T-golden:** write the replay test first against a hand-rolled 2-message fixture (red on key-set drift), then the capture script, regenerate the real fixture, delete the hand-rolled one.
4. **T-guards:** each guard test written red first (seed one deliberate violation locally to watch it fail), then the allowlist/annotations completed until green.

## 6. Edge cases & policies

- **Hypothesis flakiness policy:** CI uses `derandomize=True` — identical example sequence every run; **no** `@flaky` reruns, no time-based deadlines (`deadline=None`). A CI failure is therefore always reproducible locally with `HYPOTHESIS_PROFILE=ci`. Locally-found failures ship the printed blob in the fixing commit message.
- **Golden regeneration workflow:** transcript drift = interop break by default. Legitimate wire changes (there should be none post-freeze) require: rerun script → eyeball the JSON diff → update INTEROP-CONTRACT.md/PLAN §8 in the same commit → note in PROMPTS.md. The script refuses to overwrite if its two internal runs disagree (non-determinism regression).
- **Sample-log regeneration:** regenerating `docs/sample-run/` changes `R`, `Σ D_i`, hence `N` — IC-6 forces the README number to move in the same commit. The `N ≥ 500` floor keeps the gate meaningful for any realistic run length (`R ≥ ~22`).
- **Float payloads:** NaN/±inf excluded from crypto strategies (JSON contract); belief property uses finite non-negative smells only — negative smell is not a wire-legal input (smell fields are intensities).
- **`turn_handler.process` fuzz stub:** the stub runtime provides the same attribute surface the real `PeerRuntime` does (`history`, `last_seen_step`, `barriers`, `belief`, `decoder`, `me`, `role`, `opp_role`, transport for `send_final`); the fuzz property holds for both roles.

## 7. Risks

| Risk | Mitigation |
|---|---|
| Hypothesis shrink storms / nondeterministic CI noise | `derandomize=True` + fixed `ci` profile + `deadline=None`; examples capped at 100; failures replayable via blob (IC-12) |
| Sweep runtime growth if the sample log grows | pure-hash cost is linear (~1800 verifies ≈ well under 1 s); IC-5 GUI pass runs a 7·R sample, not the full cross-product |
| Property test finds a real bug near the deadline | that is the point — fix in an isolated commit; if a fix is risky, `xfail(strict=True)` with a linked TODO task rather than weakening the property |
| Golden fixture accidentally regenerated/blessing drift | script self-check + "drift = interop break" comment + review-the-diff workflow; test runs on every commit with no skip |
| Guard allowlists rot into rubber stamps | allowlists live inside the tests with a consumer/module comment per entry; symmetric checks (IC-15b, IC-17b) fail on stale entries too |

## 8. Traceability & budgets

- **Rubric/gates:** F3/F4 (Integrity, exhaustively proven: IC-1..6) · F6/F13 interop (IC-13/14) · R7 TDD (all) · R9 coverage 100% (A6) · R4/R11 config truth (IC-15) · R8 ≤150 (below) · doc-truth IH-22/23 (IC-16/17). PLAN-PHENOMENAL §1 items 12 (IC-1..6), 13 (IC-7..12), 14 (IC-13/14); §2 P8 acceptance = §4 here.
- **Tasks:** implemented under TODO §Phenomenal (T623+); closes leftover T430 → IC-15, T463 → IC-16, T465 → IC-17, T518 → IC-13/14.
- **New files & ≤150 raw+logical budgets:** `tests/integrity/mutations.py` ≤ 100 · `tests/integrity/test_tamper_sweep.py` ≤ 150 · `tests/properties/conftest.py` ≤ 40 · `tests/properties/test_prop_crypto.py` ≤ 120 · `tests/properties/test_prop_canonical.py` ≤ 90 · `tests/properties/test_prop_belief_board.py` ≤ 150 · `tests/properties/test_prop_fuzz.py` ≤ 120 · `tests/interop/test_golden_transcript.py` ≤ 130 · `scripts/make_golden_transcript.py` ≤ 110 · guard tests (3 files under `tests/shared/`) ≤ 120 each · `tests/interop/golden/transcript.json` = data fixture (exempt, like `docs/sample-run/*.json`).
