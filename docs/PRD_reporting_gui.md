# PRD_reporting_gui — Reporting, Gatekeeper, Orchestration, Live GUI & Replay (Stage 7)

| Field | Value |
|---|---|
| **Mechanism** | Reporting + Gmail Gatekeeper + Orchestration/Reliability + Live GUI + Replay Viewer |
| **Stage** | 7 (final stage — largest surface) |
| **Chapter** | Ch9 (reporting/gatekeeper/orchestration) + Ch7 (GUI/replay) |
| **Gates** | **F9** (orchestrator + legal-transition FSM + deadline/watchdog; silent peer → technical loss, no hang) · **F10** (Gatekeeper over Gmail: token-bucket + DOS + 429; OAuth `gmail.send` only) · **F11** (4 signed JSON auto-emailed; both sides send or 0; byte-identical mutual signature) · **F12** (Live GUI belief heatmap + Replay Verified OK/TAMPERED + README screenshots) |
| **FRs** | FR-G1..FR-G5, FR-H1..FR-H3 (+ NFR-3, NFR-4, NFR-5) |
| **Version** | 1.00 (single-source `shared/version.py`) |
| **Status** | Gate-2 per-mechanism draft — approve before code |

---

## 1. Purpose & scope

This is the **final integration stage**: it closes the game by producing the graded, verifiable, communicable evidence of a match and by making the whole turn loop robust against a hostile or silent peer. It covers five tightly-coupled concerns:

1. **Reporting (FR-G1/G2)** — build the **four signed JSON artifacts** per series/sub-game and their **symmetric mutual signature**, then auto-email them as attachments.
2. **Gmail Gatekeeper (FR-G3, NFR-3/4/5)** — route the send through the **single `ApiGatekeeper.execute()` façade** with token-bucket rate limiting, DOS guard, HTTP-429 handling, and queue-not-drop, using OAuth scope `gmail.send` only.
3. **Orchestration & reliability (FR-H1/H2/H3)** — the single **Orchestrator** gateway, the **legal-transition state machine**, the **Deadline Tracker**, and the **Watchdog**, so a silent opponent becomes a *technical loss* and never a hang.
4. **Live GUI (FR-G4)** — a Tkinter window showing the **belief heatmap** and turn banner from **local truth only** (never the objective board).
5. **Replay Viewer (FR-G5)** — re-hash each logged step → green **"Verified OK"** / red **"TAMPERED"**, with README screenshots.

**In scope:** `report/*`, `infra/email_sender.py`, `shared/gatekeeper.py`, `shared/rate_limiter.py`, `peer/orchestrator.py`, `peer/state_machine.py`, `peer/deadline.py`, `peer/watchdog.py`, `gui/*`.
**Out of scope (consumed, not built here):** the commit/reveal records and audit verdict (from `PRD_crypto` / `domain/crypto.py`), the brains (`PRD_strategy`), MCP transport (`PRD_mcp_infra`), and the `game.json`/`game.toml` config schemas (`FR-I`, all PRDs). This PRD only *reads* those outputs.

**Milestone (binary):** a full loopback match is **auto-emailed as 4 JSON attachments**; the **GUI shows the belief heatmap**; the **Replay Viewer reports "Verified OK"**.

---

## 2. Requirements

### Reporting artifacts
- **FR-G1** — Produce four signed JSON artifacts per series / sub-game: `declaration_<id>.json` (series-static), `config_<id>_g<NN>.json` (per sub-game, byte-identical shared config + `config_sha256`), `log_<id>_g<NN>.json` (per sub-game step log), `result_<id>.json` (series result). All carry the **shared `game_uid`** and a **distinct `game_id`** (from `domain/game_ids.py`). *(F11)*
- **FR-G1 (mutual signature)** — the log and result artifacts embed a `mutual_agreement` block whose signature hashes **only the symmetric outcome** (ADR-009), so both peers independently produce **byte-identical** signatures; peer-private fields are excluded from the signed structure. *(F11)*
- **FR-G2** — artifacts are **auto-emailed** to the configured recipient (`rmisegal+uoh26finalgame@gmail.com`) as **JSON attachments**; the plaintext body carries **no artifact data** (plaintext payload = 0). **Both sides send or neither is scored.** *(F11)*

