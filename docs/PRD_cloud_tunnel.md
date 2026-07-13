# PRD — Cloud / Public-Tunnel Deployment (Stage 5)

| Field | Value |
|---|---|
| **Mechanism** | Cloud / public-tunnel deployment for real league play |
| **Stage** | 5 of 7 (built after `PRD_language_scent.md`, before `PRD_crypto.md`) |
| **Spec chapter** | Ch2 (P2P MCP infrastructure / deployment) |
| **Gate** | **F13** — cloud-deployable, public-tunnel design; localhost for tests |
| **FRs covered** | FR-E1, FR-E2 (+ NFR-11, NFR-3 cross-cut) |
| **Modules** | `infra/mcp_server.py`, `infra/mcp_client.py`, `config/game.toml [network]`, deployment docs, **ADR-005** |
| **Version** | 1.00 (single-source `shared/version.py`) |
| **Status** | Gate-2 draft (per-mechanism PRD; approve before code) |

---

## 1. Purpose & scope

Enable two peers on **different machines / networks** to play a real league game (F14) by exposing each peer's FastMCP server through a **public HTTPS tunnel** and pointing the opponent at the resulting URL. This is the *deployment surface* of the already-built P2P infrastructure (Stage 2) — it adds **no new game logic**. The peer binds its server to a configurable host/port, a tunnel maps that port to a public `https://…` URL, the two teams exchange URLs + the signed pre-game declaration **out-of-band**, and each sets `opponent_url` in `game.toml [network]`.

**In scope:** server bind wiring (host `0.0.0.0`, port from config), client `opponent_url` wiring, ngrok (primary) + Localtonet (fallback) design, NAT-traversal rationale, security model, deployment runbooks, league pre-match checklist, and **ADR-005**.

**Out of scope (owned elsewhere):** the 4 MCP tools and queues (Stage 2 / `PRD_mcp_infra.md`); commit-reveal, `game.json` signing, `config_sha256` (Stage 6 / `PRD_crypto.md`); watchdog/deadline technical-loss handling (Stage 7 / `PRD_reporting_gui.md`, cross-referenced here); Gmail reporting (Stage 7).

**Design-only stage.** The binary Milestone is validated **on localhost with `FakeTransport`**; the tunnel itself is a documented, manual, deploy-time step that CI never touches.

## 2. Requirements

### Functional

- **FR-E1 — Public-tunnel exposure (design + docs).** Document how a peer (a) starts its FastMCP server on `0.0.0.0:<my_port>` (host/port from `game.toml [network]`, never hardcoded — NFR-11), (b) launches a tunnel to obtain a public `https://` URL, (c) exchanges that URL + the Step-0 signed declaration with the opponent out-of-band, and (d) records the peer's URL in `opponent_url`. **ngrok is PRIMARY; Localtonet is the documented FALLBACK** (ADR-005). Includes NAT-traversal rationale, OAuth-gating notes where relevant, and a security model.
- **FR-E2 — No live network in tests.** Every automated test runs on **localhost with `FakeTransport`** (in-memory queue pair). **No test depends on a live peer, tunnel, or key** (grader constraint C2). The tunnel is a deploy-time-only concern.

### Non-functional

- **NFR-E-a (⊂ NFR-11).** Bind host, `my_port`, and `opponent_url` are **config-driven only**; no host/port/URL literal appears in code. Default `host = "127.0.0.1"` for local runs; league deployment overrides to `0.0.0.0`.
- **NFR-E-b (⊂ NFR-3).** Any outbound HTTP the client makes to `opponent_url` routes through `ApiGatekeeper.execute(..., service="mcp", action="...")`, identical to Stage 2 — the tunnel changes only the destination URL, not the call path.
- **NFR-E-c.** This stage adds **no branching logic** beyond reading config: the same `McpTransport` code drives a localhost URL and a tunnel URL. Correctness proven on localhost therefore holds over the tunnel.
- **NFR-E-d (⊂ NFR-8).** Any code touched stays ≤150 lines raw + logical; realistically this stage edits config + docs only.

## 3. Design

### 3.1 Server bind (`infra/mcp_server.py`)

`build_peer_server(role, inboxes)` already builds the FastMCP app with the 4 tools (Stage 2). Serving is parameterized:

