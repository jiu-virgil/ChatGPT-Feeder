# PowerShell script to sign Windows executables with a self-signed certificate
# Creates certificate for Pazal Group SRL if it doesn't exist, then signs the executable
# Usage: .\sign_executable.ps1 <path-to-executable>
# Example: .\sign_executable.ps1 "dist\Spoon.exe"

param(
    [Parameter(Mandatory = $true)]
    [string]$ExecutablePath
)

$ErrorActionPreference = "Continue"

# Certificate configuration
$certFriendlyName = "Pazal Group SRL Code Signing"
$certSubject = "CN=Pazal Group SRL, O=Pazal Group SRL, L=Bucharest, C=RO"
$certStoreLocation = "Cert:\CurrentUser\My"

Write-Host "Signing executable..." -ForegroundColor Cyan
Write-Host "  Executable: $ExecutablePath" -ForegroundColor Gray
Write-Host ""

# Check if executable exists
if (-not (Test-Path $ExecutablePath)) {
    Write-Host "Error: Executable not found at: $ExecutablePath" -ForegroundColor Red
    exit 1
}

# Find signtool.exe
Write-Host "  Locating signtool.exe..." -ForegroundColor Yellow
$signtoolPath = $null

# Common Windows SDK locations
$sdkPaths = @(
    "${env:ProgramFiles(x86)}\Windows Kits\10\bin\*\x64\signtool.exe",
    "${env:ProgramFiles}\Windows Kits\10\bin\*\x64\signtool.exe"
)

foreach ($path in $sdkPaths) {
    $found = Get-ChildItem -Path $path -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | Select-Object -First 1
    if ($found) {
        $signtoolPath = $found.FullName
        break
    }
}

if (-not $signtoolPath) {
    Write-Host "  Warning: signtool.exe not found" -ForegroundColor Yellow
    Write-Host "  Code signing requires Windows SDK to be installed." -ForegroundColor White
    Write-Host "  Download: https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/" -ForegroundColor Gray
    Write-Host "  Executable will remain unsigned." -ForegroundColor Yellow
    exit 0
}

Write-Host "  Found signtool.exe: $signtoolPath" -ForegroundColor Green
Write-Host ""

# Check if certificate exists, create if not
Write-Host "  Checking for code signing certificate..." -ForegroundColor Yellow

$cert = $null
try {
    # Check if certificate store location is accessible
    if (-not (Test-Path $certStoreLocation)) {
        Write-Host "  Warning: Certificate store not accessible: $certStoreLocation" -ForegroundColor Yellow
        Write-Host "  Executable will remain unsigned." -ForegroundColor Yellow
        exit 0
    }
    
    # Try to find existing certificate
    $cert = Get-ChildItem -Path $certStoreLocation -ErrorAction Stop | Where-Object { $_.FriendlyName -eq $certFriendlyName } | Select-Object -First 1
}
catch {
    Write-Host "  Warning: Could not access certificate store" -ForegroundColor Yellow
    Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor White
    Write-Host "  Executable will remain unsigned." -ForegroundColor Yellow
    exit 0
}

if (-not $cert) {
    Write-Host "  Certificate not found, creating self-signed certificate..." -ForegroundColor Yellow
    
    try {
        # Create self-signed certificate valid for 5 years
        $cert = New-SelfSignedCertificate `
            -Type Custom `
            -Subject $certSubject `
            -KeyUsage DigitalSignature `
            -FriendlyName $certFriendlyName `
            -CertStoreLocation $certStoreLocation `
            -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3", "2.5.29.19={text}") `
            -NotAfter (Get-Date).AddYears(5) `
            -ErrorAction Stop
        
        Write-Host "  Certificate created successfully" -ForegroundColor Green
        Write-Host "  Thumbprint: $($cert.Thumbprint)" -ForegroundColor Gray
        Write-Host ""
    }
    catch {
        Write-Host "  Error: Failed to create certificate" -ForegroundColor Red
        Write-Host "  $($_.Exception.Message)" -ForegroundColor White
        Write-Host "  Executable will remain unsigned." -ForegroundColor Yellow
        exit 0
    }
}
else {
    Write-Host "  Found existing certificate" -ForegroundColor Green
    Write-Host "  Thumbprint: $($cert.Thumbprint)" -ForegroundColor Gray
    Write-Host ""
}

# Sign the executable
if (-not $cert) {
    Write-Host "  Error: No certificate available for signing" -ForegroundColor Red
    Write-Host "  Executable will remain unsigned." -ForegroundColor Yellow
    exit 0
}

Write-Host "  Signing executable..." -ForegroundColor Yellow

# Timestamp servers (try multiple in case one is down)
$timestampServers = @(
    "http://timestamp.digicert.com",
    "http://timestamp.sectigo.com",
    "http://timestamp.comodoca.com"
)

$signSuccess = $false
$lastError = $null

foreach ($timestampServer in $timestampServers) {
    try {
        $signArgs = @(
            "sign",
            "/sha1", $cert.Thumbprint,
            "/fd", "SHA256",
            "/tr", $timestampServer,
            "/td", "SHA256",
            "/v",
            "`"$ExecutablePath`""
        )
        
        $signResult = & $signtoolPath $signArgs 2>&1
        $signExitCode = $LASTEXITCODE
        
        if ($signExitCode -eq 0) {
            $signSuccess = $true
            Write-Host "  Executable signed successfully" -ForegroundColor Green
            Write-Host "  Timestamp server: $timestampServer" -ForegroundColor Gray
            break
        }
        else {
            $lastError = $signResult
        }
    }
    catch {
        $lastError = $_.Exception.Message
    }
}

if (-not $signSuccess) {
    Write-Host "  Warning: Failed to sign executable" -ForegroundColor Yellow
    if ($lastError) {
        Write-Host "  Error: $lastError" -ForegroundColor White
    }
    Write-Host "  Executable will remain unsigned." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Note: Self-signed certificates may still trigger Windows warnings." -ForegroundColor Gray
    Write-Host "  For production use, consider obtaining a certificate from a trusted CA." -ForegroundColor Gray
    exit 0
}

Write-Host ""
Write-Host "Code signing completed successfully!" -ForegroundColor Green
Write-Host "  Certificate: $certFriendlyName" -ForegroundColor Gray
Write-Host "  Company: Pazal Group SRL" -ForegroundColor Gray
Write-Host "  Developer: Constantin Virgil" -ForegroundColor Gray
Write-Host ""
Write-Host "Note: Self-signed certificates may still show warnings on other machines." -ForegroundColor Yellow
Write-Host "Users can verify the signature by right-clicking the .exe > Properties > Digital Signatures" -ForegroundColor Gray
