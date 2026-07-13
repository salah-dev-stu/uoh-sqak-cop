# PRD_crypto — CipherChase: Cryptographic Fairness (Commit-Reveal · SHA-256 · Mutual Audit · Step-0 Declaration)

## 1. Header

| Field | Value |
|---|---|
| **Mechanism** | Cryptographic fairness — Commit-Reveal, mutual audit, Step-0 signed declaration |
| **Stage** | 6 of 7 (graded spine) |
| **Chapter** | Ch5 |
| **Gates** | **F3** (Commit-Reveal + SHA-256) · **F4** (mutual audit → 0/0 on tamper) · **F5** (Step-0 signed declaration w/ per-game GitHub commit hash) |
| **FRs** | FR-F1, FR-F2, FR-F3, FR-F4 |
| **Modules** | `domain/crypto.py` · `peer/turn_sender.py` · `peer/turn_handler.py` · `peer/sealing.py` · `peer/summary.py` · `peer/handshake.py` · `shared/sysinfo.py` |
| **Version** | 1.00 (single-source `shared/version.py`) |
| **Status** | Gate-3 per-mechanism draft — approve before TODO/build |
| **Depends on** | Stage 1 (`domain/board`, `domain/rules`), Stage 2 (`domain/protocol`, `peer/turn_*`), Stage 4 (`Intent` from `PRD_language_scent`) |
| **Feeds** | Stage 7 (`PRD_reporting_gui` — log/result artifacts, mutual signature, Replay re-hash) |

---

## 2. Purpose & scope

CipherChase has **no judge and no central server** (N1). Two mutually-distrustful processes exchange moves and free-text hints that **may deliberately lie**. Nothing prevents a peer from *claiming after the fact* that it moved elsewhere, placed a barrier it never placed, or "captured" a thief it never cornered. This mechanism removes the need to trust the peer at all: **correctness is decided by mathematics, not judgment.**

The scope is exactly the zero-trust integrity layer:

- **Commit-Reveal (FR-F1/F2):** each move is bound to an unforgeable SHA-256 commitment *before* the opponent responds; the plaintext (and, critically, the per-step nonce) is revealed later, so a peer cannot retroactively change what it committed.
- **Mutual audit (FR-F3):** at game end each side re-hashes **every** recorded step of the other. Any single mismatch — or any physical claim contradicted by the revealed board — voids the forging side to **0/0** (`tamper_forfeit`, the "iron rule").
- **Step-0 signed declaration (FR-F4/F5):** before any move, each peer emits a SHA-256-signed JSON stating its hardware (from `sysinfo`), LLM model, team, player IDs, and the **per-game GitHub commit hash**, pinning the exact code that played.

**Out of scope:** the wire transport itself (Stage 2 `infra/mcp_*`), how `Intent` (truth/lie) text is generated (Stage 4 `strategy/trash_talk`), and how the audited records are serialized into the 4 JSON artifacts and emailed (Stage 7 `report/`). This PRD produces the *primitives and protocol*; those PRDs consume them.

**Interop is byte-critical (C3).** The commit formula in §4 is **frozen** and must match every opponent byte-for-byte, or every cross-team game auto-forfeits. This document reproduces it verbatim from PRD §5 (FR-F1) and PLAN §8.

---

## 3. Requirements

### Functional

