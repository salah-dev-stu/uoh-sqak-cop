# PRD_mcp_infra — Stage 2: P2P FastMCP Infrastructure

| Field | Value |
|---|---|
| **Mechanism** | P2P FastMCP infrastructure (two peer processes over localhost) |
| **Stage** | 2 of 7 (bottom-up build order) |
| **Chapter** | Ch2 (Networking / MCP transport) |
| **Gates** | **F1** (P2P FastMCP, no central server) · **F2** (two processes / two config dirs, NO shared memory — violation = **disqualification**) · supports **F7** (scent as intensity only, never opponent coordinates) |
| **FRs** | FR-B1, FR-B2, FR-B3, FR-B4, FR-B5 · NFR-3, NFR-5, NFR-8, NFR-11 |
| **Version** | 1.00 (single-sourced in `shared/version.py`) |
| **Status** | Gate-2 draft (per-mechanism) — approve with the docs package before code |
| **Milestone** | **Binary:** a message from peer A is received and interpreted by peer B over localhost. |

---

## 1. Purpose & scope

Stage 2 builds the **transport spine** that lets two mutually-distrustful peers — a Cop process and a Thief process — talk to each other with **no central server and no judge**. Each peer is *simultaneously a FastMCP server and an MCP client*. This PRD covers only the wire: how a message leaves peer A's client, arrives at peer B's four `@mcp.tool` endpoints, lands in a **thread-safe queue** (never processed inline), and is drained + interpreted by B's runtime.

**In scope:** the FastMCP server builder + 4 interop-named tools; the client transport (`McpTransport`); the on-the-wire dataclasses (`TurnMessage` / `ControlMessage` / `AuditPayload`); deterministic game-id derivation; the signed-`game.json` negotiation helper; the handshake glue; two separate config dirs; routing every external MCP call through the gatekeeper; and a `FakeTransport` for tests.

**Out of scope (owned by other PRDs):** the commit/reveal *content* of a turn (PRD_crypto — this stage only carries the `commit`/nonce fields opaquely), brain move selection (PRD_strategy), scent math (PRD_language_scent), the turn-loop state machine / watchdog (PRD_reporting_gui + peer runtime), and Gmail/JSON artifacts (PRD_reporting_gui). This stage delivers **plumbing**, not gameplay.

**Interop:** the 4 tool names, the dataclass field lists, and the `game_id`/`game_uid`/negotiation formulas defined here are a **byte-level contract shared with opponent teams**. Changing any is an API break.

## 2. Requirements

### Functional
- **FR-B1** — Each agent runs its **own FastMCP server**, started with `mcp.run(transport="http", host=<cfg>, port=<cfg>)`, host/port read from config (NFR-11). There is **no central server, matchmaker, or judge** (F1). Two peers = two independent servers that are each other's clients.
- **FR-B2** — The server exposes **exactly four** `@mcp.tool`s, interop-named precisely: **`negotiate`**, **`receive_turn`**, **`submit_audit`**, **`receive_control`**. Each has signature `(message: dict) -> dict`.
- **FR-B3** — An MCP **client** (`McpTransport`) calls the opponent's URL. Inbound messages on the server side are **enqueued into thread-safe queues and NOT processed inline** — the tool body validates shape, enqueues, and returns an immediate ack. The runtime later **drains** the queues on its own thread.
- **FR-B4** — **Two separate OS processes with two separate config dirs** (`config/police/` vs `config/thief/`) and **NO shared memory / no shared object** between Cop and Thief (F2 — violation = disqualification). The only channel between them is the MCP wire.
- **FR-B5** — On the wire, scent travels as an **intensity field only** (`"r,c" -> intensity`), **never opponent coordinates** (F7). No message field carries the *opponent's* true position.

### Non-functional
- **NFR-3 (R3)** — **Every external MCP call** (both `McpTransport` outbound calls and, symmetrically, any outbound send) is routed through the single `shared/gatekeeper.py` `ApiGatekeeper.execute(callable, *, service, action)` façade (ADR-004). No raw HTTP/MCP call bypasses it.
- **NFR-5 (R5)** — Inbound overflow is handled by a **bounded FIFO queue with backpressure — queue, not drop**. Enqueue blocks/backpressures rather than silently discarding.
- **NFR-8 (R8)** — Every module in this stage is **≤150 lines raw AND logical** (`check_file_lines.py`). The tool bodies are deliberately thin (validate → enqueue → ack) to fit.
- **NFR-11 (R11)** — Zero hardcoding: host, port, opponent URL, timeouts, queue caps all from config.
- **NFR-7 (R7)** — TDD, happy + error paths, transport mocked with `FakeTransport`.

