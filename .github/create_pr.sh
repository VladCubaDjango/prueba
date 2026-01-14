#!/usr/bin/env bash
set -euo pipefail

# Usage: ./create_pr.sh [branch] [base]
BRANCH=${1:-add/indexes-reservation-menu}
BASE=${2:-main}
BODY_FILE=".github/PR_COMMENTS/ci-addition.md"

if [ ! -f "$BODY_FILE" ]; then
  echo "PR body file not found: $BODY_FILE"
  exit 1
fi

# extract title (first line starting with 'Title: ')
PR_TITLE=$(sed -n '1p' "$BODY_FILE" | sed 's/^Title: //')
# body without the title line
PR_BODY=$(sed '1d' "$BODY_FILE")

# prefer gh cli
if command -v gh >/dev/null 2>&1; then
  echo "Using gh CLI to create PR..."
  gh pr create --base "$BASE" --head "$BRANCH" --title "$PR_TITLE" --body-file "$BODY_FILE"
  exit $?
fi

# fallback to GitHub API using GITHUB_TOKEN
if [ -z "${GITHUB_TOKEN-}" ]; then
  echo "Error: gh CLI not found and GITHUB_TOKEN not set. Install gh or set GITHUB_TOKEN env var." >&2
  exit 2
fi

# get repo info from git remote
REMOTE_URL=$(git config --get remote.origin.url)
# support git@github.com:owner/repo.git and https://github.com/owner/repo.git
if [[ "$REMOTE_URL" =~ git@github.com:(.*)/(.*)\.git ]]; then
  OWNER=${BASH_REMATCH[1]}
  REPO=${BASH_REMATCH[2]}
elif [[ "$REMOTE_URL" =~ https://github.com/(.*)/(.*) ]]; then
  OWNER=${BASH_REMATCH[1]}
  REPO=${BASH_REMATCH[2]}
else
  echo "Unable to parse remote origin URL: $REMOTE_URL" >&2
  exit 3
fi

API_URL="https://api.github.com/repos/$OWNER/$REPO/pulls"

PAYLOAD=$(jq -n --arg title "$PR_TITLE" --arg head "$BRANCH" --arg base "$BASE" --arg body "$PR_BODY" '{title: $title, head: $head, base: $base, body: $body}')

RESPONSE=$(curl -s -H "Authorization: token $GITHUB_TOKEN" -H "Accept: application/vnd.github.v3+json" -d "$PAYLOAD" "$API_URL")

PR_URL=$(echo "$RESPONSE" | jq -r .html_url)
if [ "$PR_URL" = "null" ] || [ -z "$PR_URL" ]; then
  echo "Failed to create PR. Response:" >&2
  echo "$RESPONSE" >&2
  exit 4
fi

echo "PR created: $PR_URL"
exit 0
