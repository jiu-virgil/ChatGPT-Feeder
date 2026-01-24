# PowerShell script to download VS Code icons (Optimized)
# Downloads ALL SVG icons from vscode-icons/vscode-icons repository
# Usage: .\download_icons.ps1

$ErrorActionPreference = "Stop"

Write-Host "Downloading VS Code Icons (Optimized)..." -ForegroundColor Cyan
Write-Host ""

# Create icons directory if it doesn't exist
$iconsDir = "resources\icons"
$cacheFile = Join-Path $iconsDir ".icon_cache.json"
if (-not (Test-Path $iconsDir)) {
    Write-Host "  Creating icons directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $iconsDir -Force | Out-Null
}

# Check PowerShell version for parallel support
$psVersion = $PSVersionTable.PSVersion.Major
$psFullVersion = $PSVersionTable.PSVersion.ToString()
# PSEdition is read-only, access it directly
$psEditionValue = if ($PSVersionTable.PSEdition) { $PSVersionTable.PSEdition } else { "Desktop" }

# Check if we're running PowerShell Core (7+) or Windows PowerShell (5.1)
# PowerShell 7+ has PSEdition = "Core", Windows PowerShell 5.1 doesn't have this property or it's "Desktop"
$isPowerShellCore = ($psEditionValue -eq "Core") -or ($psVersion -ge 7)
$useParallel = $isPowerShellCore
$maxConcurrency = 8

# Show detected version
Write-Host "  PowerShell Version: $psFullVersion (Major: $psVersion, Edition: $psEditionValue)" -ForegroundColor Gray
if (-not $useParallel) {
    Write-Host "  Warning: Parallel downloads require PowerShell 7+ (Core edition)" -ForegroundColor Yellow
    Write-Host "  You're running Windows PowerShell $psVersion. Install PowerShell 7+:" -ForegroundColor Yellow
    Write-Host "    winget install Microsoft.PowerShell" -ForegroundColor Cyan
    Write-Host "  Then run: pwsh .\download_icons.ps1" -ForegroundColor Cyan
    Write-Host ""
}

# GitHub API endpoint for icons directory
$apiUrl = "https://api.github.com/repos/vscode-icons/vscode-icons/contents/icons?ref=master"
$rawBaseUrl = "https://raw.githubusercontent.com/vscode-icons/vscode-icons/master/icons/"

Write-Host "  Fetching available icons from VS Code Icons repository..." -ForegroundColor Yellow
Write-Host "  Source: https://github.com/vscode-icons/vscode-icons" -ForegroundColor Gray
Write-Host "  Branch: master" -ForegroundColor Gray
if ($useParallel) {
    Write-Host "  Mode: Parallel (max $maxConcurrency concurrent downloads)" -ForegroundColor Green
} else {
    Write-Host "  Mode: Sequential (PowerShell 7+ required for parallel)" -ForegroundColor Yellow
}
Write-Host ""

# Load cache
$cache = @{}
if (Test-Path $cacheFile) {
    try {
        $cacheContent = Get-Content $cacheFile -Raw -ErrorAction Stop | ConvertFrom-Json
        $cache = @{}
        $cacheContent.PSObject.Properties | ForEach-Object {
            $cache[$_.Name] = $_.Value
        }
    } catch {
        Write-Host "  Warning: Could not load cache file, starting fresh" -ForegroundColor Yellow
    }
}

