# Submission Runbook — team `uoh-sqak` · deadline **Wed 2026-08-12 23:59** (strict)

Every agent-side deliverable is committed and gate-verified. What remains needs
**your accounts/credentials**, in this order. Nothing here lands on the deadline
day — finish steps 1–3 immediately, league games by Aug 8, paperwork by Aug 11.

## 1 · Publish the two repos (F14 — unpushed = auto-zero)

DONE (2026-07-29): both repos live under `salah-dev-stu` (the course requires
two cross-linked repos accessible to the grader — the owner account is free):
`https://github.com/salah-dev-stu/uoh-sqak-cop` ⇄ `…/uoh-sqak-thief`, pushed via
`scripts/publish_repos.sh`, first CI run green (ruff · ≤150 · version-sync ·
100%-coverage suite · self-match smoke · node arena tests · reference-interop
tripwire · README honesty guard).

## 2 · Gmail reporting (F10/F11)

DONE (2026-07-29): OAuth consent completed (scope `gmail.send` only, token at
`~/parley-secrets/token.json`, git-ignored) and the sample report REALLY sent
from BOTH roles to `rmisegal+uoh26finalgame@gmail.com` (Gmail ids
`19fae54529a9c995` police / `19fae545bbe0c9a3` thief). For league games, re-run:
```bash
CIPHERCHASE_GMAIL_TOKEN=~/parley-secrets/token.json \
CIPHERCHASE_CONFIG=config/<role> uv run --extra real python scripts/send_sample_report.py
```

## 3 · League games (F14: ≥2 games vs different `uoh-*` groups)

1. Send each opponent group `docs/INTEROP-CONTRACT.md` (the complete wire kit).
2. Start your tunnel per `docs/deploy-tunnel.md` (ngrok primary) and exchange
   `https://…/mcp` URLs; set theirs in `config/<role>/game.toml → [network]
   opponent_url` and agree the shared `game.json` (edit `agreed_between` to
   `["uoh-sqak", "<their-group>"]` on BOTH sides — must stay byte-identical).
3. **Set the recipient for the KIND of game you are about to play.** A friendly
   goes to the two teams only — mailing the lecturer a practice series is not
   undoable. `[email] recipient` accepts a comma-separated list:
   ```toml
   # FRIENDLY (uncounted): both teams, never the lecturer
   recipient = "<their addresses>, skadah324@gmail.com"
   # COUNTED: the lecturer alone
   recipient = "rmisegal+uoh26finalgame@gmail.com"
   ```
   Set `enabled = true` only once the recipient is right for this game.
4. Play — naming the opponent is what turns a peer run into a *reported* series
   (without `--opponent` it plays and reports nothing):
   ```bash
   uv run cipherchase peer --role police --config config/police \
       --opponent <their-group-id> --out docs/league/<their-group-id>
   ```
   Watch it live: `uv run python scripts/viz_server.py` → match room panel.
   This writes the 4 App-F artifacts **of the series actually played** and
   auto-mails them (rule 32 — never a human sending it). Filenames key off the
   sorted pair, so both teams derive the same `result_<a>-vs-<b>.json`.
5. Before anyone emails a counted series, run the league kit's checker over BOTH
   artifact directories so the cross-team join is verified, not assumed:
   `python tools/check_artifacts.py <ours> <theirs>`.
6. Commit the emitted JSONs under `docs/league/<group>/` as evidence. Repeat with
   a second group (the diversity bonus fires once per new group — ledger-tracked
   in `opponents.json`, and `first_meeting_between_groups` is declared truthfully
   in the result: a false one is a rule-38 project-level disqualification).

## 4 · Freeze: the submission tag

After the LAST commit (league evidence included):
```bash
scripts/publish_repos.sh --tag        # annotated v1.0-submission → both repos
```

## 5 · Paperwork (each member separately)

1. Download `uoh-rl07-final-project-2026.docx` from Moodle, fill **without
   altering fields** (repo links = the two URLs above; self-grade **85**;
   agent-report email `rmisegal+uoh26finalgame@gmail.com`), export as
   **`uoh-sqak-ex<NN>.pdf`** — confirm `<NN>` from the Moodle assignment title.
2. **Each member** uploads to Moodle assignment `id=294462` (per-individual
   timestamp) before Aug 12 23:59. Late = not submitted.

## Grader's 5-minute path (what the PDF should point at)

```bash
uv sync --dev && uv run pytest        # 100% coverage, no keys, ~6 min
uv run cipherchase self-match --config config/police --out logs
uv run cipherchase verify --log docs/sample-run/log_uoh-sqak-police-21644f70_g01.json
uv run python scripts/viz_server.py   # the 3D arena: T = guided tour
```

## Pre-flight checklist

- [ ] Both repos exist, accessible to `rmisegal@gmail.com`, CI green
- [ ] Cross-links in both READMEs resolve (already committed)
- [ ] OAuth done; 4 artifacts emailed from **both** roles
- [ ] ≥2 league games vs different groups; evidence committed
- [ ] `v1.0-submission` tag pushed to both repos
- [ ] `uoh-sqak-ex<NN>.pdf` ×2 uploaded on Moodle
