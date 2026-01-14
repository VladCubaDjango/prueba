<#
.SYNOPSIS
Create a PR using gh CLI or GitHub API (PowerShell)

Usage: .\create_pr.ps1 [-Branch] [-Base]
#>
param(
    [string]$Branch = 'add/indexes-reservation-menu',
    [string]$Base = 'main'
)

$bodyFile = '.github/PR_COMMENTS/ci-addition.md'
if (-not (Test-Path $bodyFile)) { Write-Error "PR body file not found: $bodyFile"; exit 1 }

$title = Get-Content $bodyFile -TotalCount 1 -Raw -ErrorAction Stop
$title = $title -replace '^Title:\s*', ''
$body = Get-Content $bodyFile | Select-Object -Skip 1 | Out-String

if (Get-Command gh -ErrorAction SilentlyContinue) {
    Write-Host "Using gh CLI to create PR..."
    gh pr create --base $Base --head $Branch --title "$title" --body-file $bodyFile
    exit $LASTEXITCODE
}

if (-not $env:GITHUB_TOKEN) { Write-Error 'gh not found and GITHUB_TOKEN not set. Install gh or set GITHUB_TOKEN env var.'; exit 2 }

$remote = git config --get remote.origin.url
if ($remote -match 'git@github.com:(.+)/(.+)\.git') {
    $owner = $matches[1]; $repo = $matches[2]
} elseif ($remote -match 'https://github.com/(.+)/(.+)') {
    $owner = $matches[1]; $repo = $matches[2]
} else {
    Write-Error "Unable to parse remote origin URL: $remote"; exit 3
}

$apiUrl = "https://api.github.com/repos/$owner/$repo/pulls"
$payload = @{ title = $title; head = $Branch; base = $Base; body = $body } | ConvertTo-Json -Depth 8

$response = Invoke-RestMethod -Method Post -Uri $apiUrl -Headers @{ Authorization = "token $($env:GITHUB_TOKEN)"; Accept = 'application/vnd.github.v3+json' } -Body $payload
if ($response.html_url) { Write-Host "PR created: $($response.html_url)" } else { Write-Error "Failed to create PR. Response: $($response | ConvertTo-Json)"; exit 4 }