### Gatekeeper
- **FR-G3 / NFR-3** — one `ApiGatekeeper.execute(callable, *, service, action)` façade routes **every** external call (Gmail, LLM, MCP, subprocess); wired, not decorative. *(F10)*
- **FR-G3 / NFR-4** — token-bucket parameters (30 req/min, 2 concurrent, 5 s backoff, 3 retries, queue 100) come from **config**, never code.
- **FR-G3 / NFR-5** — overflow **queues (FIFO) with backpressure**, never drops.
- **FR-G3** — DOS guard (reject a burst above capacity), HTTP-429 handling (backoff + retry + requeue), and OAuth scope **`gmail.send` only**. *(F10)*

### Orchestration & reliability
- **FR-H1** — a single **Orchestrator** gateway sequences each turn; `runtime.py` delegates to it.
- **FR-H2** — a **legal-transition state machine**; illegal transitions raise and route to `TECHNICAL_LOSS`.
- **FR-H3** — a **Deadline Tracker** (per-message expiry + retry, response timeout 30 s) and a **Watchdog** (heartbeat ~180 s / probe 60 s, controlled shutdown + state persistence). A silent opponent → **technical loss, never a hang**. *(F9)*

### GUI & Replay
- **FR-G4** — Tkinter Live GUI: belief **heatmap** + turn banner, rendering **local truth only** — never the objective board. *(F12)*
- **FR-G5** — Replay Viewer re-hashes each logged step and shows per-step + overall **"Verified OK"** (green) / **"TAMPERED"** (red); README screenshots of both GUI and Replay are mandatory. *(F12)*

---

## 3. Design

### 3.1 Four artifact schemas (top-level keys)

Built in `report/artifacts.py`; schema/version constants in `report/schemas.py`. IDs: `<id>` = peer/player id; `g<NN>` = zero-padded sub-game index. `game_uid` shared across both peers and all sub-games of a series; `game_id` distinct per peer.

**`declaration_<id>.json`** (series-static — one per peer per series):
```
schema, schema_version, game_uid, game_id, timezone ("Asia/Jerusalem"),
groups, players, roles, links, num_sub_games, max_tokens, generated_at
```

**`config_<id>_g<NN>.json`** (per sub-game — byte-identical shared constitution + lock):
```
schema, schema_version, game_uid, game_id, sub_game, config (the signed game.json body),
config_sha256, generated_at
```

**`log_<id>_g<NN>.json`** (per sub-game — the step log + audit outcome):
```
schema, schema_version, game_uid, game_id, sub_game, summary,
records[ { step, sender, payload, nonce, commit } ], mutual_agreement, generated_at
```

**`result_<id>.json`** (series result):
```
schema, schema_version, game_uid, game_id, sub_games[ { sub_game, outcome, scores } ],
final_result, mutual_agreement, generated_at
```

> `records[]` payload/nonce/commit come verbatim from `PRD_crypto` sealing bookkeeping; `summary`/`outcome`/`final_result` come from `peer/summary.py`; `config`/`config_sha256` from `shared/config.py`.

### 3.2 Mutual signature rule (`report/mutual_signature.py`, ADR-009)

Both peers must independently produce an **identical** signature, so it hashes **only the symmetric outcome** — never peer-private fields (own nonces-before-reveal, private belief, local timing, sender identity).

```
symmetric = { game_uid, sub_game, outcome, scores(sorted by role),
              final_result, audit_verdict, config_sha256 }
mutual_sig = SHA256( json.dumps(symmetric, sort_keys=True,
                     ensure_ascii=False, separators=(",",":")) )
mutual_agreement = { "signature": mutual_sig, "agreed": <bool from compare_digest>,
                     "signed_fields": [...ordered key list...] }
```
Reuses the same canonical-JSON discipline as the frozen commit formula (`PRD_crypto`). `agreed` is set by comparing the two peers' signatures with `secrets.compare_digest`; a mismatch means the outcomes disagree → downstream `TECHNICAL_LOSS`/`tamper_forfeit`.

### 3.3 Gatekeeper façade + token bucket (`shared/gatekeeper.py`, `shared/rate_limiter.py`, ADR-004)

One entry for every outward call:
```
ApiGatekeeper.execute(callable, *, service, action) -> result
```
It routes to HW6's typed methods (`google_send` / `run_subprocess` / `http_request`), records a ledger event `(service, action, ts, outcome)`, and enforces flow control before invoking `callable`.

