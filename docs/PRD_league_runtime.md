# PRD_league_runtime — Live League Runtime (Reference-Choreography Peer)

## 1. Header

| Field | Value |
|---|---|
| **Mechanism** | Live League Runtime — our peer plays a full live series against a foreign peer using the reference wire choreography |
| **Phase** | **P1** (PLAN-CHAMPIONSHIP §2.1 / §3) — the L1 blocker: "play at all" |
| **Gates** | **F1** (P2P FastMCP, live) · **F2** (two processes/config dirs) · **F5** (Step-0 sealed declaration exchanged in-band) · **F6** (NL hints on every turn) · **F9** (orchestrated turn loop + deadlines → technical win, never a hang) · **F14** (league play vs other teams) |
| **Supersedes** | **PRD_crypto §4.3 (FR-F2 per-turn Commit→Ack→Reveal)** and **PRD_mcp_infra §3.4/§3.5 (transport surface + wire dataclass fields)** — see §1.1 amendment |
| **Ground truth** | `reference-repo/src/police_thief/` v3.0.0 — every wire detail below was read from that source, not from summaries. Where our older PRDs disagree with the reference code, **the reference code wins**. |
| **Version** | 1.00 (single-source `shared/version.py`) |
| **Status** | Championship-gate draft — approve before implementation (tasks TODO §T406+) |
| **Milestone** | **Binary:** our peer completes a full 2-sub-game series against the ACTUAL reference peer on localhost; both sides' audits report verified; roles swap between sub-games. |

### 1.1 Explicit amendment — the per-turn commit→reveal design is replaced

PRD_crypto §4.3 (and the current `Orchestrator.play_move`) implement a **two-message turn**: send `TurnMessage{commit}` → then send a second `TurnMessage{commit, move, intent}` reveal. **This is wrong for interop and is hereby superseded:**

1. **One sealed `TurnMessage` per turn.** The mover seals `{payload, nonce, commit}` locally and sends a **single** wire message carrying only the `commit` hash (plus hint/smell/claims). There is **no per-turn reveal message and no ack step**.
2. **Nonce AND move AND intent stay hidden until the end-of-game audit.** The plaintext move is *never* on the wire mid-game — the opponent learns your move only through smell, hints, and claims. (Our old flow leaked the move in the clear every turn, destroying the Dec-POMDP premise *and* the crypto hiding property.)
3. **Extra keys crash the reference parser.** `police_thief.domain.protocol.TurnMessage.from_dict` does `cls(**data)` with **no unknown-key filtering** — our current `move`/`intent` wire fields would raise `TypeError` inside the reference peer. Our wire messages must carry **exactly** the reference key set (§2.4), nothing more.
4. **What is NOT amended:** the frozen commit formula (`SHA256(canonical_json(payload) + "|" + nonce)`, `nonce = secrets.token_hex(16)`), the `{payload, nonce, commit}` record triple, the golden vectors, and the mutual-audit iron rule (0/0 on tamper) all stand exactly as PRD_crypto §4.1/§4.2 froze them. Verified byte-identical against `reference-repo/.../domain/crypto.py`.
5. PRD_mcp_infra's `TurnMessage`/`ControlMessage`/`AuditPayload` field lists and `McpTransport` method surface are replaced by §2.4 and §3.7 below. Its 4 tool names, queue-not-drop model, gatekeeper routing, and config-dir separation stand.

---

## 2. The frozen interop choreography (verified wire protocol)

