# PowerShell script to download NotoSansKR fonts

# Create directory for fonts
$fontDir = "./fonts"
if (!(Test-Path $fontDir)) {
    New-Item -Path $fontDir -ItemType Directory | Out-Null
}

# List of font files to download
$fontFiles = @(
    "NotoSansKR-Black.ttf",
    "NotoSansKR-Bold.ttf",
    "NotoSansKR-ExtraBold.ttf",
    "NotoSansKR-ExtraLight.ttf",
    "NotoSansKR-Light.ttf",
    "NotoSansKR-Medium.ttf",
    "NotoSansKR-Regular.ttf",
    "NotoSansKR-SemiBold.ttf",
    "NotoSansKR-Thin.ttf"
)

# GitHub Raw file base URL
$baseUrl = "https://raw.githubusercontent.com/pyhub-kr/dump-data/main/fonts/NotoSansKR"

Write-Host "📦 NotoSansKR 폰트 파일 다운로드 중..." -ForegroundColor Cyan

# Download each font file
foreach ($file in $fontFiles) {
    Write-Host "⬇️  $file" -ForegroundColor Yellow
    $url = "$baseUrl/$file"
    $outputPath = Join-Path $fontDir $file
    
    try {
        # Use Invoke-WebRequest for downloading
        Invoke-WebRequest -Uri $url -OutFile $outputPath -UseBasicParsing
    }
    catch {
        Write-Host "❌ 다운로드 실패: $file - $_" -ForegroundColor Red
        continue
    }
}

Write-Host "✅ 모든 폰트 다운로드 완료: $fontDir" -ForegroundColor Green