- **FR-F1 — Commit formula (frozen).** `CommitReveal.commit_of(payload, nonce)` returns the hex SHA-256 of `canonical_json(payload) + "|" + nonce`, where `canonical_json = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",",":"))`. `payload = {State, Move, Intent, Nonce-context}` as agreed. `seal(payload)` draws `nonce = secrets.token_hex(16)` (32 hex chars) and returns `(commit, nonce)`. `verify(payload, nonce, commit)` recomputes and compares with `secrets.compare_digest`. The `"|"` pipe separator and `.encode()` before hashing are **mandatory**.
- **FR-F2 — Turn order.** Per move: **Commit → Acknowledge (lock) → Reveal (move + hint, nonce STILL hidden) → end-of-game reveal of ALL nonces.** The nonce never travels until the whole game is over.
- **FR-F3 — Mutual audit.** `audit_records(records)` re-hashes every step; returns `{passed, verified_steps, failed_steps}`. Any mismatch, or any physical claim (barrier / capture / win) contradicted by the revealed board, → `tamper_forfeit` **0/0** for the forging side.
- **FR-F4 / F5 — Step-0 declaration.** A signed JSON emitted before turn 1 containing OS/CPU/RAM/GPU (from `sysinfo`), LLM model+version, team name, player IDs, and the per-game **GitHub commit hash**; "signed" = SHA-256 over the same `canonical_json` of the declaration body.

### Non-functional

- **NFR-CR1 (R8):** every file in §4 ≤150 lines raw **and** logical (`check_file_lines.py`).
- **NFR-CR2 (R7/R10):** TDD; ≥85% coverage of `crypto.py` and the seal/reveal/audit paths, all externals mocked.
- **NFR-CR3 (R11):** no hardcoding — separator, hash name, nonce width read as module constants sourced from config/`constants.py`, never scattered literals; the *formula shape* is frozen by the interop contract and lives in one place.
- **NFR-CR4 (R3):** `sysinfo` shells out (`sysctl`, `system_profiler`) **only** through `ApiGatekeeper.execute(..., service="subprocess")`.
- **NFR-CR5 (security):** nonces come only from `secrets`; equality checks only via `secrets.compare_digest` (no `==` on digests — timing + habit safety); no nonce logged or transmitted before end-of-game reveal.
- **NFR-CR6 (determinism):** `canonical_json` is byte-deterministic for equal payloads across processes and platforms (asserted by an exact-bytes test, §7).

---

## 4. Design

### 4.1 `domain/crypto.py` — `CommitReveal` (pure, no I/O)

Static/stateless API (matches PLAN §4 UML — all methods `$`/static):

```python
class CommitReveal:
    @staticmethod
    def canonical(payload: dict) -> str:
        return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def commit_of(payload: dict, nonce: str) -> str:
        # FROZEN INTEROP FORMULA — byte-identical with opponents
        return hashlib.sha256(
            (CommitReveal.canonical(payload) + "|" + nonce).encode()
        ).hexdigest()

    @staticmethod
    def seal(payload: dict) -> tuple[str, str]:
        nonce = secrets.token_hex(16)            # 32 hex chars
        return CommitReveal.commit_of(payload, nonce), nonce

    @staticmethod
    def verify(payload: dict, nonce: str, commit: str) -> bool:
        return secrets.compare_digest(CommitReveal.commit_of(payload, nonce), commit)
```

**The single frozen line, reproduced verbatim (interop-critical):**

```python
commit = hashlib.sha256(
    (json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",",":")) + "|" + nonce).encode()
).hexdigest()
```

with `nonce = secrets.token_hex(16)` and verification via `secrets.compare_digest`. Any deviation — spacing in `separators`, `ensure_ascii`, key ordering, the `"|"` byte, the `.encode()`, the hash algorithm — breaks byte-compatibility and auto-forfeits league games. This formula is identical to PRD §5 FR-F1 and PLAN §8; it MUST NOT drift.

`payload` shape (the "Nonce-context as agreed"): `{"state": <own_state digest / step index>, "move": {"move_type","direction"}, "intent": "truth"|"lie", "step": <int>}`. The exact key set is frozen jointly with the opponent at handshake and pinned in `game.json`; `Intent` is supplied by Stage 4 (`brains.Decision.verdict` / `intent`).

### 4.2 `audit_records(records)` algorithm (`domain/crypto.py`)

Input: the *opponent's* end-of-game record list, each entry `{step, payload, nonce, commit, barrier_placed, capture_claim, win_claim, move}` plus the revealed final board (barriers/positions) reconstructed from the log.