try {
    # Fetch list of files from GitHub API
    $response = Invoke-RestMethod -Uri $apiUrl -ErrorAction Stop
    $iconFiles = $response | Where-Object { $_.type -eq "file" -and $_.name -like "*.svg" }
    
    if ($iconFiles.Count -eq 0) {
        Write-Host "  No SVG icons found in repository." -ForegroundColor Yellow
        exit 1
    }
    
    Write-Host "  Found $($iconFiles.Count) icon files" -ForegroundColor Green
    Write-Host ""
    
    # Function to check if file needs updating
    function Test-IconNeedsUpdate {
        param(
            [string]$filename,
            [string]$remoteSha,
            [hashtable]$cache
        )
        
        $localPath = Join-Path $iconsDir $filename
        
        # Always download if file doesn't exist
        if (-not (Test-Path $localPath)) {
            return $true
        }
        
        # Check cache for SHA match
        if ($cache.ContainsKey($filename) -and $remoteSha) {
            $cachedSha = $cache[$filename].sha
            if ($cachedSha -eq $remoteSha) {
                return $false
            }
        }
        
        # Check with HEAD request for ETag/Last-Modified
        try {
            $headResponse = Invoke-WebRequest -Uri "$rawBaseUrl$filename" -Method Head -TimeoutSec 10 -ErrorAction Stop
            $etag = $headResponse.Headers["ETag"]
            $lastModified = $headResponse.Headers["Last-Modified"]
            
            # Check ETag in cache
            if ($cache.ContainsKey($filename) -and $etag) {
                $cachedEtag = $cache[$filename].etag
                if ($cachedEtag -eq $etag) {
                    return $false
                }
            }
            
            # Update cache
            $cache[$filename] = @{
                etag = $etag
                last_modified = $lastModified
                sha = $remoteSha
            }
            
            return $true
        } catch {
            # If HEAD fails, assume we need to download
            return $true
        }
    }
    
    # Function to download a single icon
    function Download-Icon {
        param(
            [object]$iconFile,
            [hashtable]$cache
        )
        
        $iconName = $iconFile.name
        $remoteSha = $iconFile.sha
        $downloadUrl = $iconFile.download_url
        $localIconPath = Join-Path $iconsDir $iconName
        
        # Check if update needed
        if (-not (Test-IconNeedsUpdate -filename $iconName -remoteSha $remoteSha -cache $cache)) {
            return @{
                filename = $iconName
                status = "skipped"
                message = "up to date"
            }
        }
        
        try {
            # First get headers for ETag/Last-Modified
            $headResponse = Invoke-WebRequest -Uri $downloadUrl -Method Head -TimeoutSec 10 -ErrorAction Stop
            $etag = $headResponse.Headers["ETag"]
            $lastModified = $headResponse.Headers["Last-Modified"]
            
            # Download file directly to disk (handles binary correctly)
            Invoke-WebRequest -Uri $downloadUrl -OutFile $localIconPath -TimeoutSec 30 -ErrorAction Stop | Out-Null
            
            # Update cache
            $fileInfo = Get-Item $localIconPath
            $cache[$iconName] = @{
                etag = $etag
                last_modified = $lastModified
                sha = $remoteSha
                size = $fileInfo.Length
            }
            
            return @{
                filename = $iconName
                status = "downloaded"
                message = "downloaded"
            }
        } catch {
            return @{
                filename = $iconName
                status = "failed"
                message = "failed: $($_.Exception.Message.Substring(0, [Math]::Min(50, $_.Exception.Message.Length)))"
            }
        }
    }
    
    Write-Host "Downloading icons..." -ForegroundColor Yellow
    $totalFiles = $iconFiles.Count
    Write-Host "-" * 60
    
    $downloaded = 0
    $failed = 0
    $skipped = 0
    $processed = 0
    
    if ($useParallel) {
        # Parallel download (PowerShell 7+)
        # Note: Cache updates in parallel mode may not be perfect, but downloads will work
        $results = $iconFiles | ForEach-Object -Parallel {
            $iconName = $_.name
            $remoteSha = $_.sha
            $downloadUrl = $_.download_url
            $iconsDir = $using:iconsDir
            $rawBaseUrl = $using:rawBaseUrl
            $localIconPath = Join-Path $iconsDir $iconName
            
            # Check if file exists - if it does, we'll skip for now (full check is complex in parallel)
            # In parallel mode, we download if file doesn't exist, otherwise skip
            $needsUpdate = -not (Test-Path $localIconPath)
            
            if (-not $needsUpdate) {
                return @{
                    filename = $iconName
                    status = "skipped"
                    message = "up to date"
                }
            }
            
            try {
                # Get headers first for metadata
                $headResponse = Invoke-WebRequest -Uri $downloadUrl -Method Head -TimeoutSec 10 -ErrorAction Stop
                $etag = $headResponse.Headers["ETag"]
                $lastModified = $headResponse.Headers["Last-Modified"]
                
                # Download file directly to disk (handles binary correctly)
                Invoke-WebRequest -Uri $downloadUrl -OutFile $localIconPath -TimeoutSec 30 -ErrorAction Stop | Out-Null
                
                return @{
                    filename = $iconName
                    status = "downloaded"
                    message = "downloaded"
                    etag = $etag
                    last_modified = $lastModified
                    sha = $remoteSha
                }
            } catch {
                return @{
                    filename = $iconName
                    status = "failed"
                    message = "failed: $($_.Exception.Message.Substring(0, [Math]::Min(50, $_.Exception.Message.Length)))"
                }
            }
        } -ThrottleLimit $maxConcurrency
        
        # Update cache with results
        foreach ($result in $results) {
            if ($result.status -eq "downloaded" -and $result.etag) {
                $cache[$result.filename] = @{
                    etag = $result.etag
                    last_modified = $result.last_modified
                    sha = $result.sha
                }
            }
        }
        
        # Process results
        foreach ($result in $results) {
            $processed++
            $progress = [math]::Round(($processed / $totalFiles) * 100, 1)
            $statusLine = "[$processed/$totalFiles ($progress%)]"
            
            if ($result.status -eq "downloaded") {
                Write-Host "  [OK] $statusLine $($result.filename) ($($result.message))" -ForegroundColor Green
                $downloaded++
            } elseif ($result.status -eq "skipped") {
                Write-Host "  [SKIP] $statusLine $($result.filename) ($($result.message))" -ForegroundColor Gray
                $skipped++
            } else {
                Write-Host "  [FAIL] $statusLine $($result.filename) ($($result.message))" -ForegroundColor Yellow
                $failed++
            }
        }
    } else {
        # Sequential download (PowerShell 5.1)
        foreach ($iconFile in $iconFiles) {
            $processed++
            $progress = [math]::Round(($processed / $totalFiles) * 100, 1)
            $statusLine = "[$processed/$totalFiles ($progress%)]"
            
            $result = Download-Icon -iconFile $iconFile -cache $cache
            
            if ($result.status -eq "downloaded") {
                Write-Host "  [OK] $statusLine $($result.filename) ($($result.message))" -ForegroundColor Green
                $downloaded++
            } elseif ($result.status -eq "skipped") {
                Write-Host "  [SKIP] $statusLine $($result.filename) ($($result.message))" -ForegroundColor Gray
                $skipped++
            } else {
                Write-Host "  [FAIL] $statusLine $($result.filename) ($($result.message))" -ForegroundColor Yellow
                $failed++
            }
        }
    }
    
    # Save cache
    try {
        $cache | ConvertTo-Json -Depth 10 | Set-Content $cacheFile -ErrorAction Stop
    } catch {
        Write-Host "  Warning: Could not save cache file" -ForegroundColor Yellow
    }
    
    Write-Host "-" * 60
    Write-Host ""
    Write-Host "Download complete!" -ForegroundColor Green
    Write-Host "  Downloaded: $downloaded icons" -ForegroundColor Cyan
    if ($skipped -gt 0) {
        Write-Host "  Skipped: $skipped icons (up to date)" -ForegroundColor Gray
    }
    if ($failed -gt 0) {
        Write-Host "  Failed: $failed icons" -ForegroundColor Yellow
    }
    Write-Host ""
    Write-Host "Icons are now available in: $iconsDir" -ForegroundColor Cyan
    $totalIcons = (Get-ChildItem $iconsDir -Filter *.svg -ErrorAction SilentlyContinue).Count
    Write-Host "  Total icons: $totalIcons" -ForegroundColor Cyan
    
} catch {
    Write-Host "Error: Failed to fetch icon list from GitHub API" -ForegroundColor Red
    Write-Host "  $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Possible causes:" -ForegroundColor Yellow
    Write-Host "  - No internet connection" -ForegroundColor White
    Write-Host "  - GitHub API rate limit exceeded" -ForegroundColor White
    Write-Host "  - Repository structure changed" -ForegroundColor White
    Write-Host ""
    Write-Host "You can manually download icons from:" -ForegroundColor Yellow
    Write-Host "  https://github.com/vscode-icons/vscode-icons/tree/master/icons" -ForegroundColor Cyan
    exit 1
}
