#!/bin/bash

# 오류 발생 시에 스크립트 종료 및 미정의 변수 사용 방지
set -e
set -u

# 변수 정의
# OWNER: GitHub 저장소 소유자 이름
# REPO: GitHub 저장소 이름
# KEYWORD: 다운로드할 릴리스 자산 필터링 키워드
# DEFAULT_EXTRACT_BASE: 기본 설치 디렉토리 경로
OWNER="pyhub-kr"
REPO="pyhub-mcptools"
KEYWORD="pyhub.mcptools-macOS"
DEFAULT_EXTRACT_BASE="$HOME/mcptools"

# 프로그레스바 표시 함수
show_progress() {
  local width=50
  local percent=$1
  local completed=$((width * percent / 100))
  local remaining=$((width - completed))
  
  printf "\r[%s%s] %d%%" "$(printf '#%.0s' $(seq 1 $completed))" "$(printf ' %.0s' $(seq 1 $remaining))" "$percent"
}

# OS 검사 함수
check_os() {
  if [[ "$(uname)" != "Darwin" ]]; then
    echo "Unsupported OS. This script only supports macOS."
    exit 1
  fi
  echo "✅ OS check passed: macOS detected"
}

# 설치 경로 설정 함수
setup_path() {
  echo "Default extraction path is: $DEFAULT_EXTRACT_BASE"
  read -p "Use this path? (Press Enter to accept or type a new path): " EXTRACT_BASE

  if [ -z "$EXTRACT_BASE" ]; then
    EXTRACT_BASE="$DEFAULT_EXTRACT_BASE"
  fi

  EXTRACT_PATH="$EXTRACT_BASE/pyhub.mcptools"
  
  # 기존 폴더가 있으면 삭제 여부 확인
  if [ -d "$EXTRACT_PATH" ]; then
    read -p "The path '$EXTRACT_PATH' already exists. Delete and continue? (y/N): " CONFIRM
    if [[ "$CONFIRM" == "y" || "$CONFIRM" == "Y" ]]; then
      rm -rf "$EXTRACT_PATH"
    else
      echo "Installation aborted."
      exit 0
    fi
  fi
  
  echo "📁 Installation path set to: $EXTRACT_PATH"
  return 0
}

# 릴리스 정보 가져오기 함수
get_release_info() {
  echo "🔍 Fetching latest release information..."
  RELEASE_JSON=$(curl -s "https://api.github.com/repos/$OWNER/$REPO/releases/latest")
  
  # 키워드에 맞는 zip 파일 링크 찾기
  DOWNLOAD_URL=$(echo "$RELEASE_JSON" | grep "browser_download_url" | grep "$KEYWORD" | cut -d '"' -f 4 | grep "\.zip$" )
  SHA256_URL=$(echo "$RELEASE_JSON" | grep "browser_download_url" | grep "$KEYWORD" | cut -d '"' -f 4 | grep "\.sha256$" )

  if [ -z "$DOWNLOAD_URL" ]; then
    echo "❌ No release asset found matching the keyword: $KEYWORD"
    exit 1
  fi
  
  echo "🔗 Found download URL: $DOWNLOAD_URL"
  echo "🔐 Found checksum URL: $SHA256_URL"
}

# 파일 다운로드 함수
download_file() {
  local url=$1
  local output=$2
  local size_in_bytes=0
  local downloaded=0
  local percent=0
  
  # 파일 크기 가져오기
  size_in_bytes=$(curl -sI "$url" | grep -i content-length | awk '{print $2}' | tr -d '\r')
  
  # 크기 정보를 가져올 수 없으면 기본값 사용
  if [ -z "$size_in_bytes" ] || [ "$size_in_bytes" -eq 0 ]; then
    echo "⚠️ Could not determine file size, downloading without progress bar"
    curl -L "$url" -o "$output"
    return
  fi
  
  # 프로그레스바와 함께 다운로드
  echo "📥 Downloading: $url"
  curl -L "$url" -o "$output" -#
  echo ""
  echo "✅ Download complete: $output"
}

