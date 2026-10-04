#!/usr/bin/env bash
set -euo pipefail

: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY must be set}"
: "${GH_TOKEN:?GH_TOKEN must be set}"

export TZ="${TZ:-America/Los_Angeles}"

is_footer_subject() {
  local subject="$1"
  [[ "$subject" == "chore: update footer dates" || "$subject" == "chore: update footer dates ("* ]]
}

# Ensure we operate from the latest master state.
git fetch origin master
git checkout -B master origin/master

if [ -n "${FOOTER_DATE_REF:-}" ]; then
  CONTENT_SHA="$FOOTER_DATE_REF"
else
  CONTENT_SHA=""
  while IFS=$'\t' read -r sha subject; do
    if ! is_footer_subject "$subject"; then
      CONTENT_SHA="$sha"
      break
    fi
  done < <(git log --format='%H%x09%s' --no-decorate)
  if [ -z "$CONTENT_SHA" ]; then
    CONTENT_SHA="$(git rev-parse HEAD)"
  fi
fi
export FOOTER_DATE_REF="$CONTENT_SHA"

TZ="${TZ}" FOOTER_DATE_REF="$CONTENT_SHA" python3 scripts/update_footer_dates.py

if git diff --quiet -- '*.html'; then
  echo "No root HTML changes after footer date update."
  exit 0
fi

BRANCH="chore/update-footer-dates-${CONTENT_SHA:0:12}"

git checkout -B "$BRANCH"

git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

git add -- '*.html'

git commit -m "chore: update footer dates"

REMOTE_SHA="$(git ls-remote --heads origin "$BRANCH" | awk '{print $1}' | head -n 1 || true)"
if [ -n "$REMOTE_SHA" ]; then
  git push --force-with-lease=refs/heads/"$BRANCH":"$REMOTE_SHA" origin "$BRANCH"
else
  git push origin "$BRANCH"
fi

PR_NUMBER="$(gh pr list --repo "$GITHUB_REPOSITORY" --head "$BRANCH" --state open --json number --jq '.[0].number // empty')"
if [ -z "$PR_NUMBER" ]; then
  gh pr create \
    --repo "$GITHUB_REPOSITORY" \
    --base master \
    --head "$BRANCH" \
    --title "chore: update footer dates" \
    --body "Automated footer date refresh for ${CONTENT_SHA}"
  PR_NUMBER="$(gh pr view "$BRANCH" --repo "$GITHUB_REPOSITORY" --json number --jq '.number')"
fi

DISPATCH_START="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
gh workflow run pr-check.yml --repo "$GITHUB_REPOSITORY" --ref "$BRANCH"

WORKFLOW_HEAD_SHA="$(git rev-parse HEAD)"
RUN_ID=""
for attempt in $(seq 1 30); do
  RUN_ID="$(gh run list \
    --repo "$GITHUB_REPOSITORY" \
    --workflow pr-check.yml \
    --branch "$BRANCH" \
    --event workflow_dispatch \
    --limit 20 \
    --json databaseId,headBranch,headSha,createdAt,status \
    --jq ".[] | select(.headSha == \"$WORKFLOW_HEAD_SHA\" and .createdAt >= \"$DISPATCH_START\") | .databaseId" | head -n 1 || true)"

  if [ -n "$RUN_ID" ]; then
    break
  fi

  sleep 10
 done

if [ -z "$RUN_ID" ]; then
  echo "Timed out waiting for workflow_dispatch run for $BRANCH" >&2
  exit 1
fi

gh run watch "$RUN_ID" --repo "$GITHUB_REPOSITORY" --exit-status

gh pr checks "$PR_NUMBER" --repo "$GITHUB_REPOSITORY" --required --watch --fail-fast --interval 5

gh pr merge "$PR_NUMBER" --repo "$GITHUB_REPOSITORY" --squash --delete-branch