**Token bucket** (`rate_limiter.py`, config-driven — `rate_limiter_gatekeeper` in `game.json`):
```
tokens <- min(capacity, tokens + rate * dt)        # refill by elapsed dt
allow  <- (tokens >= 1)                             # then tokens -= 1 on allow
```
with `rate = 30/60` req·s⁻¹, `capacity = 30`, `max_concurrent = 2` (semaphore), `backoff = 5 s`, `retries = 3`, `queue = 100` (FIFO, NFR-5). **DOS guard:** requests beyond `queue` capacity while empty-bucket raise `RateLimitExceeded` (reject the burst) rather than unbounded buffering. **429 handling:** on HTTP 429 (or transient error), sleep `backoff`, requeue, retry up to `retries`; exhausting retries surfaces a typed error to the caller (email emit treats this as "this side failed to send" → see §5). OAuth scope requested is **`gmail.send` only**.

### 3.4 Email sender reuse (`infra/email_sender.py`, FR-G2, ADR-006/D6)

Thin adapter over HW6's `GmailApiSender` (real `gmail.send` OAuth via `token.json`, `credentials.json` — both git-ignored, NFR-12). It builds a MIME message with the four JSON files as **attachments** and an empty/neutral body, then calls `ApiGatekeeper.execute(sender.send, service="gmail", action="send")`. The Google client is **injectable** so tests pass a fake backend (HW6 pattern, ADR-010) — no real send in CI. Recipient, sender, subject template all from `game.toml [email]`.

### 3.5 Orchestrator + state machine + deadline + watchdog (`peer/*`, FR-H)

- **`orchestrator.py`** — the single gateway (FR-H1). Per turn it asks the FSM to transition, calls the crypto/turn helpers, and hands failures to `TECHNICAL_LOSS`. Thin; delegates compute to brains and I/O to `turn_sender`/`turn_handler` through the gatekeeper.
- **`state_machine.py`** — enumerated states + a **legal-transition table**; `transition(to)` raises `IllegalTransition` if the edge is absent (routed to `TECHNICAL_LOSS`). **Legal transitions:**
  ```
  HANDSHAKE       -> WAITING
  WAITING         -> COMPUTING
  COMPUTING       -> COMMITTING
  COMMITTING      -> AWAITING_REVEAL
  AWAITING_REVEAL -> VERIFYING
  VERIFYING       -> WAITING          (next turn)
  VERIFYING       -> AUDIT            (game over)
  AUDIT           -> REPORTING        (audit passed)
  AUDIT           -> TECHNICAL_LOSS   (mismatch / false claim -> 0/0)
  WAITING         -> TECHNICAL_LOSS   (deadline / silent peer)
  <any non-terminal> -> TECHNICAL_LOSS (error)
  TECHNICAL_LOSS  -> REPORTING
  REPORTING       -> [terminal]
  ```
  Every path — win, loss, tamper, timeout — funnels through `REPORTING`, so artifacts are always emitted.
- **`deadline.py`** — Deadline Tracker: registers a per-message expiry (`response_timeout = 30 s` from config), triggers retry, and on final expiry signals the orchestrator to move `WAITING → TECHNICAL_LOSS`.
- **`watchdog.py`** — heartbeat monitor (`heartbeat ≈ 180 s`, probe `≈ 60 s` from config); on missed heartbeat performs a **controlled shutdown**: persist current state + records to disk (so a partial game can still report), then terminate the loop — never hang.

### 3.6 Live GUI heatmap — local truth only (`gui/*`, FR-G4)

