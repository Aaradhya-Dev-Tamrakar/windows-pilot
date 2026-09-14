<#
.SYNOPSIS
Safely sync the WinPilot repository, check staged changes for secrets, run tests, and commit with smart messaging.

.DESCRIPTION
Pulls the latest changes from origin with rebase and autostash, runs test verification,
scans staged changes for accidental credentials/tokens, generates conventional commit messages
(feat/fix/refactor/test/docs) based on churn and component changes, and pushes to remote.
#>

[CmdletBinding()]
param (
    [Alias("m")]
    [string]$Message,

    [switch]$PullOnly,

    [switch]$SkipTests,

    [switch]$NoPush
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Status {
    param(
        [string]$Message,
        [System.ConsoleColor]$Color = [System.ConsoleColor]::Cyan
    )
    Write-Host "[$((Get-Date).ToString('HH:mm:ss'))] $Message" -ForegroundColor $Color
}

function Write-Notice {
    param([string]$Message)
    Write-Status -Message $Message -Color ([System.ConsoleColor]::Yellow)
}

function Write-Success {
    param([string]$Message)
    Write-Status -Message $Message -Color ([System.ConsoleColor]::Green)
}

function Find-StagedSecrets {
    $stagedDiff = git diff --cached -U0 2>$null
    if (-not $stagedDiff) { return @() }

    $addedLines = $stagedDiff | Where-Object { $_ -match '^\+[^+]' } | ForEach-Object { $_.Substring(1) }
    if (-not $addedLines) { return @() }

    $secretPatterns = @(
        'AKIA[0-9A-Z]{16}'
        'sk-[a-zA-Z0-9]{20,}'
        'sk-ant-[a-zA-Z0-9\-]{20,}'
        'ghp_[a-zA-Z0-9]{36}'
        'github_pat_[a-zA-Z0-9_]{20,}'
        'AIza[0-9A-Za-z\-_]{35}'
        'xox[baprs]-[0-9a-zA-Z\-]{10,}'
        '-----BEGIN (RSA|EC|OPENSSH|PGP|DSA)? ?PRIVATE KEY-----'
        '(?i)(api[_-]?key|secret|password|token|passwd)\s*[:=]\s*[''"][^''"\s]{8,}[''"]'
    )

    $hits = @()
    foreach ($line in $addedLines) {
        foreach ($pattern in $secretPatterns) {
            if ($line -match $pattern) {
                $snippet = $line.Trim()
                $hits += [PSCustomObject]@{
                    Pattern = $pattern
                    Snippet = $snippet.Substring(0, [Math]::Min(60, $snippet.Length))
                }
                break
            }
        }
    }

    return @($hits)
}

function Get-WinPilotScope {
    param([string[]]$ChangedFiles)

    if ($ChangedFiles | Where-Object { $_ -match 'tests/' }) { return "test" }
    if ($ChangedFiles | Where-Object { $_ -match 'winpilot/recipes/' }) { return "recipes" }
    if ($ChangedFiles | Where-Object { $_ -match 'winpilot/mcp_server' }) { return "mcp" }
    if ($ChangedFiles | Where-Object { $_ -match 'winpilot/cli' }) { return "cli" }
    if ($ChangedFiles | Where-Object { $_ -match 'winpilot/compose/' }) { return "compose" }
    if ($ChangedFiles | Where-Object { $_ -match 'winpilot/core/' }) { return "core" }
    if ($ChangedFiles | Where-Object { $_ -match 'docs/SAFETY_DIRECTIVES' }) { return "safety" }
    if ($ChangedFiles | Where-Object { $_ -match 'README\.md|docs/|AGENTS\.md|CONTRIBUTING\.md' }) { return "docs" }
    if ($ChangedFiles | Where-Object { $_ -match '\.github/' }) { return "ci" }
    if ($ChangedFiles | Where-Object { $_ -match 'pyproject\.toml|sync\.ps1|\.editorconfig' }) { return "config" }
    return "general"
}

function Get-AutoCommitMessage {
    $statusLines = git status --porcelain
    if (-not $statusLines) { return $null }

    $modifiedFiles = @()
    $addedFiles = @()
    $deletedFiles = @()
    $allRelativePaths = @()

    foreach ($line in $statusLines) {
        $status = $line.Substring(0, 2).Trim()
        $file = $line.Substring(3).Trim()
        $fileName = Split-Path $file -Leaf
        $allRelativePaths += $file

        if ($status -match 'A|\?\?') { $addedFiles += $fileName }
        elseif ($status -match 'D') { $deletedFiles += $fileName }
        else { $modifiedFiles += $fileName }
    }

    $allChanged = @($addedFiles + $modifiedFiles + $deletedFiles)
    if (@($allChanged).Count -eq 0) { return $null }

    $scope = Get-WinPilotScope -ChangedFiles $allRelativePaths
    $type = "chore"

    if (@($addedFiles).Count -gt 0) {
        $type = "feat"
    }
    elseif ($scope -eq "test") {
        $type = "test"
    }
    elseif ($scope -eq "docs") {
        $type = "docs"
    }
    elseif ($modifiedFiles | Where-Object { $_ -match '\.py$' }) {
        $type = "refactor"
    }

    $prefix = if ($scope -ne "general") { "${type}(${scope})" } else { "${type}" }

    $summary = ""
    if ($allChanged.Count -le 3) {
        $summary = $allChanged -join ", "
    }
    else {
        $firstTwo = ($allChanged[0..1]) -join ", "
        $extraCount = $allChanged.Count - 2
        $summary = "$firstTwo +$extraCount more"
    }

    $rawDiff = git diff --cached -U0 2>$null
    $diffStat = git diff --cached --shortstat 2>$null
    $churn = ""
    if ($diffStat -match '(\d+) insertion') { $ins = $Matches[1] } else { $ins = 0 }
    if ($diffStat -match '(\d+) deletion') { $del = $Matches[1] } else { $del = 0 }
    if (($ins + 0) -gt 0 -or ($del + 0) -gt 0) { $churn = " (+$ins/-$del)" }

    $hunkContext = $rawDiff |
        Select-String '^@@.*@@\s*(\S.*)$' |
        ForEach-Object { $_.Matches[0].Groups[1].Value } |
        Select-Object -First 1

    if (-not $hunkContext) {
        $addedLine = $rawDiff |
            Select-String '^\+[^+]' |
            ForEach-Object { $_.Line.Substring(1).Trim() } |
            Where-Object { $_.Length -gt 0 } |
            Select-Object -First 1
        if ($addedLine) {
            $snippet = $addedLine
            if ($snippet.Length -gt 45) { $snippet = $snippet.Substring(0, 45) + "..." }
            $hunkContext = $snippet
        }
    }

    if ($hunkContext) {
        return "${prefix}: update ${summary} - ${hunkContext}${churn}"
    }

    return "${prefix}: update ${summary}${churn}"
}

$RepoPath = $PSScriptRoot
if (-not (Test-Path (Join-Path $RepoPath '.git'))) {
    Write-Error "Not a git repository: $RepoPath"
    exit 1
}

Push-Location $RepoPath
try {
    $currentBranch = (git branch --show-current 2>$null)
    if ($currentBranch) { $currentBranch = $currentBranch.Trim() }
    if (-not $currentBranch) { $currentBranch = "main" }

    $hasOrigin = $false
    try {
        git remote get-url origin *> $null
        $hasOrigin = $true
    }
    catch {
        $hasOrigin = $false
    }

    Write-Status -Message "WinPilot Repository: $RepoPath"
    Write-Status -Message "Active Branch: $currentBranch"

    # 1. Pull latest changes if remote origin exists
    if ($hasOrigin) {
        Write-Status -Message "Pulling latest changes from origin/$currentBranch..."
        git pull --rebase --autostash origin $currentBranch
    }
    else {
        Write-Notice -Message "No 'origin' remote configured; skipping pull step."
    }

    if ($PullOnly) {
        Write-Success -Message "Pull complete. No commit was made because -PullOnly was set."
        exit 0
    }

    # 2. Run test verification unless skipped
    if (-not $SkipTests) {
        $pyExe = Join-Path $RepoPath ".venv\Scripts\python.exe"
        if (Test-Path $pyExe) {
            Write-Status -Message "Running test suite verification via pytest..."
            $testOutput = & $pyExe -m pytest -q 2>&1
            if ($LASTEXITCODE -ne 0) {
                Write-Error "Test suite verification failed. Commit aborted to prevent pushing broken code:`n$testOutput"
                exit 1
            }
            Write-Success -Message "Test suite passed cleanly."
        }
    }

    # 3. Stage changes
    Write-Status -Message "Staging changes..."
    git add -A

    git diff --cached --quiet 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Success -Message "Working directory clean. Nothing to commit."
        exit 0
    }

    # 4. Secret detection scan
    $secretHits = Find-StagedSecrets
    if (@($secretHits).Count -gt 0) {
        Write-Error "Possible secrets or credentials detected in staged changes! Commit aborted."
        foreach ($hit in @($secretHits)) {
            Write-Host "    Pattern: $($hit.Pattern)" -ForegroundColor Yellow
            Write-Host "    Line   : $($hit.Snippet)..." -ForegroundColor Gray
        }
        Write-Notice -Message "Unstage or remove the secrets before re-running sync."
        git reset
        exit 1
    }

    # 5. Commit message determination
    if (-not $Message) {
        $Message = Get-AutoCommitMessage
        if ($Message) {
            Write-Notice -Message "Auto-generated commit message: '$Message'"
        }
    }

    if ($Message) {
        Write-Status -Message "Committing: '$Message'..."
        git commit -m "$Message"

        # 6. Push to remote
        if ($hasOrigin -and -not $NoPush) {
            Write-Status -Message "Pushing to origin/$currentBranch..."
            git push origin $currentBranch
            if ($LASTEXITCODE -ne 0) {
                Write-Notice -Message "Push rejected. Pulling with rebase and retrying push..."
                git pull --rebase --autostash origin $currentBranch
                git push origin $currentBranch
            }
        }
        elseif ($NoPush) {
            Write-Notice -Message "Commit created locally; push skipped due to -NoPush."
        }
        else {
            Write-Notice -Message "Commit created locally, but no 'origin' remote is configured."
        }

        Write-Success -Message "WinPilot repository synced successfully."
    }
    else {
        Write-Success -Message "No changes to commit."
    }
}
finally {
    Pop-Location
}