# 체크섬 검증 함수
verify_checksum() {
  local file=$1
  local checksum_file=$2
  
  echo "🔍 Verifying file integrity..."
  
  # SHA256 해시값만 추출
  EXPECTED_HASH=$(grep -Eo '^[a-fA-F0-9]{64}' "$checksum_file")
  if [ -z "$EXPECTED_HASH" ]; then
    echo "❌ Could not extract SHA256 hash from checksum file."
    exit 1
  fi

  # zip 파일의 실제 해시 계산 (Linux/macOS 호환 처리)
  if command -v sha256sum &> /dev/null; then
    ACTUAL_HASH=$(sha256sum "$file" | awk '{print $1}')
  elif command -v shasum &> /dev/null; then
    ACTUAL_HASH=$(shasum -a 256 "$file" | awk '{print $1}')
  else
    echo "❌ No SHA256 tool found (sha256sum or shasum required)."
    exit 1
  fi

  # 해시 비교
  if [ "$ACTUAL_HASH" != "$EXPECTED_HASH" ]; then
    echo "❌ Checksum verification failed!"
    echo "Expected: $EXPECTED_HASH"
    echo "Actual  : $ACTUAL_HASH"
    rm -f "$file"
    exit 1
  else
    echo "✅ Checksum verified successfully."
  fi
}

# 압축 해제 및 설치 함수
extract_and_install() {
  local file=$1
  local tmp_dir=$2
  local extract_path=$3
  
  echo "📦 Extracting files..."
  unzip -q "$file" -d "$tmp_dir"
  show_progress 50
  
  # Move to final destination
  mkdir -p "$extract_path"
  mv "$tmp_dir"/* "$extract_path"
  show_progress 100
  echo ""
  
  # Clean up
  rm -rf "$tmp_dir"
  echo "✅ Installation complete at: $extract_path"
}

# PATH 환경변수 설정 함수
setup_path_env() {
  local extract_path=$1
  
  cd "$extract_path"
  echo ""
  echo "Changed directory to: $extract_path"

  # Check if path is already in PATH
  if [[ ":$PATH:" != *":$extract_path:"* ]]; then
    read -p "The path '$extract_path' is not in your PATH. Do you want to add it? (Y/n): " ADD_TO_PATH
    if [[ -z "$ADD_TO_PATH" || "$ADD_TO_PATH" == "y" || "$ADD_TO_PATH" == "Y" ]]; then
      SHELL_PROFILE=""
      case "$SHELL" in
        */zsh)
          SHELL_PROFILE="$HOME/.zshrc"
          ;;
        */bash)
          if [ -f "$HOME/.bash_profile" ]; then
            SHELL_PROFILE="$HOME/.bash_profile"
          else
            SHELL_PROFILE="$HOME/.bashrc"
          fi
          ;;
      esac

      if [ -n "$SHELL_PROFILE" ]; then
        if ! grep -q "$extract_path" "$SHELL_PROFILE"; then
          echo "export PATH=\"\$PATH:$extract_path\"" >> "$SHELL_PROFILE"
          echo "✅ Added to PATH in $SHELL_PROFILE"
        else
          echo "✅ Path already present in $SHELL_PROFILE"
        fi
      else
        echo "⚠️ No known shell profile found. Please add the following to your PATH manually:"
        echo "export PATH=\"\$PATH:$extract_path\""
      fi

      # Always add to current session
      export PATH="$PATH:$extract_path"
      echo "✅ Added to current session PATH."
    else
      echo "❌ Did not add '$extract_path' to PATH."
    fi
  fi
}

# 설치 후 안내 함수
show_post_install_instructions() {
  local extract_path=$1
  
  echo ""
  echo "📝 To add configuration for Claude, please run the following commands:"
  echo ""
  echo "cd \"$extract_path\""
  echo "./pyhub.mcptools --version"
  echo "./pyhub.mcptools kill claude"
  echo "./pyhub.mcptools setup-add"
  echo "./pyhub.mcptools setup-print"
}

# 메인 함수
main() {
  check_os
  setup_path
  get_release_info
  
  # Create temporary directory
  TMP_DIR=$(mktemp -d)
  
  # Download files
  FILENAME="$TMP_DIR/$(basename "$DOWNLOAD_URL")"
  CHECKSUM_FILE="$TMP_DIR/$(basename "$SHA256_URL")"
  
  download_file "$DOWNLOAD_URL" "$FILENAME"
  download_file "$SHA256_URL" "$CHECKSUM_FILE"
  
  verify_checksum "$FILENAME" "$CHECKSUM_FILE"
  extract_and_install "$FILENAME" "$TMP_DIR" "$EXTRACT_PATH"
  setup_path_env "$EXTRACT_PATH"
  show_post_install_instructions "$EXTRACT_PATH"
}

# 스크립트 실행
main