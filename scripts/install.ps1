#!/usr/bin/env pwsh

param(
    [string]$Owner = "pyhub-kr", # GitHub 저장소 소유자
    [string]$Repo = "pyhub-mcptools", # GitHub 저장소 이름
    [string]$InstallDir, # 사용자 지정 설치 디렉토리
    [switch]$NoPrompt, # 사용자 프롬프트 없이 자동 설치 여부
    [switch]$AddToPath = $true, # PATH에 설치 디렉토리 추가 여부
    [string]$Token                   # GitHub API 토큰
)

# 프로그레스바 표시 함수
function Show-Progress
{
    param (
        [int]$Step, # 현재 단계
        [int]$TotalSteps, # 전체 단계 수
        [string]$Message  # 표시할 메시지
    )

    $percent = ($Step / $TotalSteps) * 100
    $progress = [math]::Min([math]::Max(0,[math]::Round($percent)), 100)

    Write-Progress -Activity "Installing pyhub.mcptools" -Status $Message -PercentComplete $progress
    Write-Host "[$Step/$TotalSteps] $Message"
}

# 환경 설정 및 OS 감지 함수
function Initialize-Environment
{
    # 운영체제 감지 (pwsh와 기본 파워쉘 호환)
    $script:os = [System.Runtime.InteropServices.RuntimeInformation]::OSDescription

    # 경로 구분자 설정 - Windows는 세미콜론, 그 외는 콜론
    $script:PathSeparator = if ($script:os -match "Windows")
    {
        ';'
    }
    else
    {
        ':'
    }

    # 운영체제별 설정 값 지정
    switch -Regex ($script:os)
    {
        "Windows" {
            $script:keyword = "pyhub.mcptools-windows"  # 다운로드 파일 키워드
            $script:defaultExtractBasePath = "C:\mcptools"  # 기본 설치 경로
        }
        "Darwin" {
            $script:keyword = "pyhub.mcptools-macOS"  # 다운로드 파일 키워드
            $script:defaultExtractBasePath = "$HOME/mcptools"  # 기본 설치 경로
        }
        "Linux" {
            $script:keyword = "pyhub.mcptools-linux"  # 다운로드 파일 키워드
            $script:defaultExtractBasePath = "$HOME/mcptools"  # 기본 설치 경로
        }
        default {
            Write-Error "Unsupported OS: $script:os"
            exit 1
        }
    }
}

