#!/usr/bin/env pwsh
$input_json = $Input | Out-String
$data = $input_json | ConvertFrom-Json

$Model = $data.model.display_name
$Dir = $data.workspace.current_dir
$Pct = [math]::Floor([double]($data.context_window.used_percentage))

# ANSI colour codes
$Cyan = "`e[36m"; $Green = "`e[32m"; $Yellow = "`e[33m"; $Red = "`e[31m"; $Reset = "`e[0m"
$Dim = "`e[2m"; $Magenta = "`e[35m"; $LtBlue = "`e[38;5;117m"

# Pick bar colour based on context usage
if ($Pct -ge 90) { $BarColor = $Red }
elseif ($Pct -ge 70) { $BarColor = $Yellow }
else { $BarColor = $Green }

$Filled = [math]::Floor($Pct / 10)
$Empty = 10 - $Filled
$Bar = ("█" * $Filled) + ("░" * $Empty)

# Git branch
$Branch = ""
try {
    git rev-parse --git-dir 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $BranchName = git branch --show-current 2>$null
        if ($BranchName) { $Branch = "${LtBlue}⎇ ${BranchName}${Reset}" }
    }
} catch {}

# ── Account usage limits (5h + 7d) ──────────────────────────────────────────
# Cache for 2 minutes to avoid hammering the API on every statusline refresh
$CacheFile = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), "claude-usage-cache.json")
$CacheTTL = 120

function Get-OAuthToken {
    # Linux / cross-platform: credentials in plain text file
    $CredsPath = Join-Path $HOME ".claude/.credentials.json"
    if (Test-Path $CredsPath) {
        $creds = Get-Content $CredsPath -Raw | ConvertFrom-Json
        if ($creds.claudeAiOauth.accessToken) { return $creds.claudeAiOauth.accessToken }
    }
    # Windows: credentials in Credential Manager
    try {
        $credTarget = "Claude Code-credentials"
        Add-Type -AssemblyName System.Security 2>$null
        # Use cmdkey / CredRead via PowerShell module if available
        if (Get-Command Get-StoredCredential -ErrorAction SilentlyContinue) {
            $stored = Get-StoredCredential -Target $credTarget
            if ($stored) {
                $json = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto(
                    [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($stored.Password))
                $obj = $json | ConvertFrom-Json
                if ($obj.claudeAiOauth.accessToken) { return $obj.claudeAiOauth.accessToken }
            }
        }
    } catch {}
    # macOS: Keychain
    if (Get-Command security -ErrorAction SilentlyContinue) {
        try {
            $raw = security find-generic-password -s "Claude Code-credentials" -w 2>$null
            if ($raw) {
                $obj = $raw | ConvertFrom-Json
                if ($obj.claudeAiOauth.accessToken) { return $obj.claudeAiOauth.accessToken }
            }
        } catch {}
    }
    return $null
}

function Fetch-Usage {
    param([string]$Token)
    try {
        $headers = @{
            "Authorization"  = "Bearer $Token"
            "anthropic-beta" = "oauth-2025-04-20"
            "Content-Type"   = "application/json"
        }
        $resp = Invoke-RestMethod -Uri "https://api.anthropic.com/api/oauth/usage" `
            -Headers $headers -Method Get -TimeoutSec 4 -ErrorAction Stop
        return $resp
    } catch { return $null }
}

function Get-UsageColor {
    param([int]$pct)
    if ($pct -ge 90) { return $Red }
    elseif ($pct -ge 70) { return $Yellow }
    else { return $Green }
}

function Format-Reset {
    param([string]$iso)
    if (-not $iso) { return "" }
    try {
        $resetTime = [DateTime]::Parse($iso).ToUniversalTime()
        $now = [DateTime]::UtcNow
        $diff = $resetTime - $now
        if ($diff.TotalSeconds -le 0) { return "now" }
        if ($diff.Days -gt 0) {
            return "{0}:{1:D2}:{2:D2}" -f $diff.Days, $diff.Hours, $diff.Minutes
        } else {
            return "{0}:{1:D2}" -f $diff.Hours, $diff.Minutes
        }
    } catch { return "" }
}

$UsageSegment = ""

# Use cache if fresh, otherwise fetch
$CacheAge = $CacheTTL + 1
if (Test-Path $CacheFile) {
    $CacheAge = ([DateTime]::UtcNow - (Get-Item $CacheFile).LastWriteTimeUtc).TotalSeconds
}

if ($CacheAge -gt $CacheTTL) {
    $Token = Get-OAuthToken
    if ($Token) {
        $resp = Fetch-Usage -Token $Token
        if ($resp -and $resp.five_hour) {
            $resp | ConvertTo-Json -Depth 10 | Set-Content $CacheFile -Encoding UTF8
        }
    }
}

if (Test-Path $CacheFile) {
    $cache = Get-Content $CacheFile -Raw | ConvertFrom-Json
    $FiveHRaw = $cache.five_hour.utilization
    $SevenDRaw = $cache.seven_day.utilization
    $FiveHReset = $cache.five_hour.resets_at
    $SevenDReset = $cache.seven_day.resets_at

    if ($null -ne $FiveHRaw -and $null -ne $SevenDRaw) {
        $FiveHPct = [math]::Floor([double]$FiveHRaw)
        $SevenDPct = [math]::Floor([double]$SevenDRaw)

        $FiveHColor = Get-UsageColor -pct $FiveHPct
        $SevenDColor = Get-UsageColor -pct $SevenDPct

        $FiveHEta = Format-Reset -iso $FiveHReset
        $SevenDEta = Format-Reset -iso $SevenDReset

        $FiveHEtaStr = ""
        if ($FiveHEta) { $FiveHEtaStr = "${Dim}~${FiveHEta}${Reset}" }
        $SevenDEtaStr = ""
        if ($SevenDEta) { $SevenDEtaStr = "${Dim}~${SevenDEta}${Reset}" }

        $UsageSegment = " | ${Magenta}5h:${Reset}${FiveHColor}${FiveHPct}%${Reset}${FiveHEtaStr} ${Magenta}7d:${Reset}${SevenDColor}${SevenDPct}%${Reset}${SevenDEtaStr}"
    }
}

$DirName = Split-Path $Dir -Leaf
Write-Host -NoNewline "${Cyan}[${Model}]${Reset} ${DirName} ${Branch} | ${BarColor}${Bar}${Reset} ${Pct}%${UsageSegment}"
