# Deploy & Tunnel Runbook (Stage 5 · F13)

> Public-tunnel deployment for real league play. **Design + docs only** — no test
> ever touches a socket, tunnel, or key; the whole suite runs on `FakeTransport`
> loopback (C2, ADR-010). Primary tunnel: **ngrok**; fallback: **Localtonet**
> (ADR-005). Every host/port/URL is read from `config/<role>/game.toml [network]`
> — nothing hardcoded (FR-E1).

## Why a tunnel (NAT-traversal rationale)
Each peer runs its **own** FastMCP server (no central server, F1). Laptops sit
behind NAT/firewalls with no public IP and no port-forwarding. An outbound
tunnel (ngrok/Localtonet) opens a relay from a public HTTPS URL to the local
port, so the opponent can reach `receive_turn`/`negotiate`/… without either side
configuring their router. TLS terminates at the tunnel edge.

## Security model
- **Ephemeral URLs** — regenerated per match; never committed, never a secret.
- **No secrets in URLs** — auth is not URL-borne; `token.json`/keys stay local.
- **Integrity over an untrusted transport** — even if the tunnel is observed or
  a peer lies, correctness holds: `game.json` is SHA-256-signed (handshake
  refuses on mismatch) and every move is Commit-Reveal + end-of-game mutual
  audit (Stage 6). The tunnel is a dumb pipe; trust comes from the crypto.

## Runbook — ngrok (PRIMARY)
```bash
# 1. Each peer serves on 0.0.0.0:<my_port> (league override of the 127.0.0.1 default)
uv run cipherchase peer --role police --config config/police   # live league peer (P1, real command)
# 2. Open the tunnel to that port
ngrok http 8001                                           # -> https://<id>.ngrok-free.app
# 3. Exchange the two public URLs with the opponent out-of-band (chat/email)
# 4. Set opponent_url in config/<role>/game.toml [network], relaunch
# 5. Handshake locks game.json (config_sha256 match) -> automated play begins
```

## Runbook — Localtonet (FALLBACK)
Identical flow; swap step 2 for an equivalent outbound tunnel:
```bash
localtonet http 8001        # -> https://<id>.localtonet.com
```
Use when ngrok's free rate caps or regional routing get in the way.

## League pre-match checklist
1. Exchange public tunnel URLs.
2. Exchange the **Step-0 signed declaration** (members, hardware, LLM model,
   GitHub commit hash — Stage 6).
3. Both sides lock `config/*/game.json`; **verify `config_sha256` matches** (a
   mismatch aborts the match — never play an unequal constitution).
4. Set `host = "0.0.0.0"` and each side's `opponent_url` to the peer's tunnel.
5. Confirm the `negotiate` handshake succeeds, then let automated play run.

## Notes
- **Tunnel drop = silent peer.** A dropped tunnel is indistinguishable from a
  silent opponent and funnels into the Watchdog → `TECHNICAL_LOSS` (0/0, no
  hang). That path is owned by Stage 7, not reimplemented here (FR-H3).
- **Manual smoke test (non-CI):** start both peers on localhost, one `ngrok`
  tunnel, point `opponent_url` at it, play one round, and capture a screenshot
  for the README. This is never part of `pytest`.
- See **ADR-005** (PLAN §10) for the tunnel decision of record.