```
audit_records(records, board_view) -> {passed, verified_steps, failed_steps}
  failed = []
  for r in records:
      # (a) cryptographic integrity: does the revealed plaintext+nonce hash to the committed value?
      if not CommitReveal.verify(r.payload, r.nonce, r.commit):
          failed.append((r.step, "commit_mismatch"))
      # (b) plaintext consistency: revealed move must equal the move applied that step
      if r.payload["move"] != r.move:
          failed.append((r.step, "move_altered"))
      # (c) physical-claim truth: cross-check claims against the reconstructed board
      if r.barrier_placed and not board_view.barrier_legal_at(r.step, r.barrier_placed):
          failed.append((r.step, "false_barrier"))
      if r.capture_claim and not board_view.capture_valid_at(r.step):
          failed.append((r.step, "false_capture"))
      if r.win_claim and not board_view.win_valid(r.win_claim):
          failed.append((r.step, "false_win"))
  return {"passed": not failed,
          "verified_steps": len(records) - len({s for s,_ in failed}),
          "failed_steps": failed}
```

Each side runs `audit_records` over the *other* side's records (PLAN §6). The check is **symmetric and independent**: neither peer trusts the other's self-report.

### 4.3 Reveal / nonce-hiding protocol (FR-F2)

Per turn (PLAN §5 sequence), the **nonce is withheld until the entire game ends**:

1. **Commit** — mover: `seal(payload)` → `(commit, nonce)`; records `{payload, nonce, commit}` **locally only**; sends `TurnMessage{commit, hint, smell_grid}` (no move, no nonce).
2. **Acknowledge (lock)** — opponent acks; the mover's commitment is now locked and cannot be changed.
3. **Reveal** — mover sends `{move, intent, hint}`. Opponent applies the move to its own state and updates belief. **The nonce is STILL hidden.**
4. **End-of-game reveal** — only at game end (via `submit_audit`) does each side hand over **all** `{payload, nonce, commit}` records for the whole game.

**Why the nonce stays hidden until audit:** the commitment binds the move, but if the nonce were revealed per-turn, a peer could see the opponent's committed hash *plus* enough structure to attempt **pre-image / grinding games** or correlate nonces across turns to predict behavior. Holding all nonces until the game is over means no information beyond the move itself leaks during play, yet every commitment remains fully verifiable afterward. The commitment is "hiding" (nonce-blinded) during play and "binding" (re-hashable) at audit — exactly the Commit-Reveal guarantee.

### 4.4 `tamper_forfeit` result path (FR-F3, the iron rule)

If `audit_records(opponent.records).passed is False`, the auditing peer sets its local outcome to `tamper_forfeit` = **0/0 for the forging side** and transitions the state machine `AUDIT → TECHNICAL_LOSS` (PLAN §7). No score is negotiated; the forfeit is unilateral and self-evident because the auditor holds the cryptographic proof (the mismatching `{payload, nonce, commit}` triple, or the board-contradicting claim). `summary.py` records the `failed_steps` list as evidence for the Stage-7 `result` artifact. There is no appeal and no partial credit — any single failed step voids the whole game for the forger.

### 4.5 Step-0 declaration structure + signing (FR-F4/F5)

Built by `peer/handshake.py` before turn 1, from `shared/sysinfo.py`:

```json
{
  "schema": "declaration/1.0",
  "team": "uoh-sqak",
  "players": [{"name": "Salah Qadah", "id": "323039974"},
              {"name": "Andalus Kalash", "id": "211435797"}],
  "role": "police" | "thief",
  "git_commit": "<per-game GitHub commit hash>",
  "llm": {"provider": "template", "model": "<name>", "version": "<ver>"},
  "system": {"os": "...", "cpu": "...", "ram_gb": 8, "gpu": "..."},
  "version": "1.00",
  "signature": "<sha256 hex over canonical_json of the body above (signature field excluded)>"
}
```