Everything in this section was verified line-by-line against `reference-repo/src/police_thief/{peer,domain,infra,sdk}`. It is the byte-level contract with EVERY opponent (the lecturer's peer and other teams built from it).

### 2.0 Transport substrate

- Each peer runs its **own FastMCP HTTP server** (`server.run(transport="http", host, port, show_banner=False)`), started **once per process** in a daemon thread, kept alive for the **whole series**. Fail fast if the port is taken (probe-bind before starting).
- The opponent URL **includes the `/mcp` path** (reference config: `http://127.0.0.1:8802/mcp`). Our `config/*/game.toml` `opponent_url` must gain the `/mcp` suffix.
- **Four tools**, exact names and — critical — exact **parameter names**:

| Tool | Parameter name | Enqueues to | Returns |
|---|---|---|---|
| `negotiate` | `message: dict` | agreements inbox | `{"ok": true}` |
| `receive_turn` | `message: dict` | turns inbox | `{"ok": true}` |
| `submit_audit` | **`payload: dict`** ← NOT `message` | audits inbox | `{"ok": true}` |
| `receive_control` | `message: dict` | controls inbox | `{"ok": true}` |

  The reference client sends `{"message": arg}` for three tools but **`{"payload": arg}` for `submit_audit`** (`infra/mcp_client.py::_call`). Our current server declares `submit_audit(message: dict)` and our client always sends `"message"` — **both directions break against the reference today.** Must fix both.
- Tools are enqueue-only (validate-shape → put → ack); the runtime drains its own inboxes. Outbound calls **retry with a deadline**: retry every `retry_interval_seconds` (1.0) until `connect_timeout_seconds` (60) because peers may start seconds apart; then raise (→ technical outcome, never a hang).

### 2.1 Step 1 — Negotiation handshake (per sub-game, not once per series)

Each peer, at the start of **every sub-game**, calls the opponent's `negotiate` tool with its signed agreement, then blocks on its **own agreements inbox** (timeout `connect_timeout_seconds`):

```json
{
  "terms":     { ...exact key set below... },
  "nonce":     "<secrets.token_hex(16)>",
  "signature": "<CommitReveal.commit_of(terms, nonce)>",
  "identity":  { "group_id": "...", "group_name": "...", "members": [...],
                 "repos": {...}, "mcp_servers": {...}, "llm_model": "...",
                 "spec": { ...host hardware/OS from sysinfo... } }
}
```

- `signature` uses the **same frozen commit formula** as turns (canonical JSON of `terms`, `|`, nonce, SHA-256 hex).
- Verification (reference `Negotiation.verify_peer`): **`message["terms"] != my_terms` → refuse** (Python dict equality over the JSON-round-tripped dicts), then re-verify the signature (raises on mismatch). `identity` is exchanged but **NOT signed and NOT compared** — it differs per group; it feeds the declaration artifact (F5).
- **`terms` exact key set** (reference `sealing.terms_from_config` — this dict must be value-equal on both sides or no game starts):

| Key | Sourced from (our `game.json`) | Reference value |
|---|---|---|
| `board_size` | `board_and_agents.board_size` | 7 |
| `smell_grid_size` | `pheromones.grid_size` | 5 |
| `decay_per_step` | `pheromones.decay` | 0.1 |
| `emit_intensity` | `pheromones.center_intensity` | 0.9 |
| `min_center_intensity` | `pheromones.min_center_intensity` | (agree pre-match) |
| `max_steps` | `movement_and_barriers.survival_threshold` | 35 |
| `barriers_max` | `movement_and_barriers.max_barriers` | 14 |
| `setting` | `world.map_area` | e.g. "New York" |
| `hint_max_words` | `world.hint_max_words` | 15 |
| `axis_origin_corner` | `board_and_agents.axis_origin_corner` | "top-left" |
| `axis_start_index` | `board_and_agents.axis_start_index` | 0 |
| `thief_start` | `board_and_agents.thief_start` | [3, 3] |
| `cop_start` | `board_and_agents.cop_start` | [0, 0] |
| `num_games` | `network_and_league.num_games` | series length |

  ⚠ Value-alignment traps found: our `game.json` has `hint_max_words: 30` (reference 15), `min_center_intensity: 0.001` (reference 0.5), `axis_origin_corner: "top_left"` (reference `"top-left"`, hyphen). Terms come from the **agreed** `game.json`, so pre-match agreement fixes values — but our translate layer must emit the reference **key names and formats** exactly.
- After both verifications, both peers **derive identical game ids without another round-trip** (reference `game_ids.derive_game_ids`):
  - `game_id = f"{min(gidA,gidB)}-vs-{max(gidA,gidB)}"`
  - `game_uid = str(uuid.UUID(bytes=sha256(canonical(terms) + "|" + gidA_sorted + "|" + gidB_sorted).digest()[:16]))`
- The game clock starts at agreement.

### 2.2 Step 2 — Step-0 sealed declaration (F5)

Before turn 1, each peer appends to its **own record book** (not sent yet — it travels inside the audit payload):

```
records[0] = {"payload": {"step": 0, "type": "system_spec", "spec": {...},
                          "model": "<llm model or 'cli-default'>",
                          "code_version": "<version>", "group_name": "<name>",
                          "sub_game_number": <n>},
              "nonce": "...", "commit": "..."}   # sealed with the frozen formula
```

### 2.3 Step 3 — Turn loop: **thief moves first**, strict alternation, ONE message per turn

- After negotiation the **thief takes the first turn unconditionally**; the police starts by polling. Receiving a `TurnMessage` IS the turn token: it makes you the mover. There is no other synchronization.
- A turn = compute → apply move to own state → **seal** `{payload, nonce, commit}` into the local book → deposit+decay own scent → **send one `TurnMessage`** → go back to polling.
- If the brain's chosen move is illegal, apply `HOLD` — **never stall the loop** (reference `turn_sender.take_turn`).

### 2.4 `TurnMessage` — exact wire key set (all keys always present; `asdict` serialization)

```
step: int                      # mover's own step counter after applying the move
sender: str                    # "thief" | "police"
hint: str                      # free NL text ≤ hint_max_words; MAY lie (F6)
smell_grid: dict               # {"r,c": float} MY OWN decayed trail; never a position
commit: str                    # SHA256(canonical(payload)|nonce); nonce+move withheld
timestamp: str                 # ISO-8601 UTC (mandatory per move)
barrier_placed: list | null    # [r,c] this turn's newly placed barrier (public, truthful)
capture_claim: list | null     # police only, on MOVE turns: my new cell = "you are HERE"
claim_response: dict | null    # honest answer to the peer's last capture_claim:
                               #   {"claim": [r,c], "caught": bool}
win_claim: dict | null         # thief only: {"type": "survival"} at max_steps
```

Claim mechanics (verified in `turn_sender.take_turn` / `turn_handler.process`):
1. **Police**: every `MOVE` turn attaches `capture_claim = list(my_new_position)` ("I claim you are at my cell"). `BARRIER`/`HOLD` turns send `capture_claim: null`.
2. **Thief**: on receiving a `capture_claim`, computes the honest answer `caught = (my_position == tuple(claim))` and attaches `claim_response = {"claim": [...], "caught": ...}` to its **next outgoing** message. Lying is pointless — the audit reveals the sealed true position.
3. If `caught` is true the thief sends a mandatory **final message**: `HOLD`, `hint = "You got me."`, the honest `claim_response` — then ends with result `("capture", "police")`. The police ends when it receives `claim_response.caught == true`.
4. **Thief survival**: after applying its move, if `step_number >= max_steps` the thief attaches `win_claim = {"type": "survival"}` to that same message and ends with `("survival", "thief")`. The police ends on receiving any `win_claim`.
5. On every incoming message the receiver also: notes `barrier_placed` into its own board, diffuses belief, observes/absorbs `smell_grid`, records the hint.

### 2.5 Step 4 — End-of-game audit exchange

When a peer holds a **real** result (not `timeout`/`stopped` — those skip the audit entirely, `summary.NO_AUDIT_RESULTS`):

1. Build `AuditPayload{sender, records, result_claim}` — `records` = the full local book **including the step-0 spec record**, each `{"payload": dict, "nonce": str, "commit": str}`.
2. **Best-effort send** to the opponent's `submit_audit` (param name `payload`!, timeout `audit_send_timeout_seconds` = 10, errors suppressed — the winner's process may already be exiting), then **block on own audits inbox** up to `connect_timeout_seconds`; `None` if nothing arrives → audit marked skipped.
3. Run `audit_records(theirs.records)` — **hash-only** re-verification of every `{payload, nonce, commit}` triple. **The reference auditor makes NO assumption about payload keys** except `payload.get("step", -1)` for failure reporting: it re-hashes the payload dict verbatim. So the commit **payload key-set does NOT need to match the opponent's** — each side seals its own schema; ours stays `commit_payload_spec` from our `game.json`. Our auditor must be equally lenient: re-hash verbatim, never validate foreign payload internals.
4. Any failed step → **`tamper_forfeit`**: the honest peer takes the win regardless of the board result (iron rule, PRD_crypto §4.4). Our extra **physical audit** (barrier/capture cross-check) remains a *local evidence layer* recorded in our artifacts; the interop verdict against foreign peers is the hash audit, so both sides' verdicts stay symmetric.

