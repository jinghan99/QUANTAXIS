param(
    [switch]$Check,
    [switch]$PushFork,
    [ValidateSet('merge','ff-only')][string]$Mode = 'merge',
    [string]$UpstreamBranch = 'master'
)
$ErrorActionPreference = 'Stop'
$repo = $PSScriptRoot
$transcribing = $false

function Invoke-RepoGit {
    param([string[]]$GitArguments)
    & git -C $repo @GitArguments
    if ($LASTEXITCODE -ne 0) { throw ('git failed: ' + ($GitArguments -join ' ')) }
}

try {
    $repoRoot = & git -C $repo rev-parse --show-toplevel
    if ($LASTEXITCODE -ne 0 -or [IO.Path]::GetFullPath($repoRoot) -ne [IO.Path]::GetFullPath($repo)) {
        throw 'Run this script from the root of its own Git checkout.'
    }
    $branch = & git -C $repo symbolic-ref --quiet --short HEAD
    if ($LASTEXITCODE -ne 0) { throw 'Detached HEAD: switch to your working branch first.' }
    $origin = & git -C $repo remote get-url origin
    if ($LASTEXITCODE -ne 0) { throw 'origin remote is missing.' }
    $upstream = & git -C $repo remote get-url upstream
    if ($LASTEXITCODE -ne 0) { throw 'upstream remote is missing.' }
    $gitDir = & git -C $repo rev-parse --absolute-git-dir
    foreach ($state in @('MERGE_HEAD','CHERRY_PICK_HEAD','REVERT_HEAD','rebase-merge','rebase-apply')) {
        if (Test-Path -LiteralPath (Join-Path $gitDir $state)) {
            throw "An existing Git operation is in progress ($state). Finish or abort it yourself before updating."
        }
    }
    $dirty = @(& git -C $repo status --porcelain)
    Write-Host "Branch:   $branch"
    Write-Host "Fork:     $origin"
    Write-Host "Upstream: $upstream ($UpstreamBranch)"
    if ($Check) {
        Write-Host "Uncommitted/untracked entries: $($dirty.Count)"
        if ($dirty.Count) { Write-Host 'Commit or explicitly stash your work before updating.' }
        Write-Host 'Check only: no fetch, merge, or push performed.'
        exit 0
    }
    if ($dirty.Count) {
        $dirty | ForEach-Object { Write-Host $_ }
        throw 'Working tree is not clean. Commit or explicitly stash your changes, then run again. Nothing was reset or stashed automatically.'
    }
    $gitDir = & git -C $repo rev-parse --absolute-git-dir
    $logDir = Join-Path $gitDir 'upstream-update-logs'
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    $log = Join-Path $logDir ((Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '.log')
    Start-Transcript -LiteralPath $log | Out-Null
    $transcribing = $true
    Invoke-RepoGit -GitArguments @('fetch','upstream')
    $source = "refs/remotes/upstream/$UpstreamBranch"
    Invoke-RepoGit -GitArguments @('rev-parse','--verify',$source)
    if ($PushFork) {
        Invoke-RepoGit -GitArguments @('fetch','origin')
        & git -C $repo show-ref --verify --quiet "refs/remotes/origin/$UpstreamBranch"
        if ($LASTEXITCODE -eq 0) {
            & git -C $repo merge-base --is-ancestor "origin/$UpstreamBranch" $source
            if ($LASTEXITCODE -ne 0) { throw 'Fork branch has its own commits. Refusing to overwrite it; reconcile that branch manually.' }
        }
    }
    if ($Mode -eq 'ff-only') {
        & git -C $repo merge --ff-only $source
    } else {
        & git -C $repo merge --no-edit $source
    }
    if ($LASTEXITCODE -ne 0) {
        & git -C $repo rev-parse --quiet --verify MERGE_HEAD *> $null
        if ($LASTEXITCODE -eq 0) { Invoke-RepoGit -GitArguments @('merge','--abort') }
        throw 'Update could not be merged. Any merge started by this script was aborted; review the log and resolve the branch relationship manually.'
    }
    if ($PushFork) {
        Invoke-RepoGit -GitArguments @('push','origin',($source + ':refs/heads/' + $UpstreamBranch))
    }
    Invoke-RepoGit -GitArguments @('log','-1','--oneline')
    Write-Host "Updated current branch '$branch'. Log: $log"
    if (-not $PushFork) { Write-Host 'To also synchronize the fork master branch, run with -PushFork.' }
} catch {
    Write-Error $_ -ErrorAction Continue
    exit 1
} finally {
    if ($transcribing) { Stop-Transcript | Out-Null }
}