## 3. Design

### 3.1 Module inventory (exact names from PLAN §3)

| File | Purpose | Approx budget |
|---|---|---|
| `infra/mcp_server.py` | `build_peer_server(role, inboxes) -> FastMCP` with the 4 tools bound to queues | ≤120 |
| `infra/mcp_client.py` | `McpTransport(opponent_url, inboxes)` — outbound calls + local drain helpers | ≤150 |
| `domain/protocol.py` | `TurnMessage` / `ControlMessage` / `AuditPayload` dataclasses + `to_dict`/`from_dict` | ≤150 |
| `domain/game_ids.py` | deterministic `game_id(...)` / `game_uid(...)` | ≤60 |
| `domain/negotiation.py` | build + sign + compare `game.json` agreement | ≤120 |
| `peer/handshake.py` | drive URL exchange → `negotiate` → `game.json` lock → declaration hook | ≤120 |
| `tests/fakes/fake_transport.py` | in-memory queue-pair transport (no HTTP/MCP) | ≤120 |

`domain/` stays **pure** (no I/O); `infra/` performs I/O and depends only on `domain` + `shared`.

### 3.2 The `Inboxes` queue model (FR-B3, NFR-5)

A small container of **four bounded `queue.Queue`s**, one per tool, created from config (`maxsize` from `network.queue_maxsize`, default e.g. 100). Passed by reference into both the server (producers) and the runtime/transport (consumers). This is the *only* object the server tools touch — they do **not** call game logic.

```
class Inboxes:                      # shared/queue container, thread-safe
    negotiate:  queue.Queue[dict]   # bounded FIFO (maxsize from config)
    turn:       queue.Queue[dict]
    audit:      queue.Queue[dict]
    control:    queue.Queue[dict]
    def put(self, box: str, msg: dict) -> None   # blocking put = backpressure, NOT drop
    def drain(self, box: str) -> list[dict]      # non-blocking get_nowait loop → FIFO order
```

> `Inboxes` is *per-process* state, not shared memory between peers (F2 safe): each of the two processes owns its own `Inboxes`.

### 3.3 The four MCP tools (exact interop signatures)

Bound inside `build_peer_server(role, inboxes)`; each validates the dict shape, enqueues, and returns an ack dict **without running game logic** (FR-B3):

```
@mcp.tool
def negotiate(message: dict) -> dict:       # game.json agreement exchange (handshake)
    inboxes.put("negotiate", message); return {"ok": True, "box": "negotiate"}

@mcp.tool
def receive_turn(message: dict) -> dict:     # a TurnMessage (commit or reveal payload)
    inboxes.put("turn", message);      return {"ok": True, "box": "turn"}

@mcp.tool
def submit_audit(message: dict) -> dict:      # an AuditPayload (records + ALL nonces at game end)
    inboxes.put("audit", message);     return {"ok": True, "box": "audit"}

@mcp.tool
def receive_control(message: dict) -> dict:   # a ControlMessage (enable/status/restart/quit)
    inboxes.put("control", message);   return {"ok": True, "box": "control"}
```

`build_peer_server` reads `host`/`port` from config and returns the configured `FastMCP` instance; `mcp.run(transport="http", host=host, port=port)` is called by the peer runtime (kept out of the builder so it stays unit-testable).

### 3.4 `McpTransport` (client) method list (`infra/mcp_client.py`)

`McpTransport(opponent_url: str, inboxes: Inboxes)` — every outbound method wraps its MCP call in `ApiGatekeeper.execute(..., service="mcp", action=<tool>)`:

