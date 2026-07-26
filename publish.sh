#!/usr/bin/env bash
# Creates the GitHub repo, pushes everything, and enables GitHub Pages.
#
# Usage:
#   export GITHUB_TOKEN=ghp_xxxxxxxxxxxx
#   ./publish.sh                      # repo name defaults to mlb-daily-results
#   ./publish.sh my-custom-repo-name
#
# Token needs: Contents(rw), Pages(rw), Workflows(rw)  [fine-grained]
#          or: repo + workflow scopes                  [classic]

set -euo pipefail

REPO_NAME="${1:-mlb-daily-results}"
TOKEN="${GITHUB_TOKEN:-}"

if [ -z "$TOKEN" ]; then
  echo "ERROR: set GITHUB_TOKEN first:  export GITHUB_TOKEN=ghp_xxxx" >&2
  exit 1
fi

api() {
  curl -sS -w '\n%{http_code}' \
    -H "Authorization: Bearer $TOKEN" \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" "$@"
}

split() { BODY=$(echo "$1" | sed '$d'); CODE=$(echo "$1" | tail -n1); }

echo "==> Verifying token..."
split "$(api https://api.github.com/user)"
if [ "$CODE" != "200" ]; then
  echo "Token rejected (HTTP $CODE): $(echo "$BODY" | head -3)" >&2
  exit 1
fi
USERNAME=$(echo "$BODY" | grep -m1 '"login"' | cut -d'"' -f4)
echo "    Authenticated as: $USERNAME"

echo "==> Creating repo $USERNAME/$REPO_NAME ..."
split "$(api -X POST https://api.github.com/user/repos -d "{
  \"name\": \"$REPO_NAME\",
  \"description\": \"Daily MLB game results, box scores and standings - collected automatically\",
  \"homepage\": \"https://$USERNAME.github.io/$REPO_NAME/\",
  \"private\": false,
  \"has_issues\": true,
  \"has_wiki\": false
}")"
case "$CODE" in
  201) echo "    Created." ;;
  422) echo "    Already exists - will push into it." ;;
  *)   echo "Failed (HTTP $CODE): $(echo "$BODY" | head -5)" >&2; exit 1 ;;
esac

echo "==> Personalizing README with your username..."
sed -i.bak "s|USERNAME|$USERNAME|g" README.md && rm -f README.md.bak
git add README.md
git commit -qm "Point README at $USERNAME" || true

echo "==> Pushing..."
git remote remove origin 2>/dev/null || true
git remote add origin "https://x-access-token:${TOKEN}@github.com/${USERNAME}/${REPO_NAME}.git"
git branch -M main
git push -u origin main --quiet
git remote set-url origin "https://github.com/${USERNAME}/${REPO_NAME}.git"   # strip token
echo "    Pushed."

echo "==> Enabling GitHub Pages (main /docs)..."
split "$(api -X POST "https://api.github.com/repos/$USERNAME/$REPO_NAME/pages" \
  -d '{"source":{"branch":"main","path":"/docs"}}')"
case "$CODE" in
  201|204) echo "    Pages enabled." ;;
  409)     echo "    Pages already enabled." ;;
  *)       echo "    Could not auto-enable (HTTP $CODE). Turn it on manually:"
           echo "    Settings > Pages > Deploy from a branch > main > /docs" ;;
esac

cat <<EOF

============================================================
  Done.

  Repo:  https://github.com/$USERNAME/$REPO_NAME
  Site:  https://$USERNAME.github.io/$REPO_NAME/
         (first build takes 1-2 minutes)

  The collector runs automatically twice a day.
  Run it now:  Actions tab > "Collect MLB results" > Run workflow
============================================================
EOF
