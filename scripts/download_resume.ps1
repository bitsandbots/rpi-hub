# Resume remaining rpi-hub downloads (after initial timeout)
param(
    [string]$Dest = "E:\rpi-hub-payload"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$DEST_ZIMS   = Join-Path $Dest "var\lib\kiwix"
$DEST_MODELS = Join-Path $Dest "var\lib\rpi-hub\models"
$DEST_FONTS  = Join-Path $Dest "var\www\rpi-hub-portal\assets\fonts"

foreach ($d in @($DEST_ZIMS, $DEST_MODELS, $DEST_FONTS)) {
    New-Item -ItemType Directory -Path $d -Force | Out-Null
}

function Write-Log($msg) {
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $msg"
}

function Get-Sha256($path) {
    if (-not (Test-Path $path)) { return "" }
    $hash = certutil -hashfile $path SHA256 | Select-Object -Index 1
    return $hash.Trim().ToLower()
}

# ============================================================
# Verify already-completed ZIMs
# ============================================================
$zims = @(
    @{name="wikipedia_en_simple_all_nopic.zim"; sha256="503b74027d101ec13b272f1ebbd23473e1d260be71a35a71141dfc985fd20d0a"},
    @{name="zimgit-post-disaster_en.zim"; sha256="0ba9bb358b768b94eb0d7920752fe356bf097de514ee61843f3a4da6cce174f8"},
    @{name="zimgit-water_en.zim"; sha256="392c7bc970a44fddd61dd17f6eabf1f4e21936f2d5c27c83093e1dc475cb56b6"},
    @{name="zimgit-food-preparation_en.zim"; sha256="db92c6c9dac14ff30f1cbc15aa834a7c012c6e87d4ff0519f33a0902ab6e732b"},
    @{name="zimgit-knots_en.zim"; sha256="7c3120b19fc2dc190b5ebfee01af54150136643d7b9d29d7fa9a6ba29787a57b"},
    @{name="ifixit_en_all.zim"; sha256="9bb5f3408707fd0300c6ef47a425c3217187f144cd9154a928183816aa72eead"},
    @{name="wiktionary_en_all_nopic.zim"; sha256="0f08b3faf89542dd336f4efb47d290460b54b711bd8b103f0de5c0902743e2b3"},
    @{name="wikem_en_all_maxi.zim"; sha256="d28e41a2c2a7d8946564c009dca38bb213f0b112118b362b26755c50dc58d770"},
    @{name="zimgit-medicine_en.zim"; sha256="a86c31b93e9800aae2cd812ef18cbf9c087a7537784c62fbc259db7f9f9d18c0"},
    @{name="wikipedia_en_all_nopic.zim"; sha256="441a56d9e05b2d98f8ae9acb7986a513ed47904d73852c92dc6b7d50baa122e5"}
)

Write-Log "========== Verifying completed ZIMs =========="
$bad = @()
foreach ($z in $zims) {
    $outFile = Join-Path $DEST_ZIMS $z.name
    if (Test-Path $outFile) {
        $actual = Get-Sha256 $outFile
        if ($actual -eq $z.sha256) {
            Write-Log "OK    $($z.name)"
        } else {
            Write-Log "BAD   $($z.name) — hash mismatch"
            $bad += $z.name
        }
    } else {
        Write-Log "MISS  $($z.name)"
        $bad += $z.name
    }
}
if ($bad.Count -gt 0) {
    Write-Host "WARNING: $($bad.Count) ZIMs need re-download: $($bad -join ', ')" -ForegroundColor Yellow
}

# ============================================================
# Resume Gutenberg (206 GB) — curl -C - for native resume
# ============================================================
Write-Log "========== Gutenberg (206 GB) =========="
$gutPath = Join-Path $DEST_ZIMS "gutenberg_en_all.zim"
$gutPartial = "$gutPath.partial"
$gutUrl = "https://download.kiwix.org/zim/gutenberg/gutenberg_en_all_2025-11.zim"
$gutHash = "01677c8d554a1cab2cbfd020ac99ebca7dd6c74d3ce0d13f266a2ba603dfaf28"

if (Test-Path $gutPath) {
    $actual = Get-Sha256 $gutPath
    if ($actual -eq $gutHash) {
        Write-Log "OK    gutenberg_en_all.zim (already complete)"
    } else {
        Write-Log "BAD   gutenberg_en_all.zim — hash mismatch, refetching"
        Remove-Item $gutPath -Force
        Remove-Item $gutPartial -Force -ErrorAction SilentlyContinue
    }
}

if (-not (Test-Path $gutPath)) {
    if (Test-Path $gutPartial) {
        Write-Log "resuming from $([math]::Round((Get-Item $gutPartial).Length / 1GB, 1)) GB"
    }
    Write-Log "get    gutenberg_en_all.zim (~206 GB — this will take hours)"
    $env:ProgressPreference = "Continue"
    curl --fail --location --retry 5 --retry-delay 10 --retry-all-errors `
        -C - --progress-bar -o $gutPartial $gutUrl
    $env:ProgressPreference = "SilentlyContinue"

    $actual = Get-Sha256 $gutPartial
    if ($actual -eq $gutHash) {
        Move-Item -Force $gutPartial $gutPath
        Write-Log "OK    gutenberg_en_all.zim"
    } else {
        Write-Host "FAIL  gutenberg_en_all.zim — SHA256 mismatch" -ForegroundColor Red
    }
}

# ============================================================
# Models
# ============================================================
Write-Log "========== Model Downloads =========="
$models = @(
    @{name="qwen2.5-1.5b-instruct-q4_k_m.gguf"; url="https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf"; sha256="6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e"},
    @{name="bge-small-en-v1.5-q8_0.gguf"; url="https://huggingface.co/CompendiumLabs/bge-small-en-v1.5-gguf/resolve/main/bge-small-en-v1.5-q8_0.gguf"; sha256="ec38e8da142596baa913124ae50550de284b6916bf59577ef2f0cb9660c2f514"}
)

foreach ($m in $models) {
    $outFile = Join-Path $DEST_MODELS $m.name
    if (Test-Path $outFile) {
        $actual = Get-Sha256 $outFile
        if ($actual -eq $m.sha256) {
            Write-Log "cached $($m.name)"
            continue
        }
        Write-Log "stale  $($m.name) — refetching"
        Remove-Item $outFile -Force
    }
    $partial = "$outFile.partial"
    Write-Log "get    $($m.name)"
    curl --fail --location --retry 5 --retry-delay 10 --retry-all-errors `
        -C - --progress-bar -o $partial $m.url
    $actual = Get-Sha256 $partial
    if ($actual -eq $m.sha256) {
        Move-Item -Force $partial $outFile
        Write-Log "OK    $($m.name)"
    } else {
        Remove-Item $partial -Force
        Write-Host "FAIL  $($m.name) — SHA256 mismatch" -ForegroundColor Red
    }
}

# ============================================================
# Fonts
# ============================================================
Write-Log "========== Font Downloads =========="
$FONTSOURCE_VER = "5"
$fonts = @(
    @{name="exo2-700.woff2"; url="https://cdn.jsdelivr.net/npm/@fontsource/exo-2@$FONTSOURCE_VER/files/exo-2-latin-700-normal.woff2"},
    @{name="jakarta-400.woff2"; url="https://cdn.jsdelivr.net/npm/@fontsource/plus-jakarta-sans@$FONTSOURCE_VER/files/plus-jakarta-sans-latin-400-normal.woff2"},
    @{name="jakarta-700.woff2"; url="https://cdn.jsdelivr.net/npm/@fontsource/plus-jakarta-sans@$FONTSOURCE_VER/files/plus-jakarta-sans-latin-700-normal.woff2"},
    @{name="plexmono-400.woff2"; url="https://cdn.jsdelivr.net/npm/@fontsource/ibm-plex-mono@$FONTSOURCE_VER/files/ibm-plex-mono-latin-400-normal.woff2"}
)

foreach ($f in $fonts) {
    $outFile = Join-Path $DEST_FONTS $f.name
    if (Test-Path $outFile) {
        Write-Log "cached $($f.name)"
        continue
    }
    Write-Log "get    $($f.name)"
    curl --fail --location --silent --show-error --connect-timeout 10 --max-time 60 `
        -o $outFile $f.url
    Write-Log "OK    $($f.name)"
}

# OFL license
$ofl = Join-Path $DEST_FONTS "OFL.txt"
if (-not (Test-Path $ofl)) {
    curl --fail --location --silent --show-error `
        -o $ofl "https://cdn.jsdelivr.net/npm/@fontsource/exo-2@$FONTSOURCE_VER/LICENSE"
    Write-Log "OK    OFL.txt"
}

# ============================================================
# Summary
# ============================================================
Write-Log ""
Write-Log "========== FINAL SUMMARY =========="
$zims = Get-ChildItem -LiteralPath $DEST_ZIMS -Filter "*.zim" -ErrorAction SilentlyContinue
$totalZimGB = [math]::Round(($zims | Measure-Object -Property Length -Sum).Sum / 1GB, 1)
Write-Log "ZIMs: $($zims.Count) files, $totalZimGB GB"
foreach ($z in $zims | Sort-Object Name) {
    Write-Log "  $($z.Name) — $([math]::Round($z.Length/1GB,1)) GB"
}

$modelFiles = Get-ChildItem -LiteralPath $DEST_MODELS -ErrorAction SilentlyContinue
if ($modelFiles) {
    Write-Log "Models: $($modelFiles.Count) files"
    foreach ($m in $modelFiles) { Write-Log "  $($m.Name) — $([math]::Round($m.Length/1GB,2)) GB" }
} else {
    Write-Log "Models: none"
}

$fontFiles = Get-ChildItem -LiteralPath $DEST_FONTS -ErrorAction SilentlyContinue
if ($fontFiles) {
    Write-Log "Fonts: $($fontFiles.Count) files"
} else {
    Write-Log "Fonts: none"
}
Write-Log "Destination: $Dest"