| Method | Direction | Purpose |
|---|---|---|
| `exchange_agreement(payload: dict) -> dict` | out → opponent `negotiate` | send our signed `game.json` / agreement, get theirs back |
| `send_turn(message: dict) -> dict` | out → opponent `receive_turn` | push a `TurnMessage` (commit, then reveal) |
| `poll_turn(timeout: float \| None = None) -> dict \| None` | in ← local | pop next turn from our `inboxes.turn` (FIFO) |
| `send_control(message: dict) -> dict` | out → opponent `receive_control` | push a `ControlMessage` |
| `poll_control(timeout=None) -> dict \| None` | in ← local | pop next control from `inboxes.control` |
| `drain_inboxes() -> dict[str, list[dict]]` | in ← local | non-blocking drain of all four boxes (FIFO) for the runtime loop |
| `exchange_audit(payload: dict) -> dict` | out → opponent `submit_audit` | send our `AuditPayload`, receive theirs |

**Design note:** `send_*` / `exchange_*` are outbound (gatekept HTTP to `opponent_url`); `poll_*` / `drain_inboxes` are inbound reads of *our own* queues that the server populated — no network, so no gatekeeper needed. Timeouts come from config (`network.rpc_timeout_s`); `None` = non-blocking.

### 3.5 Wire dataclasses (`domain/protocol.py`) — exact field lists

All three are `@dataclass` with `to_dict()` and `from_dict(cls, d)` (`from_dict` ignores unknown keys and fills declared defaults, for forward-compat with opponents).

**`TurnMessage`**
```
step: int                       # turn index
sender: str                     # "police" | "thief"
hint: str                       # free natural-language text — MAY bluff
smell_grid: dict[str, float]    # "r,c" -> intensity  (INTENSITY ONLY, never coords of opponent — FR-B5/F7)
commit: str                     # SHA-256 hex from PRD_crypto (opaque here)
timestamp: str                  # ISO-8601
barrier_placed: str | None      # "r,c" or None (cop only; truthful physical fact)
capture_claim: bool             # sender claims a capture this turn
claim_response: str | None      # "accept" | "reject" | None (reply to peer's claim)
win_claim: bool                 # sender claims game-ending win
```

**`ControlMessage`**
```
kind: str                       # "enable" | "status" | "restart" | "quit"
sender: str                     # "police" | "thief"
sub_game_number: int            # which sub-game in the series
status: str                     # free status string
step_budget: int                # remaining/agreed step budget
payload: dict                   # kind-specific extra data
```

**`AuditPayload`**
```
sender: str                                 # "police" | "thief"
records: list[dict]                         # each: {"payload": dict, "nonce": str, "commit": str}
result_claim: str                           # sender's claimed outcome (verified against re-hash by PRD_crypto)
```

> `records[*].nonce` and `commit` are produced by PRD_crypto; this stage transports them verbatim. `payload` inside a record is the canonical `{State,Move,Intent,Nonce}` dict.

### 3.6 `domain/game_ids.py` (deterministic)

- `game_uid(agreed_between, config_sha256, series_seed) -> str` — one id **shared** by both peers for the whole series (deterministic hash of the sorted agreed party ids + `config_sha256` + seed).
- `game_id(game_uid, sub_game_number) -> str` — **distinct** per sub-game (`game_uid` + index). Both are pure/deterministic so peers derive identical ids without a coordinator.

### 3.7 `domain/negotiation.py`

- `build_agreement(game_json: dict, my_party: str) -> dict` — assemble the shared constitution + `agreed_between`.
- `sign_agreement(game_json: dict) -> str` — `config_sha256` over canonical JSON (same canonical-JSON rule as PRD_crypto: `sort_keys=True, ensure_ascii=False, separators=(",",":")`).
- `compare_agreements(mine: dict, theirs: dict) -> bool` — **byte-identical** check of the signed `game.json`; mismatch → refuse to start (handshake fails, no game). Uses `secrets.compare_digest` on the two signatures.

### 3.8 `peer/handshake.py`

`run_handshake(transport, config, my_party) -> Agreement` orchestrates: build local agreement → `transport.exchange_agreement()` → `compare_agreements()` → on match, derive `game_uid`/`game_id` and return a locked `Agreement`; on mismatch raise `HandshakeError` (→ technical loss, never a hang). Declaration signing (Step-0) is a hook consumed by PRD_crypto.

### 3.9 Config-dir separation (F2)

Two dirs, selected by `--role`, each a full private set:
```
config/police/game.toml   config/police/game.json   config/police/.env
config/thief/game.toml    config/thief/game.json    config/thief/.env
```
`game.json` is byte-identical across the two (signed shared constitution); `game.toml` differs (own host/port, opponent URL, role, brain class). **No module holds a reference reachable from both peers** — the two processes only ever meet on the MCP wire. A test asserts the two `Inboxes` instances are distinct objects.