# 설치 경로 설정 함수
function Set-InstallPath
{
    Write-Host "Default extraction path is: $script:defaultExtractBasePath"

    # 자동 설치 모드이거나 사용자 지정 경로가 있는 경우
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
        # 사용자에게 경로 확인
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

    $script:extractPath = Join-Path $script:extractBasePath "pyhub.mcptools"

    # 기존 폴더 체크 및 처리
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

# 최신 릴리스 정보 가져오기 함수
function Get-LatestRelease
{
    $releaseApiUrl = "https://api.github.com/repos/$Owner/$Repo/releases/latest"  # GitHub API URL
    $headers = @{ "User-Agent" = "PowerShell" }  # API 요청 헤더

    # 토큰이 제공된 경우 인증 헤더 추가
    if ($Token)
    {
        $headers.Authorization = "Bearer $Token"
    }

    try
    {
        $response = Invoke-WebRequest -Uri $releaseApiUrl -Headers $headers -ErrorAction Stop
        $rateRemaining = $response.Headers["x-ratelimit-remaining"]  # API 요청 제한 확인

        # API 요청 제한 초과 체크
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

# 자산 다운로드 함수
function Download-Asset
{
    param (
        [PSObject]$Release  # 릴리스 정보 객체
    )

    # 운영체제에 맞는 자산 찾기
    $asset = $Release.assets | Where-Object { $_.name -like "$script:keyword*.zip" } | Select-Object -First 1

    if ($null -eq $asset)
    {
        Write-Error "No release asset found matching the keyword: $script:keyword"
        exit 1
    }

    # 다운로드 경로 및 파일명 설정
    $downloadUrl = $asset.browser_download_url  # 다운로드 URL
    $outputFile = Join-Path $PWD $asset.name    # 저장할 파일 경로

    # 다운로드 실행 (Invoke-WebRequest의 기본 진행률 표시 사용)
    Write-Host "Downloading: $( $asset.browser_download_url )"

    try
    {
        # Invoke-WebRequest는 기본적으로 진행률 표시줄을 제공함
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

# 체크섬 검증 함수
function Verify-Checksum
{
    param (
        [string]$DownloadUrl, # 다운로드 URL
        [string]$OutputFile    # 다운로드한 파일 경로
    )

    # 체크섬 파일 다운로드
    $sha256Url = "$DownloadUrl.sha256"  # 체크섬 파일 URL
    $sha256File = "$OutputFile.sha256"  # 체크섬 파일 저장 경로

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

    # 체크섬 파일에서 해시값 추출
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

    # 다운로드한 파일의 해시값 계산
    $actualHash = (Get-FileHash -Path $OutputFile -Algorithm SHA256).Hash

    # 해시값 비교
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

# 파일 압축 해제 함수
function Extract-Archive
{
    param (
        [string]$ArchiveFile, # 압축 파일 경로
        [string]$DestinationPath  # 압축 해제 대상 경로
    )

    # 임시 디렉토리 생성
    $tempPath = Join-Path ([System.IO.Path]::GetTempPath()) ([System.Guid]::NewGuid().ToString())  # 임시 경로
    New-Item -ItemType Directory -Path $tempPath | Out-Null

    # 임시 디렉토리에 압축 해제
    Write-Host "Extracting to temporary location: $tempPath"
    Expand-Archive -LiteralPath $ArchiveFile -DestinationPath $tempPath -Force

    # 압축 해제된 내용을 최종 경로로 이동
    Move-Item -Path (Join-Path $tempPath "*") -Destination $DestinationPath -Force

    # 임시 디렉토리 정리
    Remove-Item -Recurse -Force $tempPath

    # 최종 디렉토리로 이동
    Set-Location -Path $DestinationPath
    Write-Host "`nChanged directory to: $DestinationPath"
}

# PATH 환경변수 설정 함수
function Update-PathVariable
{
    param (
        [string]$AddedPath  # PATH에 추가할 경로
    )

    # 사용자 PATH 환경변수 가져오기
    $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")  # 현재 사용자 PATH

    # 경로가 이미 PATH에 있는지 확인
    if ($AddToPath -and -not ($currentPath.Split($script:PathSeparator) -contains $AddedPath))
    {
        if ($NoPrompt)
        {
            [Environment]::SetEnvironmentVariable("Path", "$currentPath$script:PathSeparator$AddedPath", "User")
            Write-Host "Added to user PATH."
        }
        else
        {
            $addToPath = Read-Host "The path '$AddedPath' is not in your PATH. Add it? (Y/n)"
            if ([string]::IsNullOrWhiteSpace($addToPath) -or $addToPath -match "^[Yy]$")
            {
                [Environment]::SetEnvironmentVariable("Path", "$currentPath$script:PathSeparator$AddedPath", "User")
                Write-Host "Added to user PATH."
            }
            else
            {
                Write-Host "Did not add '$AddedPath' to user PATH."
            }
        }
    }

    # 현재 세션 PATH에 추가
    if (-not ($env:Path.Split($script:PathSeparator) -contains $AddedPath))
    {
        $env:Path += "$script:PathSeparator$AddedPath"
    }
}

# 설치 완료 후 안내 메시지 출력 함수
function Show-PostInstallInstructions
{
    Write-Host "`nTo add configuration for Claude, please run the following commands:"
    Write-Host ""

    # 운영체제별 명령어 표시
    if ($script:os -match "Windows")
    {
        Write-Host ".\pyhub.mcptools.exe --version"
        Write-Host ".\pyhub.mcptools.exe kill claude"
        Write-Host ".\pyhub.mcptools.exe setup-add"
        Write-Host ".\pyhub.mcptools.exe setup-print"
    }
    else
    {
        Write-Host "./pyhub.mcptools --version"
        Write-Host "./pyhub.mcptools kill claude"
        Write-Host "./pyhub.mcptools setup-add"
        Write-Host "./pyhub.mcptools setup-print"
    }
}

# 메인 설치 함수
function Install-PyHubMCPTools
{
    $totalSteps = 6  # 전체 설치 단계 수
    $currentStep = 0  # 현재 진행 단계

    # 1. 환경 초기화
    $currentStep++
    Show-Progress -Step $currentStep -TotalSteps $totalSteps -Message "Initializing environment"
    Initialize-Environment

    # 2. 설치 경로 설정
    $currentStep++
    Show-Progress -Step $currentStep -TotalSteps $totalSteps -Message "Setting installation path"
    $installPath = Set-InstallPath

    # 3. 최신 릴리스 정보 가져오기
    $currentStep++
    Show-Progress -Step $currentStep -TotalSteps $totalSteps -Message "Fetching latest release information"
    $releaseInfo = Get-LatestRelease

    # 4. 다운로드 및 체크섬 검증
    $currentStep++
    Show-Progress -Step $currentStep -TotalSteps $totalSteps -Message "Downloading and verifying assets"
    $downloadResult = Download-Asset -Release $releaseInfo
    Verify-Checksum -DownloadUrl $downloadResult.DownloadUrl -OutputFile $downloadResult.OutputFile

    # 5. 압축 해제
    $currentStep++
    Show-Progress -Step $currentStep -TotalSteps $totalSteps -Message "Extracting files"
    Extract-Archive -ArchiveFile $downloadResult.OutputFile -DestinationPath $installPath

    # 6. PATH 업데이트 및 설치 후 안내
    $currentStep++
    Show-Progress -Step $currentStep -TotalSteps $totalSteps -Message "Configuring environment and finishing installation"
    Update-PathVariable -AddedPath $installPath
    Show-PostInstallInstructions

    # 완료 표시
    Write-Progress -Activity "Installing pyhub.mcptools" -Completed
    Write-Host "`nInstallation complete!"
}

# 설치 실행
Install-PyHubMCPTools