**Signing** = SHA-256 over `canonical_json(body)` where `body` is every field **except** `signature`, using the identical `canonical_json` of §4.1 (same `sort_keys`/`separators`/`ensure_ascii`). Verification recomputes and compares with `secrets.compare_digest`. The `git_commit` field pins the *exact* code that played this game (F5), so a post-hoc code swap is detectable.

### 4.6 `shared/sysinfo.py` — macOS OS/CPU/RAM/GPU probe

Returns the `system` block above. Fields and sources (all subprocess calls via gatekeeper, NFR-CR4):

| Field | Source |
|---|---|
| `os` | `platform.platform()` / `sw_vers` |
| `cpu` | `sysctl -n machdep.cpu.brand_string` (Apple Silicon: `machdep.cpu.brand_string` / `hw.model`) |
| `ram_gb` | `sysctl -n hw.memsize` → bytes → GiB |
| `gpu` | `system_profiler SPDisplaysDataType` (name only) |

Degrades gracefully: any probe failure yields `"unknown"` for that field (never raises), so the declaration always builds.

### 4.7 Peer modules (each ≤150 lines)

| File | Role in this mechanism |
|---|---|
| `peer/sealing.py` | Bookkeeping: append `{step, payload, nonce, commit, move, barrier_placed, capture_claim, win_claim}` to the local record list each step; expose `all_records()` for end-of-game reveal. Holds nonces privately until then. |
| `peer/turn_sender.py` | Commit path: call `crypto.seal`, record via `sealing`, send `TurnMessage{commit,...}` through the gatekeeper; later send the reveal (move+intent, nonce withheld). |
| `peer/turn_handler.py` | Receive path: ack (lock) on commit; on reveal, apply move + update belief; store the opponent's revealed `{payload, move, commit}` awaiting its nonce at audit. |
| `peer/summary.py` | End-of-game: exchange full record lists, invoke `crypto.audit_records` over the opponent's records, decide `tamper_forfeit` vs verified outcome, emit evidence for Stage 7. |
| `peer/handshake.py` | Build + sign the Step-0 declaration; verify the opponent's declaration signature; lock `game.json` (frozen payload key set + commit formula). |

---

## 5. Threat model & disqualification triggers

Zero-trust: assume the peer is an adversary trying to win by cheating. Each attack and how the math catches it:

| Attack | What the adversary does | How it is caught |
|---|---|---|
| **Log alteration** | Edits a recorded step's `payload` before the audit reveal | `verify(payload, nonce, commit)` fails — the committed hash no longer matches (`commit_mismatch`) → 0/0 |
| **Post-commit move change** | Commits move A, later reveals/applies move B | Reveal step (b): `payload["move"] != move`, and the commit binds A, so `verify` fails (`move_altered`) → 0/0 |
| **False barrier** | Claims a barrier it never legally placed (or on an illegal cell) | Cross-check against the reconstructed board: `barrier_legal_at` false (`false_barrier`) → 0/0 |
| **False capture / false win** | Claims capture/victory not supported by the revealed positions | `capture_valid_at` / `win_valid` false (`false_capture`/`false_win`) → 0/0 |
| **Replay** | Reuses a prior game's commit/nonce to forge a "valid-looking" step | Fresh `nonce = secrets.token_hex(16)` per step + per-game `git_commit` + `game_uid` in the declaration bind the record to this game; a replayed nonce won't hash against this game's payload/step |
| **Nonce grinding / pre-image** | Tries to find a payload/nonce colliding with a committed hash during play | SHA-256 pre-image resistance + nonces hidden until game end (§4.3) → no exploitable info leaks mid-game |
| **Code swap after declaration** | Plays with different code than declared | Step-0 `git_commit` pins the exact commit (F5); mismatch is evidence |

Any one trigger = `tamper_forfeit` 0/0 for the forging side (the iron rule). Physical facts (moves, barriers, captures) must be TRUTHFUL; only the free-text **hint** may bluff (FR-D2) — and the `Intent` flag that declares whether the hint lies is itself committed and revealed, so even the bluff is auditable for consistency with its declared intent.