### 2.6 Step 5 — Series and role swap

- The transport + MCP server are built **once**; each sub-game gets a **fresh runtime** (fresh state/belief/smell/record book) and a **fresh negotiation** (§2.1).
- `num_games` sub-games; **role alternation**: a peer plays its config-natural role on **odd** sub-games and the opposite role on **even** ones — so when A is cop, B is always thief.
- Restart (control channel): drain all turn/control/audit inboxes on both sides, restart from sub-game 1; hard cap 10 restarts.

### 2.7 Control channel scope (out-of-band, optional, never sealed)

`ControlMessage{kind, sender, sub_game_number=1, status="", step_budget=0.0, payload=null}`; kinds `enable | status | restart | quit`. Active only when **both** peers sent `enable`. Status strings: `WAITING/THINKING/PLAYING/PAUSED/STOPPED/GAME_OVER/QUIT`. Sends are **best-effort** (2 s timeout, errors suppressed — advisory only); receive parsing filters unknown keys. `restart` is auto-approved when active and raises a series restart; `quit` ends the game as `("quit","-")` / `("opponent_quit", my_role)`. A transport without control methods degrades to no-op. **We implement: receive-and-tolerate everything; send `status` (on change only) and honor `quit`.** Pause/restart initiation stays GUI-optional — not required for league play.