Split to honor ≤150 lines/file (NFR-8):
- `window.py` — Tk root, layout, wiring (no logic beyond composition).
- `board_view.py` — draws the 7×7 grid + own pieces/barriers from **own_state**.
- `heatmap.py` — colors each cell by `BeliefGrid.as_matrix()` (the peer's *belief* of the opponent), plus turn banner. **It never renders the opponent's true position** (that data does not exist locally — F12/F7).
- `live_apply.py` — applies each committed/revealed step to the view model (subscribes to the orchestrator's step events).
- `live_controls.py` — start/pause/step buttons (call the SDK, hold zero business logic — R1).

### 3.7 Replay Viewer — re-hash verifier (`gui/replay*`, FR-G5)

- `replay_data.py` — loads a committed `log_<id>_g<NN>.json`, exposing its `records[]`.
- `replay.py` — for each record, recompute `CommitReveal.commit_of(payload, nonce)` and `compare_digest` vs the stored `commit`; render the step **green "Verified OK"** or **red "TAMPERED"**, and an overall verdict (all-green ⇒ "Verified OK"; any red ⇒ "TAMPERED").
- `replay_controls.py` — load-file / step / play-through controls.
Screenshots of both the Live GUI and a "Verified OK" Replay (plus a deliberately-tampered "TAMPERED" shot) are committed to `docs/sample-run/` and embedded in the README.

**File-size discipline:** report split into `schemas/artifacts/mutual_signature/emit`; GUI split into 8 modules; gatekeeper vs rate_limiter separated; orchestrator/state_machine/deadline/watchdog separated — each ≤150 lines raw+logical (NFR-8).

---

## 4. (folded into §3 per template)
*Design detail is fully specified in Section 3.*

---

## 5. Edge cases & error handling

| Case | Handling |
|---|---|
| **Only one side reports** (F11) | `mutual_agreement.agreed = false`; result records **both scored 0** — a match counts only if both peers emit. |
| **HTTP 429 / transient send error** | Gatekeeper sleeps `backoff` (5 s), requeues, retries ≤ 3; exhaustion → typed error → treated as "this side failed to send" (→ 0/0), never a crash or hang. |
| **Queue overflow / DOS burst** | Beyond `queue=100` → `RateLimitExceeded` (reject), never drop-silently and never unbounded memory (NFR-5). |
| **Deadline / silent opponent** (F9) | Deadline Tracker fires → FSM `WAITING → TECHNICAL_LOSS → REPORTING`; artifacts still emitted; process exits cleanly. |
| **Watchdog missed heartbeat** | Controlled shutdown: persist state + records to disk, then stop; a resumed/partial game can still produce a `result` (technical loss). |
| **Illegal FSM transition** | `IllegalTransition` raised → routed to `TECHNICAL_LOSS` (no undefined behavior). |
| **Tampered log** (F12) | Replay recomputes commits; any `compare_digest` mismatch → that step red "TAMPERED" + overall "TAMPERED". |
| **Mutual signature mismatch** | `agreed=false` → downstream `tamper_forfeit`/`TECHNICAL_LOSS` (0/0). |
| **GUI would need opponent truth** | Impossible by construction — GUI only reads local `own_state` + `BeliefGrid`; no objective board exists locally. |
| **Missing `token.json`/creds at emit** | Emit path in CI uses the fake backend; real send is a separate non-CI script — CI never depends on secrets. |

---

## 6. TDD test plan (Red-Green-Refactor; NFR-7, ≥85 % cov NFR-10)

**Reporting**
- Artifact **schema tests**: each builder emits exactly the specified top-level keys; `game_uid` shared + `game_id` distinct across the four; `config_sha256` matches the config bytes; `sub_game` zero-padding.
- **Mutual signature identical both sides**: build the symmetric structure from two peer views of the *same* outcome → assert byte-identical `mutual_sig`; assert peer-private fields excluded (perturbing a private field does not change the sig; perturbing an outcome field does).
- Emit: writes 4 files to disk, then calls the gatekeeper-wrapped sender exactly once with 4 attachments and empty body.

**Gatekeeper**
- **Token bucket**: refill formula (`tokens = min(cap, tokens+rate·dt)`), allow iff `tokens≥1`, decrement on allow; burst beyond capacity blocked.
- **429**: injected 429 → asserts backoff + retry + requeue, success after N; retries exhausted → typed error.
- **Queue-not-drop**: overflow up to 100 buffered FIFO; 101st → `RateLimitExceeded` (NFR-5).
- Single-façade test: every service path (`gmail`/`llm`/`mcp`/`subprocess`) goes through `execute()` and records a ledger event.

**Gmail** — mocked via an **injected fake `google` backend** (HW6 pattern, ADR-010); **no real send in CI**. A **separate non-CI script** (`scripts/send_sample_report.py`, excluded from pytest/CI) performs the one real `gmail.send` that produces the committed `docs/sample-run/` artifacts.

**Orchestration** — state-machine **legal-transition tests** (every edge in §3.5 accepted) and **illegal-transition tests** (absent edges raise `IllegalTransition` → `TECHNICAL_LOSS`); Deadline Tracker fires `TECHNICAL_LOSS` on timeout (fake clock); Watchdog persists state on missed heartbeat.

**GUI** — logic tested **headless** where possible: `heatmap` color-mapping from a `BeliefGrid` matrix (pure function), `replay` verifier returns per-step Verified/Tampered from crafted logs (one clean log ⇒ all green; one flipped `commit` ⇒ that step red). Tk widget construction guarded so import/logic tests run without a display.

---

## 7. Milestone & Definition of Done

**Milestone (binary):** run a full loopback (`FakeTransport`) cop-vs-thief match → (1) 4 JSON artifacts are built and handed to the gatekeeper-wrapped sender (fake backend in CI; real send via the non-CI script for the committed sample); (2) the **Live GUI** displays the belief heatmap + turn banner; (3) the **Replay Viewer** loads the committed log and reports **"Verified OK"** (and "TAMPERED" on a corrupted log).

**Definition of Done:**
- FR-G1..G5 + FR-H1..H3 implemented; F9/F10/F11/F12 demonstrably pass.
- Every external call routed through `ApiGatekeeper.execute()` (NFR-3); rate limits in config (NFR-4); queue-not-drop proven (NFR-5).
- All files ≤150 lines raw+logical (`check_file_lines.py`); `ruff` = 0; `pytest --cov` ≥85 % with LLM+MCP+Gmail mocked.
- `docs/sample-run/` holds the 4 real JSON + GUI + Replay(Verified OK) + Replay(TAMPERED) screenshots; README embeds them.

---

## 8. Traceability

| Gate / FR / NFR | Satisfied by (section) |
|---|---|
| **F9** | §3.5 orchestrator + FSM + deadline + watchdog; §5 timeout/watchdog rows |
| **F10** | §3.3 gatekeeper façade + token bucket + DOS + 429 + `gmail.send`-only |
| **F11** | §3.1 four artifacts; §3.2 mutual signature; §3.4 email attachments; §5 only-one-side → 0/0 |
| **F12** | §3.6 Live GUI heatmap (local truth); §3.7 Replay verifier + README screenshots |
| FR-G1 | §3.1, §3.2 |
| FR-G2 | §3.4 |
| FR-G3 | §3.3 |
| FR-G4 | §3.6 |
| FR-G5 | §3.7 |
| FR-H1 | §3.5 (orchestrator) |
| FR-H2 | §3.5 (state_machine + transition list) |
| FR-H3 | §3.5 (deadline + watchdog) |
| NFR-3 | §3.3 single `execute()` façade |
| NFR-4 | §3.3 config-driven bucket params |
| NFR-5 | §3.3 + §6 queue-not-drop tests |
| NFR-6/8/9/10 | §7 DoD |

---

## 9. Dependencies & open questions

**Depends on (consumed):**
- `PRD_crypto` — `records[]` (`payload/nonce/commit`), `CommitReveal.commit_of`, `audit_verdict`, `peer/summary.py` outcome/final_result. *(Replay re-hash and log records rely on the frozen commit formula.)*
- `PRD_mcp_infra` — MCP transport for turn/audit exchange; `FakeTransport` for loopback tests.
- `PRD_strategy` — `BeliefGrid.as_matrix()` for the heatmap.
- **All PRDs / FR-I** — `shared/config.py` supplies `game.json` body + `config_sha256` and `rate_limiter_gatekeeper` params, and `game.toml [email]`.
- **HW6 reuse (D6)** — `GmailApiSender` + real `gmail.send` OAuth (`token.json`), `ApiGatekeeper` typed methods, `check_file_lines.py`.

**Open questions:**
- **Q1** `game_id` vs `game_uid` derivation — confirm `domain/game_ids.py` gives a shared `game_uid` (agreed at handshake) and a per-peer `game_id`; owned by `PRD_mcp_infra`/`PRD_crypto`.
- **Q2** Exact `records[]` field spelling (`payload/nonce/commit` here) must match `PRD_crypto` sealing output byte-for-byte.
- **Q3** Watchdog "state persistence" file format — proposal: reuse the `log` artifact partial builder; confirm with `PRD_crypto` summary owner.
- **Q4** D7 submission-PDF `<NN>` still pending (not this mechanism; noted for README links).