```
host = cfg.network.host        # game.toml [network].host  (default "127.0.0.1")
port = cfg.network.my_port     # game.toml [network].my_port
mcp.run(transport="http", host=host, port=port)
```

For a league match the operator sets `host = "0.0.0.0"` so the server accepts connections forwarded by the tunnel agent (which connects from the loopback side). For all local runs and every test, `host` stays `127.0.0.1`. **No code change** distinguishes the two — only the config value differs.

### 3.2 Client wiring (`infra/mcp_client.py`)

`McpTransport` targets `cfg.network.opponent_url`. Locally this is `http://127.0.0.1:<opp_port>`; in a league match it is the opponent's `https://<sub>.ngrok-free.app` (or Localtonet) URL. The transport is URL-agnostic; every call still passes through the gatekeeper (NFR-E-b).

### 3.3 Tunnel launch — ngrok (primary)

The peer's process binds `0.0.0.0:my_port`. A separate `ngrok http <my_port>` process (started by the operator, **not** spawned by the app) opens an outbound connection to ngrok's edge and returns a public `https://<random>.ngrok-free.app` URL that forwards inbound HTTPS to `localhost:my_port`.

- **NAT traversal rationale:** neither team can rely on a public inbound IP (home routers / campus NAT / firewalls block inbound). ngrok makes an **outbound** connection from inside the NAT to a public relay, so no port-forwarding, no inbound firewall rule, and no static IP is needed. This is the standard reason a relay tunnel is used instead of raw `host:port` exposure.
- **TLS:** ngrok terminates TLS at its edge and forwards to the local plaintext HTTP server; peers therefore always exchange `https://` URLs even though the FastMCP server speaks plain HTTP locally.

### 3.4 Tunnel launch — Localtonet (fallback, ADR-005)

If ngrok is unavailable (account limits, blocked region, rate caps), Localtonet provides an equivalent outbound HTTP/TCP tunnel. The operator runs the Localtonet agent bound to the same `my_port`, obtains its public URL, and the opponent sets that as `opponent_url`. **Nothing in the code differs** — only the URL string. Documented as fallback so a single provider outage never blocks F14.

### 3.5 URL & declaration exchange (out-of-band)

There is **no matchmaker** (assumption A1). Before a match the two teams exchange, over any private channel (email/chat):
1. Each side's public tunnel URL.
2. Each side's **Step-0 signed declaration** (owned by `PRD_crypto.md` — OS/CPU/RAM/GPU, LLM model, team, player IDs, per-game GitHub commit hash).
3. The agreed **`config/game.json`** (byte-identical), whose `config_sha256` both sides must match (Stage 6).

Each side then writes the peer's URL into `opponent_url` and locks `game.json`. `peer/handshake.py` performs the URL + declaration + `game.json` lock at runtime (F5, F14); this PRD supplies only the transport/config layer it runs over.

### 3.6 Security model

- **Ephemeral tunnels.** ngrok/Localtonet free URLs rotate on every restart; they are single-match, disposable, and never committed.
- **No secrets in URLs.** The public URL carries no auth token, no credential, no player secret — only a hostname. Nonces stay hidden until end-of-game reveal (Stage 6) regardless of transport.
- **Integrity independent of transport trust.** The tunnel is treated as an **untrusted channel**. Correctness rides on Commit-Reveal + SHA-256 + the signed `game.json` / mutual audit (Stage 6), not on tunnel confidentiality — a tampering relay or a lying peer still yields `tamper_forfeit` 0/0 by mathematics. The signature on the game artifacts protects integrity even over a hostile tunnel.
- **OAuth-gated where relevant.** The tunnel exposes only the 4 game MCP tools. It never exposes Gmail: reporting uses the direct Gmail `gmail.send` OAuth path (Stage 7), which is not reachable through the peer's tunnel. If a control endpoint is exposed, it stays behind the same handshake/`game.json` lock; no unauthenticated control action is possible.

### 3.7 Localhost-vs-tunnel separation

| Concern | Local / test | League deploy |
|---|---|---|
| Transport | `FakeTransport` (in-memory) | `McpTransport` over HTTPS tunnel |
| `host` | `127.0.0.1` | `0.0.0.0` |
| `opponent_url` | `http://127.0.0.1:<port>` | `https://…ngrok-free.app` |
| Tunnel process | none | ngrok/Localtonet (manual) |
| Who runs it | CI + grader | operator, deploy-time |