## 4. Edge cases & error handling

| Case | Handling |
|---|---|
| **Malformed message** (missing/extra keys, wrong types) | Tool validates minimal shape; on failure returns `{"ok": False, "error": "malformed"}` and does **not** enqueue. `from_dict` tolerates unknown keys but rejects missing required fields → caller sees error, never a crash. |
| **Queue overflow** (NFR-5) | Bounded FIFO `Inboxes.put` uses **blocking put with backpressure** (or `put` with a config timeout then `QueueFullError` surfaced to the caller) — **never silently dropped**. Test drives cap+1 messages and asserts FIFO order preserved and nothing lost. |
| **RPC timeout / silent peer** | `send_*`/`exchange_*` raise `TransportTimeout` after `network.rpc_timeout_s`; the runtime maps this to a **technical loss, never a hang** (FR-H3, PRD_reporting_gui). `poll_*` with `timeout=None` returns `None` immediately (non-blocking). |
| **Opponent URL unreachable** | Gatekeeper `execute` surfaces the connection error as `TransportError`; handshake fails cleanly. |
| **Agreement mismatch** | `compare_agreements` false → `HandshakeError`, no game starts (protects interop + F5/F14). |
| **Scent leak guard (F7)** | `TurnMessage.to_dict` only serializes `smell_grid` intensities; a test asserts no opponent-coordinate field is ever present on the wire. |
| **Duplicate / out-of-order turn** | `step` field lets the consumer detect; queue preserves FIFO arrival order; dedup by `step` is the runtime's concern (noted for PRD_reporting_gui). |

## 5. TDD test plan

**`FakeTransport`** (`tests/fakes/fake_transport.py`) — an **in-memory queue-pair** implementing the same method surface as `McpTransport` (`exchange_agreement/send_turn/poll_turn/send_control/poll_control/drain_inboxes/exchange_audit`). Two `FakeTransport`s share a wiring where A's `send_turn` puts directly into B's `inboxes.turn` (and vice-versa) — **no real HTTP/MCP, no FastMCP server** needed for unit tests.

Happy path:
- `test_build_peer_server_has_exactly_four_tools` — names are exactly `negotiate/receive_turn/submit_audit/receive_control`.
- `test_tool_enqueues_not_inline` — calling `receive_turn(msg)` puts into `inboxes.turn` and returns ack **without** invoking any game logic (patched brain asserted un-called).
- `test_turnmessage_roundtrip` / `test_control_roundtrip` / `test_audit_roundtrip` — `to_dict → from_dict` identity for all three dataclasses; unknown keys ignored.
- `test_game_ids_deterministic` — both "peers" derive identical `game_uid`/`game_id` from the same inputs.
- `test_negotiation_byte_identical_match` — matching `game.json` → `compare_agreements` True.
- **`test_loopback_A_to_B_over_fake_transport`** (the Milestone test) — A builds a `TurnMessage`, calls `send_turn`; B `poll_turn()` returns the byte-equal message and `from_dict` reconstructs it → **received + interpreted by B**.

Error path:
- `test_malformed_message_not_enqueued` — bad dict → `{"ok": False}`, queue empty.
- `test_queue_overflow_is_fifo_not_drop` — push `maxsize+1`; assert backpressure and FIFO preservation, zero loss (NFR-5).
- `test_rpc_timeout_maps_to_transport_timeout` — fake raises after timeout → `TransportTimeout`.
- `test_agreement_mismatch_raises_handshake_error`.
- `test_no_opponent_coords_on_wire` — serialized `TurnMessage` has only `smell_grid` intensities (F7).
- `test_every_outbound_call_routes_through_gatekeeper` — spy asserts each `send_*`/`exchange_*` went through `ApiGatekeeper.execute` with `service="mcp"` (NFR-3).

Coverage target contribution ≥85% for these modules; all with mocked/fake transport (no live peer, per C2/ADR-010).

## 6. Milestone & Definition of Done

**Milestone (binary):** a message from peer A is received and interpreted by peer B over localhost — demonstrated by `test_loopback_A_to_B_over_fake_transport` (unit) **and** a manual two-process localhost smoke run where A's `send_turn` lands in B's queue and B reconstructs the `TurnMessage`.

