#!/usr/bin/env pwsh

param(
    [string]$Owner = "pyhub-kr", # GitHub repository owner
    [string]$Repo = "pyhub-mcptools", # GitHub repository name
    [string]$InstallDir, # Custom installation directory
    [switch]$NoPrompt, # Auto install without user prompts
    [switch]$AddToPath = $true, # Add installation directory to PATH
    [string]$Token                   # GitHub API token
)

# Function to display progress bar
function Show-Progress
{
    param (
        [int]$Step, # Current step
        [int]$TotalSteps, # Total number of steps
        [string]$Message  # Message to display
    )

    $percent = ($Step / $TotalSteps) * 100
    $progress = [math]::Min([math]::Max(0,[math]::Round($percent)), 100)

    Write-Progress -Activity "Installing pyhub.mcptools" -Status $Message -PercentComplete $progress
    Write-Host "[$Step/$TotalSteps] $Message"
}

# Function for environment setup and OS detection
function Initialize-Environment
{
    # OS detection (compatible with pwsh and default PowerShell)
    $script:os = [System.Runtime.InteropServices.RuntimeInformation]::OSDescription

    # Windows only - exit with error message for other OS
    if (-not ($script:os -match "Windows"))
    {
        Write-Error "This installer only supports Windows. Detected OS: $script:os"
        exit 1
    }

    # Set path separator - semicolon for Windows
    $script:PathSeparator = ';'

    # Set Windows configuration values
    $script:keyword = "pyhub.mcptools-windows"  # Download file keyword
    $script:defaultExtractBasePath = "C:\mcptools"  # Default installation path
}

# Function to set installation path
function Set-InstallPath
{
    Write-Host "Default extraction path is: $script:defaultExtractBasePath"

    # For auto install mode or custom path provided
    if ($NoPrompt -or $InstallDir)
    {
        $script:extractBasePath = if ($InstallDir)
        {
            $InstallDir
        }
        else
        {
            $script:defaultExtractBasePath
        }
    }
    else
    {
        # Ask user for path confirmation
        $userPath = Read-Host "Use this path? (Press Enter to accept or type a new path)"
        $script:extractBasePath = if ( [string]::IsNullOrWhiteSpace($userPath))
        {
            $script:defaultExtractBasePath
        }
        else
        {
            $userPath
        }
    }

    # Restore original code (using Join-Path)
    $script:extractPath = Join-Path $script:extractBasePath "pyhub.mcptools"

    # Check and handle existing folder
    if (Test-Path $script:extractPath)
    {
        $proceed = $true
        if (-not $NoPrompt)
        {
            $response = Read-Host "The path already exists. Delete it and continue? (y/N)"
            $proceed = $response -eq "y"
        }
        if ($proceed)
        {
            Remove-Item -Recurse -Force $script:extractPath
        }
        else
        {
            Write-Host "Installation aborted."
            exit 0
        }
    }

    return $script:extractPath
}

# Function to get latest release information
function Get-LatestRelease
{
    $releaseApiUrl = "https://api.github.com/repos/$Owner/$Repo/releases/latest"  # GitHub API URL
    $headers = @{ "User-Agent" = "PowerShell" }  # API request headers

    # Add auth header if token provided
    if ($Token)
    {
        $headers.Authorization = "Bearer $Token"
    }

    try
    {
        $response = Invoke-WebRequest -Uri $releaseApiUrl -Headers $headers -ErrorAction Stop
        $rateRemaining = $response.Headers["x-ratelimit-remaining"]  # Check API rate limit

        # Check for API rate limit exceeded
        if ($response.StatusCode -eq 403 -or $response.StatusCode -eq 429)
        {
            Write-Error "Rate limit exceeded (status: $( $response.StatusCode )). Remaining quota: $rateRemaining"
            exit 1
        }

        $release = $response.Content | ConvertFrom-Json
        return $release
    }
    catch
    {
        Write-Error "Failed to fetch release information: $_"
        exit 1
    }
}

# Function to download assets
function Download-Asset
{
    param (
        [PSObject]$Release  # Release information object
    )

    # Find asset matching OS
    $asset = $Release.assets | Where-Object { $_.name -like "$script:keyword*.zip" } | Select-Object -First 1

    if ($null -eq $asset)
    {
        Write-Error "No release asset found matching the keyword: $script:keyword"
        exit 1
    }

    # Download to temp directory
    $tempDir = [System.IO.Path]::GetTempPath()
    $downloadUrl = $asset.browser_download_url
    $outputFile = Join-Path $tempDir $asset.name

    # Execute download
    Write-Host "Downloading to temp directory: $downloadUrl"

    try
    {
        Invoke-WebRequest -Uri $downloadUrl -OutFile $outputFile -ErrorAction Stop
        Write-Host "Download complete: $outputFile"
    }
    catch
    {
        Write-Error "Failed to download file: $_"
        exit 1
    }

    return @{
        DownloadUrl = $downloadUrl
        OutputFile = $outputFile
    }
}