The code path is identical across both columns; only `game.toml [network]` values and the presence of an external tunnel process change.

## 4. Config keys (`game.toml [network]`) — other PRDs must match

```toml
[network]
host         = "127.0.0.1"   # league override: "0.0.0.0"   (NFR-11)
my_port      = 8001          # this peer's FastMCP server port
opponent_url = "http://127.0.0.1:8002"  # league: opponent's https tunnel URL
# request_timeout_s, retries → consumed by deadline/watchdog (PRD_reporting_gui)
```

`config/police/game.toml` and `config/thief/game.toml` differ only in `my_port` / `opponent_url` (role-swapped). These keys are the **contract** `infra/mcp_server.py`, `infra/mcp_client.py`, and `peer/handshake.py` read.

## 5. Deployment runbook

### 5.1 ngrok (primary)

```bash
# (a) start the COP peer (binds 0.0.0.0:my_port from config)
uv run cipherchase --role police --config config/police
# (b) start the THIEF peer on the other machine
uv run cipherchase --role thief  --config config/thief
# (c) start the tunnel on EACH machine (separate terminal), pointing at that peer's my_port
ngrok http 8001                       # cop machine  -> https://<a>.ngrok-free.app
ngrok http 8002                       # thief machine-> https://<b>.ngrok-free.app
# (d) exchange URLs out-of-band, then set opponent_url in each game.toml [network]
#     cop:   opponent_url = "https://<b>.ngrok-free.app"
#     thief: opponent_url = "https://<a>.ngrok-free.app"
# (e) run one remote round: relaunch/point both peers; handshake locks game.json,
#     then automated play proceeds with ZERO manual moves.
```

### 5.2 Localtonet (fallback)

```bash
# (a)(b) start peers exactly as above
# (c) start the Localtonet agent bound to the same my_port on each machine
localtonet http 8001                  # -> https://<a>.localtonet.com
localtonet http 8002                  # -> https://<b>.localtonet.com
# (d)(e) identical to ngrok: paste the Localtonet URL into opponent_url, play.
```

Only the tool in step (c) and the resulting URL string change; peers and config keys are identical.

### 5.3 League pre-match checklist

1. Exchange public tunnel URLs (out-of-band).
2. Exchange + lock the agreed `config/game.json` (byte-identical).
3. **Verify `config_sha256` matches** on both sides (abort if not — Stage 6).
4. Exchange Step-0 signed declarations (per-game commit hash included).
5. Set `opponent_url` (+ `host = "0.0.0.0"`) in each `game.toml [network]`.
6. Start both peers; confirm handshake (`negotiate`) succeeds over the tunnel.
7. Hands off — automated Commit-Reveal play runs to completion; both sides auto-email the 4 JSON artifacts (Stage 7).

## 6. Edge cases & error handling

| Case | Handling |
|---|---|
| **Tunnel drops mid-game** | Peer sees no reply within the deadline → `peer/watchdog.py` / `deadline.py` declare a **technical loss (0/0)**, never a hang (FR-H3). This PRD does not implement that logic — it is owned by `PRD_reporting_gui.md`; here we only note the tunnel drop is *indistinguishable from a silent peer* and correctly funnels into the same `TECHNICAL_LOSS` state. |
| **URL rotation** (ngrok restart) | Public URL changes on every tunnel restart. Treated as a new match setup: re-exchange URLs, re-run the pre-match checklist. Never commit a URL. |
| **Firewall / NAT blocks inbound** | The reason for the outbound relay tunnel (§3.3); no port-forwarding needed. If the *outbound* tunnel port is blocked, fall back to Localtonet or a different network. |
| **Wrong `host`** (`127.0.0.1` in league) | Tunnel forwards to a server not listening on the tunnel's interface → connection refused; checklist step 5 sets `0.0.0.0`. |
| **`config_sha256` mismatch** | Handshake aborts before any move (Stage 6). No game is played over the tunnel with mismatched constitutions. |
| **Provider outage** (ngrok down) | Localtonet fallback runbook (§5.2); documented so a single-provider outage never blocks F14. |

