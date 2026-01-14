Open PR from a new machine

You can create the PR for branch `add/indexes-reservation-menu` using one of the methods below.

Option A (recommended) — gh CLI (most convenient):
1. Install GitHub CLI: https://cli.github.com/
2. Authenticate: `gh auth login`
3. From project root run:
   - `gh pr create --base main --head add/indexes-reservation-menu --title "$(head -n1 .github/PR_COMMENTS/ci-addition.md | sed 's/^Title: //')" --body-file .github/PR_COMMENTS/ci-addition.md`

Option B — helper script (bash or PowerShell):
- Bash (Linux/macOS/Git Bash on Windows):
  - `chmod +x .github/create_pr.sh`
  - `GITHUB_TOKEN=your_token .github/create_pr.sh add/indexes-reservation-menu main`
- PowerShell (Windows):
  - `.\.github\create_pr.ps1 -Branch add/indexes-reservation-menu -Base main`
  - If using the API fallback, set `GITHUB_TOKEN` environment variable first.

Option C — manual: open https://github.com/<owner>/<repo>/compare and select the branch `add/indexes-reservation-menu`, then create the PR using the content of `.github/PR_COMMENTS/ci-addition.md`.

Notes:
- The helper scripts prefer `gh` if available, otherwise they use the GitHub API with `GITHUB_TOKEN`.
- Do not commit or paste personal tokens into the repo. Use environment variables or the `gh` auth flow.