# Function to verify checksum
function Verify-Checksum
{
    param (
        [string]$DownloadUrl,
        [string]$OutputFile
    )

    # Download checksum file to same temp path
    $sha256Url = "$DownloadUrl.sha256"
    $sha256File = "$OutputFile.sha256"

    Write-Host "Downloading checksum file: $sha256Url"
    try
    {
        Invoke-WebRequest -Uri $sha256Url -OutFile $sha256File -ErrorAction Stop
    }
    catch
    {
        Write-Error "Failed to download SHA256 checksum file: $_"
        exit 1
    }

    # Extract hash from checksum file
    $expectedHash = Get-Content $sha256File | ForEach-Object {
        if ($_ -match "([a-fA-F0-9]{64})")
        {
            return $matches[1]
        }
    }

    if (-not $expectedHash)
    {
        Write-Error "Could not parse SHA256 hash from: $sha256File"
        exit 1
    }

    # Calculate hash of downloaded file
    $actualHash = (Get-FileHash -Path $OutputFile -Algorithm SHA256).Hash

    # Compare hashes
    if ($actualHash -ne $expectedHash)
    {
        Write-Error "Checksum verification failed! Expected: $expectedHash, Actual: $actualHash"
        Remove-Item -Force $OutputFile
        exit 1
    }
    else
    {
        Write-Host "Checksum verified successfully."
        return $true
    }
}

# Function to extract archive
function Extract-Archive
{
    param (
        [string]$ArchiveFile,
        [string]$DestinationPath
    )

    # Create temp directory
    $tempPath = Join-Path ([System.IO.Path]::GetTempPath()) ([System.Guid]::NewGuid().ToString())
    New-Item -ItemType Directory -Path $tempPath | Out-Null

    # Create destination directory if not exists
    if (-not (Test-Path -Path $DestinationPath -PathType Container))
    {
        New-Item -ItemType Directory -Path $DestinationPath -Force | Out-Null
    }

    # Extract to temp directory
    Write-Host "Extracting to temporary location: $tempPath"
    Expand-Archive -LiteralPath $ArchiveFile -DestinationPath $tempPath -Force

    # Check archive contents - look for pyhub.mcptools folder
    $pyhubFolder = Get-ChildItem -Path $tempPath -Directory | Where-Object { $_.Name -eq "pyhub.mcptools" } | Select-Object -First 1

    if ($pyhubFolder)
    {
        # Move only files inside pyhub.mcptools folder to target
        Get-ChildItem -Path $pyhubFolder.FullName -Force | ForEach-Object {
            Move-Item -Path $_.FullName -Destination $DestinationPath -Force
        }
    }
    else
    {
        # Move all files from temp folder to target
        Get-ChildItem -Path $tempPath -Force | ForEach-Object {
            Move-Item -Path $_.FullName -Destination $DestinationPath -Force
        }
    }

    # Clean up temp directory
    Remove-Item -Recurse -Force $tempPath
}

# Function to set PATH environment variable
function Update-PathVariable
{
    param (
        [string]$AddedPath  # Path to add to PATH
    )

    $env:PATH += ";$AddedPath"
    [Environment]::SetEnvironmentVariable("PATH", $env:PATH, [EnvironmentVariableTarget]::User)
    Write-Host "✅ Added '$AddedPath' to User PATH environment variable"
}

# Function to show post-installation instructions
function Show-PostInstallInstructions
{
    Write-Host "`nTo add configuration for Claude, please run the following commands:"
    Write-Host ""

    # Show Windows commands
    Write-Host "cd $script:extractPath"
    Write-Host ""
    Write-Host ".\pyhub.mcptools.exe --version"
    Write-Host ".\pyhub.mcptools.exe kill claude"
    Write-Host ".\pyhub.mcptools.exe setup-add"
    Write-Host ".\pyhub.mcptools.exe setup-print"
}

# Main installation function
function Install-PyHubMCPTools
{
    $totalSteps = 6  # Total number of installation steps
    $currentStep = 0  # Current progress step

    # 1. Initialize environment
    $currentStep++
    Show-Progress -Step $currentStep -TotalSteps $totalSteps -Message "Initializing environment"
    Initialize-Environment

    # 2. Set installation path
    $currentStep++
    Show-Progress -Step $currentStep -TotalSteps $totalSteps -Message "Setting installation path"
    $installPath = Set-InstallPath

    # 3. Get latest release info
    $currentStep++
    Show-Progress -Step $currentStep -TotalSteps $totalSteps -Message "Fetching latest release information"
    $releaseInfo = Get-LatestRelease

    # 4. Download and verify checksum
    $currentStep++
    Show-Progress -Step $currentStep -TotalSteps $totalSteps -Message "Downloading and verifying assets"
    $downloadResult = Download-Asset -Release $releaseInfo
    Verify-Checksum -DownloadUrl $downloadResult.DownloadUrl -OutputFile $downloadResult.OutputFile

    # 5. Extract files
    $currentStep++
    Show-Progress -Step $currentStep -TotalSteps $totalSteps -Message "Extracting files"
    Extract-Archive -ArchiveFile $downloadResult.OutputFile -DestinationPath $installPath

    # Delete downloaded temp files and checksum
    Remove-Item -Force $downloadResult.OutputFile
    Remove-Item -Force "$( $downloadResult.OutputFile ).sha256"
    
    # Add installation directory to PATH if enabled
    if ($AddToPath)
    {
        Update-PathVariable -AddedPath $installPath
    }

    # 6. Post-installation guide
    $currentStep++
    Show-Progress -Step $currentStep -TotalSteps $totalSteps -Message "Finishing installation"
    Show-PostInstallInstructions

    # Show completion
    Write-Progress -Activity "Installing pyhub.mcptools" -Completed
    Write-Host "`nInstallation complete!"
}

# Run installation
Install-PyHubMCPTools