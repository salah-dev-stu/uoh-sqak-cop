#!/usr/bin/env bash
# Publish the mono-source to BOTH league repos (D1 / F14) and cross-link them.
# One codebase, two runtime roles: the repos are identical; the role is chosen
# at launch (`cipherchase peer --role ... --config config/<role>`).
#
# Usage:  scripts/publish_repos.sh <cop-remote-url> <thief-remote-url>
# Then:   scripts/publish_repos.sh --tag        # after the final commit
set -euo pipefail
cd "$(dirname "$0")/.."

if [ "${1:-}" = "--tag" ]; then
  git tag -a v1.0-submission -m "uoh-sqak final submission (course 203.3763)"
  git push cop main --tags
  git push thief main --tags
  echo "v1.0-submission tagged and pushed to both repos."
  exit 0
fi

COP_URL="${1:?usage: publish_repos.sh <cop-url> <thief-url>}"
THIEF_URL="${2:?usage: publish_repos.sh <cop-url> <thief-url>}"
git remote remove cop 2>/dev/null || true
git remote remove thief 2>/dev/null || true
git remote add cop "$COP_URL"
git remote add thief "$THIEF_URL"
git push -u cop main
git push -u thief main
echo "Both repos pushed. Verify the README cross-links, then run:  scripts/publish_repos.sh --tag"
