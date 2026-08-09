# CipherChase / police_thief — Interop Contract (one page, v1.00)

> Hand this to your team before our match. Everything is copy-pasteable; it is byte-compatible with the
> course reference implementation (`police_thief` v3.0.0). Contact: team `uoh-sqak`.

## 1. Transport
- Each peer runs its **own FastMCP HTTP server**; the peer URL **includes `/mcp`**: `http://<host>:<port>/mcp`.
- Four tools; note the **parameter names** (the audit one differs!):

| Tool | Call with | Ack |
|---|---|---|
| `negotiate` | `{"message": <agreement>}` | `{"ok": true}` |
| `receive_turn` | `{"message": <turn>}` | `{"ok": true}` |
| `submit_audit` | **`{"payload": <audit>}`** | `{"ok": true}` |
| `receive_control` | `{"message": <control>}` (optional channel) | `{"ok": true}` |

- Outbound calls retry every ~1 s for up to 60 s (peers may start at different times). Either side may start first.

## 2. Negotiation (per sub-game)
Both peers push, then read their own inbox. Payload:
```json
{"terms": { "board_size": 7, "smell_grid_size": 5, "decay_per_step": 0.1,
            "emit_intensity": 0.9, "min_center_intensity": 0.5, "max_steps": 35,
            "barriers_max": 14, "setting": "New York", "hint_max_words": 15,
            "axis_origin_corner": "top-left", "axis_start_index": 0,
            "thief_start": [3, 3], "cop_start": [0, 0], "num_games": 6 },
 "nonce": "<secrets.token_hex(16)>",
 "signature": "<commit formula over terms — §4>",
 "identity": { "group_id": "...", "group_name": "...", "members": [...], "repos": {},
               "mcp_servers": {}, "llm_model": "...", "spec": {} }}
```
- **`terms` must be value-equal on both sides** — most peers compare by exact dict equality, so a
  spelling difference (`top-left` vs `top_left`) fails the handshake as surely as a wrong number.
  The block above is generated from our config and CHECKED BY A TEST against the bytes we actually
  send (`tests/test_interop_contract_matches_the_wire.py`); an earlier hand-maintained version had
  drifted on five values and would have talked an opponent out of terms that already matched ours.
  We are flexible on all of them — tell us yours and we adopt. `identity` is informational, never
  compared, but FILE it: repos and counted-game counts arrive there and nowhere else.
- Both sides then derive identical ids: `game_id = "<min-gid>-vs-<max-gid>"`,
  `game_uid = UUID(bytes=sha256(canonical(terms) + "|" + lo_gid + "|" + hi_gid).digest()[:16])`.

## 3. Turn loop
- **Thief moves first.** Strict alternation; receiving a turn message makes you the mover. One message per turn:
```json
{"step": 1, "sender": "thief", "hint": "free text (may bluff)",
 "smell_grid": {"3,3": 0.9, "3,4": 0.63}, "commit": "<sha256 hex>",
 "timestamp": "2026-08-01T12:00:00+00:00", "barrier_placed": null,
 "capture_claim": null, "claim_response": null, "win_claim": null}
```
- The **move is never on the wire** — it is sealed inside `commit` and revealed only at the audit.
- Claims: police attaches `capture_claim = [r,c]` (its own new cell) on move turns; the thief answers honestly
  on its next message: `claim_response = {"claim": [r,c], "caught": true|false}` — if caught, its final message
  is a HOLD with hint `"You got me."`. Thief attaches `win_claim = {"type": "survival"}` on reaching `max_steps`.
- `barrier_placed = [r,c]` is public and must be truthful. Timeout: silent > 180 s ⇒ technical loss.

## 4. The commit formula (frozen)
```python
canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
commit    = hashlib.sha256((canonical + "|" + nonce).encode("utf-8")).hexdigest()
nonce     = secrets.token_hex(16)      # 32 hex chars, hidden until the audit
```
Golden vector: `payload={"a":1}`, `nonce="ab"*16` → commit `sha256('{"a":1}|' + "ab"*16)`.
Payload schema is **each side's own** — the audit re-hashes records verbatim, no schema matching needed.

## 5. End-of-game audit
Each side (except on timeout) sends its full record book and reads the peer's:
```json
{"sender": "thief", "records": [{"payload": {...}, "nonce": "...", "commit": "..."}, ...],
 "result_claim": "capture" | "survival"}
```
Re-hash every record; **any mismatch ⇒ the forger loses (0/0 tamper forfeit)** — the iron rule.

## 6. Sequence
`negotiate ⇄` → thief turn → police turn → … → claims → capture (`caught:true` + "You got me.") **or**
survival (`win_claim`) → `submit_audit ⇄` → both emit + email their reports.

## 7. Match checklist (with us)
1. Agree the `terms` values + `num_games` (we propose 6 — roles swap each sub-game: odd = your natural role).
2. Exchange public URLs (ngrok: `ngrok http <port>` → `https://….ngrok-free.app/mcp`).
3. Set each side's `opponent_url`; start both peers (order doesn't matter); play; both email reports to
   `rmisegal+uoh26finalgame@gmail.com`.