### 2.8 Timeouts (from config, § robustness)

| Wait | Config key | Reference default | On expiry |
|---|---|---|---|
| Opponent's next turn | `network.turn_timeout_seconds` | 180 | result `("timeout", my_role)` = **my technical win**; skip audit |
| Inbox poll granularity | `network.poll_interval_seconds` | 0.5 | loop again (drain control between polls) |
| First contact / negotiate reply / audit reply | `network.connect_timeout_seconds` | 60 | raise → clean CLI error / audit `skipped` |
| Outbound retry cadence | `network.retry_interval_seconds` | 1.0 | keep retrying until deadline |
| Audit push | `network.audit_send_timeout_seconds` | 10 | suppress; still read own inbox |

The turn deadline **resets on every received message**.

---

## 3. New / rewritten modules (each ≤150 lines raw + logical, tests too)

| # | File | Status | Responsibility | Budget |
|---|---|---|---|---|
| 1 | `peer/runtime.py` | **NEW** | `PeerRuntime(role, config, brain, transport, listener, sub_game_number)` — one agent, one sub-game: negotiate → (thief) first turn → poll/process/respond loop → result → audit via `summary.finish`. Owns state/belief/smell/record-book; turn deadline + watchdog beat; maps phases onto our `StateMachine`. `run() -> summary dict`. | ≤150 |
| 2 | `peer/handshake.py` | **REWRITE** | `negotiate(rt)` — build terms+identity, `transport.exchange_agreement(signed)`, verify terms equality + signature, capture `peer_identity`, derive `game_id`/`game_uid`, start clock. Raises `HandshakeError` on mismatch (no game). | ≤80 |
| 3 | `domain/negotiation.py` | **REWRITE** | `Negotiation(terms, identity)` — `signed() -> {terms, nonce, signature, identity}`; `verify_peer(msg)` (terms dict-equality + `CommitReveal` signature check). Replaces `sign_agreement/verify_agreement`. | ≤80 |
| 4 | `peer/terms.py` | **NEW** | `terms_from_config(cfg)` (exact §2.1 key set from OUR `game.json` sections), `validate_terms(cfg)` fail-fast on missing required terms **before opening a port**, `identity_from_config(cfg)` (§2.1 identity keys incl. `spec`). | ≤110 |
| 5 | `domain/game_ids.py` | **REWRITE** | `derive_game_ids(terms, group_a, group_b) -> (game_id, game_uid)` — reference formula (§2.1). Old `game_uid/game_id` signatures kept only if reporting still needs them, else migrated. | ≤60 |
| 6 | `peer/turn_sender.py` | **REWRITE** | `take_turn(rt, claim_response)` — decide, apply (HOLD fallback), seal step record, scent deposit+decay, attach police `capture_claim` / thief `win_claim`, build+send the single `TurnMessage`; `send_final(rt, claim_response)` ("You got me."). | ≤120 |
| 7 | `peer/turn_handler.py` | **REWRITE** | `TurnHandler.process(msg) -> IncomingOutcome{i_won, i_am_caught, opponent_won, win_type, claim_response}` — barrier note, belief diffuse+observe, smell absorb+decay, claim logic (§2.4), history for GUI/replay. **Lenient**: accepts any foreign extras via our filtering `from_dict`. | ≤110 |
| 8 | `peer/sealing.py` | **EXTEND** | Keep `SealBook`; add `sealed_step_record(state, decision, step)` (our payload schema per `commit_payload_spec`), `sealed_spec_record(cfg, sub_game_number)` (§2.2), `build_turn_message(...)` (§2.4 exact key set), `now_iso()`. | ≤150 |
| 9 | `peer/summary.py` | **EXTEND** | `finish(rt)` — audit exchange (§2.5: best-effort send, read own inbox, hash-audit theirs, `tamper_forfeit` on fail, `skipped` on timeout results) + summary dict `{result, winner, steps, sub_game_number, started_at, duration_seconds, audit, records, history, role}` feeding the 4 artifacts. | ≤150 |
| 10 | `infra/inboxes.py` | **EXTEND** | Add `agreements` queue (`put_agreement/get_agreement`); add non-raising `try_get_*(timeout) -> dict \| None` poll semantics; `drain_all()` for restarts. Bounded FIFO stays (queue-not-drop). | ≤100 |
| 11 | `infra/mcp_server.py` | **AMEND** | Route `negotiate` → **agreements** inbox (today it lands in `control` — wrong); rename `submit_audit` parameter to **`payload`**; add `start_peer_server(role, host, port) -> Inboxes` (port-free probe, daemon thread, `show_banner=False`). | ≤120 |
| 12 | `infra/mcp_client.py` + `transport_base.py` | **AMEND** | Add retry-until-deadline `_call_with_retry`; `exchange_agreement(signed) -> dict`, `exchange_audit(payload) -> dict \| None` (best-effort push + own-inbox read), `drain_inboxes()`, best-effort `send_control`; `poll_turn/poll_control` return `None` on empty (no exception on the hot loop); `submit_audit` outbound arg key = `"payload"`. All outbound still gatekept (`service="mcp"`). | ≤150 each |
| 13 | `domain/protocol.py` | **AMEND** | `TurnMessage` drops `move`/`intent` **from the wire class entirely** (they exist only inside sealed payloads); field order/defaults per §2.4 (`hint`, `smell_grid`, `timestamp` always populated). `from_dict` stays **lenient** (filter to known keys — never crash on foreign extras) while `to_dict` emits exactly the reference key set. | ≤150 |
| 14 | `sdk/series.py` | **NEW** | `SeriesResult` dataclass; `role_for(natural, n)` (natural on odd); `run_series(cfg, natural_role, brain_factory, transport, listener) -> SeriesResult` — fresh `PeerRuntime` per sub-game, transport reused, restart loop with inbox drain + `MAX_RESTARTS`. | ≤110 |
| 15 | `sdk/sdk.py` | **EXTEND** | `SimulationSdk.run_peer(role, config_dir, *, transport=None, listener=None) -> dict` — validate terms → start server+transport once (or injected fake) → `run_series` → emit the 4 artifacts per sub-game + series result → gatekept email. `run_self_match` untouched (grader's offline proof). | ≤150 |
| 16 | `cli.py` | **AMEND** | New subcommand: `cipherchase peer --role {police,thief} --config <dir> [--out logs]` → `SimulationSdk.run_peer`; prints result JSON `{result, winner, steps, sub_game(s), audit}` to stdout (machine-parseable — the interop test reads it). No logic in the CLI. | ≤150 |
| 17 | `peer/orchestrator.py` | **REPLACED** | The commit→reveal `Orchestrator` is deleted; `PeerRuntime` is its replacement. `StateMachine` transitions amended: `HANDSHAKE→WAITING→COMPUTING→COMMITTING→WAITING` (one send per turn; `AWAITING_REVEAL`/`VERIFYING` states removed), `WAITING→AUDIT→REPORTING`, every active state →`TECHNICAL_LOSS`→`REPORTING`. | — |
| 18 | `tests/fakes/fake_transport.py` | **EXTEND** | Same surface as the new `McpTransport` (incl. `exchange_agreement/exchange_audit/drain_inboxes`, None-returning polls) wired as an in-memory queue pair. | ≤150 |

Config additions (`config/*/game.toml [network]`): `opponent_url` gains `/mcp`; new keys `turn_timeout_seconds`, `poll_interval_seconds`, `connect_timeout_seconds`, `retry_interval_seconds`, `audit_send_timeout_seconds` (all read — no dead keys, R11). `rpc_timeout_s` is retired or aliased.

## 4. Robustness-as-points (L3: harvest technical wins, never donate one)

| Threat | Policy |
|---|---|
| **Opponent silent past `turn_timeout_seconds`** | Result `("timeout", our_role)` — logged, artifacts emitted, audit skipped (reference-compatible). This is **our technical win**; the runtime exits 0. |
| **Malformed inbound turn** (unparseable, missing required keys, wrong types) | Reject at the parse boundary: log evidence into `history`, do **not** apply, do **not** crash. The message does not reset our deadline; a peer that only sends garbage times out → our technical win. A tool-level malformed dict returns `{"ok": false, "error": "malformed"}` without enqueueing. |
| **Foreign extra fields** | **Lenient parser** (filter-to-known-keys `from_dict`) — a stricter-than-us opponent must never crash us. Symmetrically we send the exact reference key set so strict parsers never crash on us. |
| **Unreachable opponent at start** | Retry loop to `connect_timeout_seconds`, then clean `HandshakeError` → non-zero exit with a human message (no traceback, no hang). |
| **Watchdog (F9)** | `Watchdog(turn_timeout)` beats on every received message; the poll loop checks `expired()` each `poll_interval` — belt-and-braces with the deadline arithmetic; expiry funnels to `TECHNICAL_LOSS → REPORTING` in the FSM, which still writes artifacts. |
| **Crash on our side** | Any unhandled exception in the loop is caught at the runtime boundary, recorded as `("error", "-")`, artifacts still emitted — we never leave a hung server holding a port. |
| **Between sub-games / restarts** | `drain_inboxes()` before every fresh negotiation so a stale turn from an aborted sub-game can never be consumed as live (reference `series` behaviour). Port stays bound; runtime state is rebuilt from scratch. |
| **Audit push races** | Best-effort push + always read own inbox (reference §2.5) — the winner exiting early never voids our audit. |

## 5. THE interop proof — playing the actual reference peer

`tests/interop/test_vs_reference.py` (marked `slow`; CI job step `interop`, skipped when `uv`/reference repo absent):

1. **Fixture configs** (built in `tmp_path` by the test): two config dirs for OUR peer (`police`/`thief`) and two for the reference peer, with **value-aligned shared terms** (one source dict rendered into our `game.json` schema AND the reference's `game.json` v1.3 schema — `grid_size` vs `board_size`, `pheromone_*` names, `top-left` hyphen), distinct ports (e.g. 8801/8802 from the fixture, never hardcoded in code), `opponent_url` with `/mcp`, `num_games = 2`, short `turn_timeout_seconds` (30), email disabled, reference `--stub-llm`.
2. **Launch**: reference peer via its own project — `uv run --project <abs>/reference-repo python -m police_thief peer --role police --no-gui --stub-llm --config <fixture>` — as a `subprocess.Popen`; our peer via `uv run cipherchase peer --role thief --config <fixture>`. Start order swapped in a second run (retry-until-connect makes order irrelevant — asserted).
3. **Guards**: overall `timeout=180 s` per series; on expiry kill both process groups and fail with both stdout/stderr attached.
4. **Assertions**:
   - both processes exit 0; a full **2-sub-game series** completes;
   - both stdout JSON summaries report `audit.passed == true` (**both sides' audits verified**);
   - roles swapped: sub-game 1 result roles ≠ sub-game 2 roles in our summaries;
   - **byte-identical agreement lock**: both sides print/derive the **same `game_uid`** (pure function of terms+group ids — equality proves the terms dicts matched byte-for-byte);
   - results are legal outcomes (`capture`/`survival`), no `timeout`, no `tamper_forfeit`.
5. **Both-role coverage**: parametrized `[our_role=thief, our_role=police]`.
6. **Golden-transcript fixtures**: a listener tap records every wire dict of one blessed run into `tests/interop/golden/transcript_*.json`; fast (non-`slow`) tests replay these against `TurnHandler`/`negotiate`/`audit` and assert: exact `TurnMessage` key set, `{terms,nonce,signature,identity}` shape, `submit_audit` `payload` param, and that the reference's strict `from_dict(cls(**data))` — imported via `sys.path` from `reference-repo/src` — parses **every message we emit** without error. That last test is the cheap every-commit interop tripwire.

This is the rehearsal for real matches: no other team can show a green vs-the-lecturer's-code series.

## 6. Opponent kit — `docs/INTEROP-CONTRACT.md` (one page, handed to teams before matches)

Contents (spec — the file is a deliverable of this PRD): (1) the 4 tool names + parameter names (incl. the `payload` quirk) + URL form `http://<host>:<port>/mcp`; (2) the negotiate payload `{terms, nonce, signature, identity}` with the exact terms key table (§2.1) and a filled example; (3) the frozen commit formula reproduced verbatim + one golden vector; (4) the `TurnMessage` key set with types and claim semantics; (5) the audit exchange (`AuditPayload` shape, hash-only verification, iron rule); (6) a mermaid sequence diagram: negotiate ×2 → thief turn → alternating turns → claims → win/capture → mutual `submit_audit`; (7) timeout table (§2.8) and role-swap rule; (8) our tunnel checklist (ngrok URL exchange, port, who starts first — anyone). Style: zero prose padding, everything copy-pasteable.

## 7. TDD test plan (unit — all fast, FakeTransport, no sockets)

1. `test_negotiation_signed_shape` — `signed()` has exactly `{terms, nonce, signature, identity}`; signature verifies with the frozen formula.
2. `test_negotiate_rejects_terms_mismatch` — one differing term value → `HandshakeError`; identity differences do NOT reject.
3. `test_terms_exact_keyset_and_values` — `terms_from_config` over our `game.json` fixture yields exactly the §2.1 keys; golden dict compare.
4. `test_derive_game_ids_matches_reference` — golden vector computed from the reference formula; both orderings of group ids give identical output.
5. `test_thief_sends_first` / `test_police_waits_first` — FakeTransport pair: thief's first outbound happens before any poll; police's first action is a poll.
6. `test_turn_message_exact_wire_keys` — `to_dict()` keys == the 10 §2.4 keys, no `move`/`intent`/`nonce`; timestamp ISO-8601; hint non-empty.
7. `test_lenient_parse_foreign_extras` — a turn dict with 3 unknown keys parses fine; missing optional keys default; malformed required keys → rejected not crashed.
8. `test_capture_claim_only_on_police_move` — MOVE ⇒ claim = own cell; BARRIER/HOLD ⇒ null.
9. `test_claim_response_honest_and_next_message` — claim at thief's true cell ⇒ `caught: true` + final "You got me." message; wrong cell ⇒ `caught: false` attached to next turn.
10. `test_survival_win_claim_at_max_steps` — thief step == max_steps ⇒ `win_claim {"type":"survival"}` on that message; police ends on receipt.
11. `test_full_series_loopback` — two `PeerRuntime`s over FakeTransport play `num_games=2`; roles swap; both audits pass; game_uids equal.
12. `test_timeout_is_technical_win_and_skips_audit`; `test_deadline_resets_on_message`.
13. `test_audit_exchange_best_effort` — push raises → suppressed → own inbox still read; empty inbox → audit `skipped`, no crash.
14. `test_tampered_opponent_record_forfeits` — flip one payload byte ⇒ `tamper_forfeit`, we win.
15. `test_restart_drains_inboxes`; `test_submit_audit_uses_payload_param` (spy on the outbound arg dict key).
16. Edge cases: duplicate turn (same step twice) processed idempotently by step guard; empty smell_grid tolerated; `win_claim` with unknown type treated as opponent win with that type recorded; port-in-use → clean `SimulationError`-equivalent message.

Coverage ≥85% on all §3 modules; ruff 0; ≤150 checker green (tests included).

## 8. Milestone (binary)

> **Our peer completes a full 2-sub-game series against the reference peer on localhost; both sides' audits report verified; roles swap between sub-games.** — i.e. §5 item 4's assertions all green, both-role parametrization, plus the golden-transcript tripwire in the fast suite.

## 9. Traceability

| Gate / requirement | Where satisfied |
|---|---|
| **F1** live P2P, no central server | §2.0 own server per peer, §3 #11/#12, §5 two real processes |
| **F2** two processes / config dirs | §5 fixture dirs; per-process `Inboxes`; CLI `--config` |
| **F5** Step-0 sealed declaration | §2.2 spec record; identity exchange §2.1; audited in §2.5 |
| **F6** NL hints every turn (may lie) | §2.4 `hint` mandatory field; `hint_max_words` term |
| **F9** orchestrated loop + deadlines | §3 #1 runtime + FSM, §4 watchdog/timeout rows |
| **F14** league vs other teams | §6 opponent kit; §2 frozen choreography; §5 rehearsal |
| PLAN §2.1 single-sealed-turn amendment | §1.1, §2.3–2.4 |
| R3 gatekeeper on external calls | §3 #12 (all outbound gatekept) |
| R5 queue-not-drop | §3 #10 bounded FIFO retained |
| R8 ≤150 | §3 budget column |
| R11 zero hardcoding | §2.8 config table, §3 config additions |
| R7 TDD | §7; interop §5 |

## 10. Dependencies & risks

**Depends on:** frozen `CommitReveal` (PRD_crypto §4.1 — already byte-identical to the reference, verified); `Inboxes`/server builder (PRD_mcp_infra, amended §3); brains seam (PRD_strategy / PRD_winning_brain — `PeerRuntime` takes any brain with `decide(state, belief, …)`); artifacts emitters (PRD_reporting_gui) consume the §3 #9 summary shape; `shared/sysinfo` for identity `spec`.

**Feeds:** P3 league ops (ngrok = same choreography, different URL), PRD_integrity_hardening (declaration truthfulness), the 4-artifact reporting per real match.

**Risks:** (1) FastMCP version skew between our pin and reference `fastmcp>=3.4.3` — the interop test catches it; pin compatibly. (2) Reference peer's email/GUI side effects in the test — disabled via fixture config + `--no-gui`; if its EmailSender still attempts sends, fixture sets its enable flag off (verify at implementation, adjust fixture). (3) Terms value drift with real opponents — mitigated by §6 kit + pre-match `game.json` exchange; `validate_terms` fails fast. (4) Our physical-audit verdict diverging from a foreign hash-only verdict — policy fixed in §2.5.3/.4 (hash audit decides interop outcome; physical audit is evidence). (5) Reference `TurnMessage` strictness — the golden-transcript tripwire (§5.6) runs on every commit.