---

## 6. Edge cases & error handling

- **Nonce reuse guard:** nonces are always freshly drawn from `secrets.token_hex(16)`; `sealing.py` never reuses a nonce across steps. (Collision probability at 128 bits is negligible; no explicit dedup needed, but tests assert distinctness across a run.)
- **Malformed reveal:** a reveal whose `payload` is missing keys, has a wrong type, or is non-JSON-serializable → `CryptoError` (from `exceptions.py`); the handler treats it as a failed step (audit fails that step → 0/0), never a crash.
- **Missing nonce at audit:** if the opponent omits a step's nonce in its end-of-game reveal, that step **cannot** be verified → automatic `failed_steps` entry (`missing_nonce`) → `tamper_forfeit`. Absence of proof is treated as tamper.
- **Signature failure on declaration:** if the opponent's declaration signature doesn't verify (or `git_commit` is empty), `handshake` rejects → state machine → `TECHNICAL_LOSS` before turn 1.
- **`sysinfo` probe failure:** field-level fallback to `"unknown"`; never blocks declaration construction (§4.6).
- **`CryptoError`** (defined in `cipherchase/exceptions.py`) is the single typed exception for all commit/verify/audit/canonicalization failures; callers catch it at the peer boundary and route to the audit-failure / technical-loss path, never surface a raw traceback.
- **Non-ASCII in hints/payload:** `ensure_ascii=False` means UTF-8 text hashes consistently; `.encode()` (UTF-8 default) is mandatory and asserted by the exact-bytes test.

---

## 7. TDD test plan (Red → Green → Refactor)

Externals mocked (subprocess for `sysinfo` via gatekeeper fake); `crypto.py` is pure and needs none.

1. **Commit/verify round-trip:** `seal(payload)` → `verify(payload, nonce, commit)` is `True`; a mutated `payload` or wrong `nonce` → `False`.
2. **`compare_digest` usage:** `verify` returns `False` for a one-char-different commit; test asserts `secrets.compare_digest` is the comparison (no `==`).
3. **Audit passes a clean log:** a full honest cop-vs-thief loopback record → `audit_records` returns `passed=True`, `failed_steps=[]`, `verified_steps == len(records)`.
4. **Audit FAILS a mutated payload:** flip one byte of a recorded `payload` → `passed=False`, correct step flagged `commit_mismatch`.
5. **Audit FAILS an altered move:** commit move N, reveal move S → flagged `move_altered`.
6. **Audit FAILS a false barrier/capture:** inject `barrier_placed` on an illegal cell / `capture_claim` unsupported by the board → `false_barrier` / `false_capture`; result path → `tamper_forfeit` 0/0.
7. **Missing-nonce at audit → forfeit:** drop one step's nonce → `missing_nonce` in `failed_steps`, `passed=False`.
8. **Declaration verifies:** build → sign → `verify` True; tamper any body field (or `git_commit`) → verify False → handshake rejects.
9. **Deterministic canonical bytes (interop lock):** assert `CommitReveal.canonical({"b":2,"a":1})` **== exact string** `'{"a":1,"b":2}'`; assert a known `(payload, nonce)` pair hashes to a **hard-coded expected hex digest** (golden vector) — guards the frozen formula against silent drift and matches opponents byte-for-byte.
10. **Nonce distinctness / width:** many `seal` calls → all nonces distinct, each 32 hex chars.
11. **`CryptoError` on malformed reveal:** non-serializable / missing-key payload raises `CryptoError`, handled as a failed step, not a crash.
12. **`sysinfo` fallback:** patched subprocess raising → fields default to `"unknown"`, declaration still builds and signs.

---

## 8. Milestone & Definition of Done

**Milestone (binary — from PRD §9, Stage 6):** *A move is committed then revealed with a valid nonce; the Step-0 declaration verifies; the audit voids a tampered log.* Concretely, one green test drives: `seal → send commit → ack → reveal → record`, then `handshake` builds+verifies a signed declaration, then `audit_records` returns `passed=True` on the honest loopback **and** `passed=False` (→ `tamper_forfeit` 0/0) on a mutated copy of the same log.

