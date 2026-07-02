# Download full rpi-hub content set (PowerShell — Windows workstation)
# Usage: .\scripts\download_full.ps1 [-Dest E:\rpi-hub-payload]
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
    $ts = Get-Date -Format "HH:mm:ss"
    Write-Host "[$ts] $msg"
}

function Get-Sha256($path) {
    $hash = certutil -hashfile $path SHA256 | Select-Object -Index 1
    return $hash.Trim().ToLower()
}

function Invoke-Fetch($url, $outPath, $label) {
    $partial = "$outPath.partial"
    $resumeFrom = 0
    if (Test-Path $partial) {
        $resumeFrom = (Get-Item $partial).Length
        Write-Log "resuming $label at $resumeFrom bytes"
    }
    $headers = @{}
    if ($resumeFrom -gt 0) {
        $headers["Range"] = "bytes=$resumeFrom-"
    }

    $tempFile = "$partial.new"
    try {
        curl --fail --location --retry 5 --retry-delay 5 --progress-bar `
            -o $tempFile $url
        if ($resumeFrom -gt 0 -and (Test-Path $partial)) {
            $existing = Get-Content -Raw -Encoding Byte $partial
            $new = Get-Content -Raw -Encoding Byte $tempFile
            $combined = $existing + $new
            [System.IO.File]::WriteAllBytes($partial, $combined)
            Remove-Item $tempFile
        } else {
            Move-Item -Force $tempFile $partial
        }
    } catch {
        if (Test-Path $tempFile) { Remove-Item $tempFile }
        throw
    }
    return $partial
}

# ============================================================
# 1. ZIMs — Full tier (all entries from content/manifest.yaml)
# ============================================================
Write-Log "========== ZIM Downloads (full tier) =========="

$zims = @(
    # minimal
    @{name="wikipedia_en_simple_all_nopic.zim"; url="https://download.kiwix.org/zim/wikipedia/wikipedia_en_simple_all_nopic_2026-05.zim"; sha256="503b74027d101ec13b272f1ebbd23473e1d260be71a35a71141dfc985fd20d0a"; size="937 MB"; tier="minimal"},
    @{name="zimgit-post-disaster_en.zim"; url="https://download.kiwix.org/zim/other/zimgit-post-disaster_en_2024-05.zim"; sha256="0ba9bb358b768b94eb0d7920752fe356bf097de514ee61843f3a4da6cce174f8"; size="615 MB"; tier="minimal"},
    @{name="zimgit-water_en.zim"; url="https://download.kiwix.org/zim/other/zimgit-water_en_2024-08.zim"; sha256="392c7bc970a44fddd61dd17f6eabf1f4e21936f2d5c27c83093e1dc475cb56b6"; size="20 MB"; tier="minimal"},
    @{name="zimgit-food-preparation_en.zim"; url="https://download.kiwix.org/zim/other/zimgit-food-preparation_en_2025-04.zim"; sha256="db92c6c9dac14ff30f1cbc15aa834a7c012c6e87d4ff0519f33a0902ab6e732b"; size="93 MB"; tier="minimal"},
    @{name="zimgit-knots_en.zim"; url="https://download.kiwix.org/zim/other/zimgit-knots_en_2024-08.zim"; sha256="7c3120b19fc2dc190b5ebfee01af54150136643d7b9d29d7fa9a6ba29787a57b"; size="27 MB"; tier="minimal"},
    @{name="ifixit_en_all.zim"; url="https://download.kiwix.org/zim/ifixit/ifixit_en_all_2025-12.zim"; sha256="9bb5f3408707fd0300c6ef47a425c3217187f144cd9154a928183816aa72eead"; size="3.4 GB"; tier="minimal"},
    # core
    @{name="wiktionary_en_all_nopic.zim"; url="https://download.kiwix.org/zim/wiktionary/wiktionary_en_all_nopic_2026-05.zim"; sha256="0f08b3faf89542dd336f4efb47d290460b54b711bd8b103f0de5c0902743e2b3"; size="8.7 GB"; tier="core"},
    @{name="wikem_en_all_maxi.zim"; url="https://download.kiwix.org/zim/other/wikem_en_all_maxi_2026-04.zim"; sha256="d28e41a2c2a7d8946564c009dca38bb213f0b112118b362b26755c50dc58d770"; size="46 MB"; tier="core"},
    @{name="zimgit-medicine_en.zim"; url="https://download.kiwix.org/zim/other/zimgit-medicine_en_2024-08.zim"; sha256="a86c31b93e9800aae2cd812ef18cbf9c087a7537784c62fbc259db7f9f9d18c0"; size="67 MB"; tier="core"},
    # full
    @{name="wikipedia_en_all_nopic.zim"; url="https://download.kiwix.org/zim/wikipedia/wikipedia_en_all_nopic_2026-06.zim"; sha256="441a56d9e05b2d98f8ae9acb7986a513ed47904d73852c92dc6b7d50baa122e5"; size="50 GB"; tier="full"},
    @{name="gutenberg_en_all.zim"; url="https://download.kiwix.org/zim/gutenberg/gutenberg_en_all_2025-11.zim"; sha256="01677c8d554a1cab2cbfd020ac99ebca7dd6c74d3ce0d13f266a2ba603dfaf28"; size="206 GB"; tier="full"}
)

$fetched = 0
$skipped = 0
$failed = @()

foreach ($z in $zims) {
    $outFile = Join-Path $DEST_ZIMS $z.name

    if (Test-Path $outFile) {
        $actual = Get-Sha256 $outFile
        if ($actual -eq $z.sha256) {
            Write-Log "cached $($z.name) ($($z.size))"
            $skipped++
            continue
        }
        Write-Log "stale  $($z.name) — hash mismatch, refetching"
        Remove-Item $outFile -Force
    }

    Write-Log "get    $($z.name) [$($z.tier)] — $($z.size)"
    Write-Log "       $($z.url)"
    try {
        $partial = Invoke-Fetch -url $z.url -outPath $outFile -label $z.name
        $actual = Get-Sha256 $partial
        if ($actual -ne $z.sha256) {
            Remove-Item $partial -Force
            throw "SHA256 mismatch (got $actual, expected $($z.sha256))"
        }
        Move-Item -Force $partial $outFile
        Write-Log "ok     $($z.name)"
        $fetched++
    } catch {
        Write-Host "FAIL   $($z.name) — $_" -ForegroundColor Red
        $failed += $z.name
    }
}

# ============================================================
# 2. Model Weights
# ============================================================
Write-Log "========== Model Downloads =========="

$models = @(
    @{name="qwen2.5-1.5b-instruct-q4_k_m.gguf"; url="https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf"; sha256="6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e"; size="~1 GB"},
    @{name="bge-small-en-v1.5-q8_0.gguf"; url="https://huggingface.co/CompendiumLabs/bge-small-en-v1.5-gguf/resolve/main/bge-small-en-v1.5-q8_0.gguf"; sha256="ec38e8da142596baa913124ae50550de284b6916bf59577ef2f0cb9660c2f514"; size="~140 MB"}
)

foreach ($m in $models) {
    $outFile = Join-Path $DEST_MODELS $m.name

    if (Test-Path $outFile) {
        $actual = Get-Sha256 $outFile
        if ($actual -eq $m.sha256) {
            Write-Log "cached $($m.name)"
            $skipped++
            continue
        }
        Write-Log "stale  $($m.name) — refetching"
        Remove-Item $outFile -Force
    }

    Write-Log "get    $($m.name) ($($m.size))"
    try {
        $partial = Invoke-Fetch -url $m.url -outPath $outFile -label $m.name
        $actual = Get-Sha256 $partial
        if ($actual -ne $m.sha256) {
            Remove-Item $partial -Force
            throw "SHA256 mismatch"
        }
        Move-Item -Force $partial $outFile
        Write-Log "ok     $($m.name)"
        $fetched++
    } catch {
        Write-Host "FAIL   $($m.name) — $_" -ForegroundColor Red
        $failed += $m.name
    }
}

# ============================================================
# 3. Brand Fonts
# ============================================================
Write-Log "========== Font Downloads =========="

$FONTSOURCE_VER = "5"
$fonts = @{
    "exo2-700.woff2" = "https://cdn.jsdelivr.net/npm/@fontsource/exo-2@$FONTSOURCE_VER/files/exo-2-latin-700-normal.woff2"
    "jakarta-400.woff2" = "https://cdn.jsdelivr.net/npm/@fontsource/plus-jakarta-sans@$FONTSOURCE_VER/files/plus-jakarta-sans-latin-400-normal.woff2"
    "jakarta-700.woff2" = "https://cdn.jsdelivr.net/npm/@fontsource/plus-jakarta-sans@$FONTSOURCE_VER/files/plus-jakarta-sans-latin-700-normal.woff2"
    "plexmono-400.woff2" = "https://cdn.jsdelivr.net/npm/@fontsource/ibm-plex-mono@$FONTSOURCE_VER/files/ibm-plex-mono-latin-400-normal.woff2"
}

foreach ($name in $fonts.Keys) {
    $outFile = Join-Path $DEST_FONTS $name
    if (Test-Path $outFile) {
        Write-Log "cached $name"
        $skipped++
        continue
    }
    $url = $fonts[$name]
    Write-Log "get    $name"
    try {
        curl --fail --location --silent --show-error --connect-timeout 10 --max-time 60 `
            -o $outFile $url
        Write-Log "ok     $name"
        $fetched++
    } catch {
        Write-Host "FAIL   $name — $_" -ForegroundColor Red
        $failed += $name
    }
}

