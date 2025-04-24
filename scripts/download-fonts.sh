#!/bin/bash

# 저장할 디렉토리 생성
FONT_DIR="./fonts"
mkdir -p "$FONT_DIR"

# 다운로드할 파일 목록
FONT_FILES=(
    "NotoSansKR-Black.ttf"
    "NotoSansKR-Bold.ttf"
    "NotoSansKR-ExtraBold.ttf"
    "NotoSansKR-ExtraLight.ttf"
    "NotoSansKR-Light.ttf"
    "NotoSansKR-Medium.ttf"
    "NotoSansKR-Regular.ttf"
    "NotoSansKR-SemiBold.ttf"
    "NotoSansKR-Thin.ttf"
)

# GitHub Raw 파일 base URL
BASE_URL="https://raw.githubusercontent.com/pyhub-kr/dump-data/main/fonts/NotoSansKR"

echo "📦 NotoSansKR 폰트 파일 다운로드 중..."

# 파일 다운로드
for FILE in "${FONT_FILES[@]}"; do
    echo "⬇️  $FILE"
    curl -L -o "$FONT_DIR/$FILE" "$BASE_URL/$FILE"
done

echo "✅ 모든 폰트 다운로드 완료: $FONT_DIR"