## 7. TDD / verification plan

- **Localhost `FakeTransport` loopback proves the protocol.** A full cop-vs-thief match runs in one test process over the in-memory queue pair (per PLAN §9). Because the transport is URL-agnostic (NFR-E-c), a passing loopback match *is* the proof the same code plays over a tunnel — the tunnel only substitutes the `opponent_url` string.
- **Config-wiring tests.** Assert `mcp_server` reads `host`/`my_port` from config and `mcp_client` reads `opponent_url` from config — no literal host/port/URL in code (NFR-11). Assert default `host = "127.0.0.1"`.
- **Manual (non-CI) tunnel smoke test — documented, not automated.** A `docs/`-recorded procedure: run §5.1, confirm `negotiate` round-trips and one round completes over a real ngrok URL. Its output/screenshot is committed as offline proof; it is **never** part of `pytest` and never gates the grade (C2).
- **No live dependency in the suite.** No test imports ngrok/Localtonet, opens a socket to a public URL, or requires a key. Enforced by the FakeTransport-only rule and CI running with no network.

## 8. Milestone & Definition of Done

**Milestone (binary):** a remote peer connects and plays a **full round** — validated on **localhost** (FakeTransport loopback) with the ngrok/Localtonet path fully designed and captured in ADR-005 + this PRD's runbooks.

**Definition of Done:**
- [ ] `infra/mcp_server.py` binds `host`/`my_port` from `game.toml [network]`; default `127.0.0.1`.
- [ ] `infra/mcp_client.py` targets `opponent_url` from config; all calls via gatekeeper.
- [ ] No host/port/URL literal in code (NFR-11 verified by test + ruff).
- [ ] ngrok primary + Localtonet fallback runbooks + league pre-match checklist written.
- [ ] Security model (ephemeral, no-secrets-in-URL, integrity-over-untrusted-transport) documented.
- [ ] ADR-005 present in `PLAN.md` (already recorded) and referenced here.
- [ ] FakeTransport loopback match green; no test touches the network (C2).
- [ ] Manual tunnel smoke-test procedure documented (non-CI).
- [ ] ruff 0, ≤150 lines/file, CI green.

## 9. Traceability

| Requirement | Satisfied by (section) |
|---|---|
| **F13** (cloud-deployable / public tunnel; localhost for tests) | §3, §5, §7, ADR-005 |
| **FR-E1** (tunnel exposure design + docs, ngrok/Localtonet) | §3.3, §3.4, §3.5, §5.1, §5.2, §5.3 |
| **FR-E2** (all tests localhost + FakeTransport; no live dep) | §3.7, §7 |
| **NFR-11** (no hardcoded host/port/URL) | §3.1, §3.2, §4, §7 |
| **NFR-3** (every external call via gatekeeper) | §3.2, NFR-E-b |
| **NFR-8** (≤150 lines) | NFR-E-d, §8 |
| **ADR-005** (ngrok primary / Localtonet fallback; deploy-time only) | §3.3, §3.4, §7 |

## 10. Dependencies & open questions

**Depends on:**
- `PRD_mcp_infra.md` (Stage 2) — `build_peer_server`, the 4 tools, `McpTransport`, `FakeTransport`, gatekeeper routing. This stage only parameterizes their host/port/URL.
- `peer/handshake.py` — URL + declaration + `game.json` lock at runtime (F5, F14).

**Cross-references (owned elsewhere — must stay consistent):**
- **Watchdog / deadline → `PRD_reporting_gui.md`:** tunnel drop = silent peer → `TECHNICAL_LOSS` 0/0 (FR-H3). This PRD assumes that funnel exists; it must not be re-implemented here.
- **Declaration + `config_sha256` → `PRD_crypto.md`:** Step-0 signed declaration and `game.json` signing/verification. The pre-match checklist (§5.3) invokes them; the crypto PRD defines them.

**Open questions:**
- **OQ-1:** ngrok free-tier request/rate caps under a full 35-turn match — confirm during the manual smoke test; Localtonet fallback mitigates.
- **OQ-2:** Whether the control channel (`receive_control`) is exposed over the tunnel or kept localhost-only. Default: keep control localhost-only; expose only the 4 game tools. Confirm with `PRD_reporting_gui.md` (control-link owner).