**Definition of Done:**
- `domain/crypto.py`, `peer/{turn_sender,turn_handler,sealing,summary,handshake}.py`, `shared/sysinfo.py` implemented, each ≤150 lines raw+logical.
- Frozen formula (§4.1) reproduced exactly; golden-vector test (§7.9) green.
- All §7 tests pass; coverage ≥85% for the crypto/audit paths with externals mocked.
- `ruff check` = 0; `check_file_lines.py` = 0; version-sync green in CI.
- Records/evidence structure handed to Stage 7 matches the log/result artifact schema (see §10 assumptions).

---

## 9. Traceability

| Gate / FR / NFR | Satisfied by (section) |
|---|---|
| **F3** (Commit-Reveal + SHA-256) | §4.1, §4.3, §7.1–2, §7.9 |
| **F4** (mutual audit → 0/0 on tamper) | §4.2, §4.4, §5, §7.3–7 |
| **F5** (Step-0 signed decl + git commit hash) | §4.5, §4.6, §7.8, §7.12 |
| **FR-F1** (frozen commit formula) | §4.1, §3, §7.9 |
| **FR-F2** (commit→ack→reveal→end-reveal) | §4.3, §4.7, §7.1 |
| **FR-F3** (mutual audit / iron rule) | §4.2, §4.4, §5, §7.3–7 |
| **FR-F4** (Step-0 declaration) | §4.5, §4.6 |
| **NFR-CR1..6** | §3 (non-functional), §7 |

---

## 10. Dependencies & open questions

**Consumes (must match upstream):**
- **`Intent` (truth/lie)** from `PRD_language_scent` (Stage 4, FR-D3): the `intent`/`verdict` field placed into the committed `payload`. Its key name and value domain (`"truth"|"lie"`) must be frozen jointly so the payload key set is identical both sides. **Assumption to confirm with the language-scent PRD:** `Intent` is a top-level payload key `"intent"` with values exactly `"truth"`/`"lie"`, present on every committed move.
- `domain/protocol.TurnMessage` fields (`commit`, `barrier_placed`, `capture_claim`, `win_claim`) from Stage 2 — the audit reads these claim fields.
- `domain/rules` + `domain/board` — `audit_records` uses them to reconstruct the board and validate physical claims.

**Feeds (downstream must match):**
- **`PRD_reporting_gui` (Stage 7):** the per-step record list `{step, payload, nonce, commit, move, barrier_placed, capture_claim, win_claim}` and the audit result `{passed, verified_steps, failed_steps}` are the raw material for the `log_<id>_g<NN>.json` and `result_<id>.json` artifacts, and for the Replay Viewer's per-step re-hash ("Verified OK" / "TAMPERED"). **Assumption the reporting PRD must honor:** it re-uses `CommitReveal.verify` (not a re-implementation) so Replay and audit agree byte-for-byte.
- **Mutual signature (ADR-009, FR-G1):** Stage 7 hashes **only the symmetric outcome** so both peers produce an identical signature. **Assumption:** the audit's shared inputs (both record lists + agreed result) are canonicalized with the **same** `canonical_json` (§4.1) that this PRD defines, and the signature excludes peer-private fields (nonces are shared by then, but private scoring/belief is excluded).

**Open questions:**
- **OQ-1:** Exact frozen payload key set (`{state, move, intent, step}` vs including `game_uid`) — must be agreed with opponents at handshake and pinned in `game.json`; the golden vector (§7.9) locks it once chosen.
- **OQ-2:** Does the Step-0 `git_commit` reference the repo tag `v1.0-submission` commit, or the live HEAD at match time? (Affects F5 verification across the two cross-linked repos.)
- **OQ-3:** GPU field content on the M2 (8 GB) — integrated GPU name only; confirm `system_profiler` output is stable enough to declare without leaking noise.