**DoNE checklist:**
- [ ] 4 tools present, exactly named, each `(message: dict) -> dict`, thin (enqueue-only).
- [ ] `McpTransport` exposes all 7 listed methods; all outbound calls gatekept (`service="mcp"`).
- [ ] `TurnMessage`/`ControlMessage`/`AuditPayload` with the exact field lists + `to_dict`/`from_dict`.
- [ ] Two config dirs, distinct `Inboxes` per process, F2 no-shared-memory test green.
- [ ] Bounded FIFO queues, overflow = backpressure not drop (NFR-5 test green).
- [ ] `game_ids` + `negotiation` deterministic and byte-identical-verified.
- [ ] `ruff check` = 0; `check_file_lines.py` ≤150 raw+logical on all files incl. tests; `pytest --cov` ≥85% for the stage.
- [ ] CI (Py-3.13) green.

## 7. Traceability

| Gate / FR / NFR | Where satisfied |
|---|---|
| **F1** (P2P, no central server) | §3.3 own FastMCP per peer, §2 FR-B1 |
| **F2** (two processes/config dirs, no shared memory) | §3.9, §3.2 (per-process `Inboxes`), F2 distinct-object test §5 |
| **F7** (scent intensity only) | §3.5 `smell_grid`, §4 leak guard, `test_no_opponent_coords_on_wire` |
| FR-B1 | §3.3, §2 |
| FR-B2 | §3.3 (exact 4 tool names/signatures) |
| FR-B3 | §3.2 queue model, §3.3 enqueue-not-inline, `test_tool_enqueues_not_inline` |
| FR-B4 | §3.9 config dirs + no shared memory |
| FR-B5 | §3.5 `smell_grid`, §4, §5 leak test |
| NFR-3 (R3) | §3.4 gatekeeper routing, `test_every_outbound_call_routes_through_gatekeeper` |
| NFR-5 (R5) | §3.2 / §4 bounded FIFO, `test_queue_overflow_is_fifo_not_drop` |
| NFR-8 (R8) | §3.1 per-file ≤150 budgets |
| NFR-11 (R11) | host/port/url/timeouts/caps from config throughout |
| NFR-7 (R7) | §5 TDD happy + error, FakeTransport |

## 8. Dependencies & open questions for other PRDs

**Provides to others:**
- The **4 tool names + `(message: dict) -> dict`** signature — a frozen interop contract every opponent and every downstream PRD must match.
- The **three wire dataclasses** and their field lists — the envelope for all gameplay.
- `game_uid`/`game_id` derivation + `config_sha256` signing — reused by reporting.

**Depends on:**
- **`shared/gatekeeper.py`** `ApiGatekeeper.execute(callable, *, service, action)` (ADR-004) — must exist for NFR-3 wiring. If not yet built when this stage starts, stub with the same signature.
- **`shared/config.py`** `ConfigManager` for host/port/opponent-url/timeouts/queue-maxsize.

**Contracts other PRDs MUST match:**
- **PRD_crypto:** the `commit` string on `TurnMessage` and the `{payload, nonce, commit}` record shape in `AuditPayload` are **opaque passthroughs** here — crypto owns their contents. Canonical-JSON rule (`sort_keys=True, ensure_ascii=False, separators=(",",":")`) is **shared** between `negotiation.sign_agreement` (`config_sha256`) and crypto's commit formula — keep them identical.
- **PRD_reporting_gui:** consumes `game_uid` (shared) + `game_id` (distinct per sub-game) for the 4 artifacts; `AuditPayload.result_claim` feeds the mutual-audit → result. The runtime/state-machine (not this stage) maps `TransportTimeout` → technical loss.
- **PRD_language_scent:** owns `smell_grid` *values*; this stage guarantees the wire carries **intensity only**, never opponent coordinates (F7).

**Open questions:**
1. Exact FastMCP HTTP client call shape for `McpTransport` outbound (tool-call over `transport="http"`) — confirm against the pinned FastMCP version before coding; wrap behind `execute` regardless.
2. Whether `sub_game_number` on `ControlMessage` and `game_id` derivation index must align 1:1 — reconcile with PRD_reporting_gui's `config_<id>_g<NN>.json` `<NN>`.