# OFL license
$oflLicense = Join-Path $DEST_FONTS "OFL.txt"
if (-not (Test-Path $oflLicense)) {
    try {
        curl --fail --location --silent --show-error `
            -o $oflLicense "https://cdn.jsdelivr.net/npm/@fontsource/exo-2@$FONTSOURCE_VER/LICENSE"
        Write-Log "ok     OFL.txt"
        $fetched++
    } catch {
        Write-Host "FAIL   OFL.txt — $_" -ForegroundColor Red
    }
}

# ============================================================
# Summary
# ============================================================
Write-Log ""
Write-Log "============================================"
Write-Log "DOWNLOAD COMPLETE"
Write-Log "  fetched: $fetched"
Write-Log "  skipped (cached): $skipped"
Write-Log "  failed: $($failed.Count)"
Write-Log "  destination: $Dest"
if ($failed.Count -gt 0) {
    Write-Log "  failed items: $($failed -join ', ')"
}
Write-Log ""
Write-Log "Next steps:"
Write-Log "  1. Build PDFs from pack HTML:  scripts\build_pack_pdfs.sh (requires bash/chromium)"
Write-Log "  2. Apply regional pack:        scripts\apply_pack.sh <pack-name>"
Write-Log "  3. Transfer to Pi:             rsync -avh $Dest/ pi@hub.local:/"
Write-Log "  4. Or bake image:              scripts\bake_image.sh"
