# Google Sheets CLI 사용법

Google Sheets MCP Tools의 명령행 인터페이스(CLI) 사용 가이드입니다.

## 설치 및 환경 설정

### 필수 요구사항
- Python 3.9 이상
- Google Cloud Console에서 생성한 OAuth 2.0 클라이언트 ID

### 환경 변수 설정
```bash
export USE_GOOGLE_SHEETS=1
export GOOGLE_CLIENT_SECRET_PATH=./google_client_secret.json
```

## CLI 명령어

### 1. 기본 사용법

#### Google 모듈 CLI
```bash
python -m pyhub.mcptools.google <command> [options]
```

#### Sheets 전용 CLI
```bash
python -m pyhub.mcptools.google.sheets <command> [options]
```

### 2. 인증 관리

#### 새로운 인증
```bash
# 브라우저를 통한 OAuth 인증
python -m pyhub.mcptools.google auth

# 강제 재인증 (기존 토큰 덮어쓰기)
python -m pyhub.mcptools.google auth --force
```

#### 인증 상태 확인
```bash
python -m pyhub.mcptools.google auth --status
```

#### 토큰 갱신
```bash
python -m pyhub.mcptools.google auth --refresh
```

#### 토큰 삭제
```bash
python -m pyhub.mcptools.google auth --clear
```

### 3. 스프레드시트 관리

#### 스프레드시트 목록 조회
```bash
# 기본 목록 (최대 10개)
python -m pyhub.mcptools.google sheets list

# 더 많은 결과
python -m pyhub.mcptools.google sheets list --limit 50

# JSON 형식으로 출력
python -m pyhub.mcptools.google sheets list --json
```

#### 스프레드시트 검색
```bash
# 이름으로 검색
python -m pyhub.mcptools.google sheets search 'Budget'

# 여러 단어 검색
python -m pyhub.mcptools.google sheets search 'Annual Budget 2024'
```

#### 새 스프레드시트 생성
```bash
# 기본 생성 (시트명 자동 표준화)
python -m pyhub.mcptools.google sheets create 'My New Sheet'

# JSON 출력으로 ID 확인
python -m pyhub.mcptools.google sheets create 'My New Sheet' --json
```

#### 스프레드시트 정보 조회
```bash
python -m pyhub.mcptools.google sheets info <spreadsheet_id>
```

### 4. 데이터 조작

#### 데이터 읽기
```bash
# 특정 범위 읽기
python -m pyhub.mcptools.google sheets read <spreadsheet_id> 'Sheet1!A1:C10'

# JSON 형식으로 출력
python -m pyhub.mcptools.google sheets read <spreadsheet_id> 'Sheet1!A1:C10' --json
```

#### 데이터 쓰기
```bash
# 2D 배열 데이터 쓰기
python -m pyhub.mcptools.google sheets write <spreadsheet_id> 'Sheet1!A1' '[["Name","Age"],["Alice",30],["Bob",25]]'

# 단일 행 데이터
python -m pyhub.mcptools.google sheets write <spreadsheet_id> 'Sheet1!A1' '[["Header1","Header2","Header3"]]'
```

### 5. 연결 테스트

```bash
# API 연결 상태 확인
python -m pyhub.mcptools.google test
```

### 6. 버전 정보

```bash
python -m pyhub.mcptools.google version
```

## 출력 형식

### 표 형식 (기본)
```
📊 스프레드시트 목록 조회 중... (최대 10개)

총 3개의 스프레드시트:
--------------------------------------------------------------------------------
  1. Budget 2024
     ID: 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms
     수정: 2024-01-15T10:30:00Z

  2. Sales Report
     ID: 1AbcDEf0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upxy
     수정: 2024-01-14T16:45:00Z
```

### JSON 형식 (--json 옵션)
```json
[
  {
    "id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
    "name": "Budget 2024",
    "modifiedTime": "2024-01-15T10:30:00Z",
    "webViewLink": "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
  }
]
```

## 실용적인 예시

### 1. 일일 업무 워크플로우

```bash
# 1. 인증 상태 확인
python -m pyhub.mcptools.google auth --status

# 2. 오늘의 업무 시트 찾기
python -m pyhub.mcptools.google sheets search 'Daily Tasks'

# 3. 시트 정보 확인
python -m pyhub.mcptools.google sheets info <found_id>

# 4. 오늘 날짜의 데이터 읽기
python -m pyhub.mcptools.google sheets read <sheet_id> 'Tasks!A1:E20'
```

### 2. 데이터 백업

```bash
# JSON 형식으로 전체 데이터 백업
python -m pyhub.mcptools.google sheets read <sheet_id> 'Sheet1!A:Z' --json > backup.json
```

### 3. 새 프로젝트 시트 생성

```bash
# 새 프로젝트 시트 생성
SHEET_ID=$(python -m pyhub.mcptools.google sheets create 'Project Alpha' --json | jq -r '.id')

# 헤더 작성
python -m pyhub.mcptools.google sheets write $SHEET_ID 'Sheet1!A1' '[["Task","Assignee","Status","Due Date"]]'

# 초기 데이터 입력
python -m pyhub.mcptools.google sheets write $SHEET_ID 'Sheet1!A2' '[["Setup repo","Alice","In Progress","2024-01-20"],["Design UI","Bob","Not Started","2024-01-25"]]'
```

## 에러 처리

### 일반적인 오류

#### 인증 오류
```
❌ 유효한 인증이 없습니다.
   먼저 'python -m pyhub.mcptools.google auth'를 실행하세요.
```
**해결**: `python -m pyhub.mcptools.google auth` 실행

#### 권한 오류
```
❌ 권한이 없습니다. 스프레드시트 접근 권한을 확인하세요.
```
**해결**: 스프레드시트 소유자에게 편집 권한 요청

#### 잘못된 범위 형식
```
❌ 범위 형식이 잘못되었습니다. 'Sheet1!A1:C10' 형식으로 입력하세요.
```
**해결**: 올바른 A1 표기법 사용

### 디버깅

#### 상세한 오류 정보 확인
```bash
# 상세 로그와 함께 실행
python -m pyhub.mcptools.google sheets list --json 2>&1 | jq .
```

#### 연결 테스트
```bash
# API 연결 상태 확인
python -m pyhub.mcptools.google test
```

## 팁과 요령

### 1. 스프레드시트 ID 찾기
- URL에서 추출: `https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit`
- 검색 명령어 사용: `python -m pyhub.mcptools.google sheets search 'Sheet Name'`

### 2. 대용량 데이터 처리
- 청크 단위로 나누어 처리
- JSON 출력을 활용하여 파일로 저장 후 처리

### 3. 자동화 스크립트
```bash
#!/bin/bash
# 일일 보고서 생성 스크립트

REPORT_ID="your_report_sheet_id"
TODAY=$(date +%Y-%m-%d)

# 오늘 데이터 읽기
python -m pyhub.mcptools.google sheets read $REPORT_ID "Daily!A:E" --json > daily_$TODAY.json

# 데이터 처리 (jq 사용)
cat daily_$TODAY.json | jq '.[] | select(.date == "'$TODAY'")'
```

### 4. 배치 작업
여러 작업을 연속으로 실행할 때는 환경 변수를 한 번만 설정:

```bash
export USE_GOOGLE_SHEETS=1
export GOOGLE_CLIENT_SECRET_PATH=./google_client_secret.json

python -m pyhub.mcptools.google sheets list
python -m pyhub.mcptools.google sheets search 'Budget'
python -m pyhub.mcptools.google sheets create 'New Project'
```

## 문제 해결

### Q: 브라우저가 자동으로 열리지 않아요
A: 터미널에 표시되는 URL을 수동으로 복사하여 브라우저에 붙여넣으세요.

### Q: 토큰이 자꾸 만료돼요
A: `python -m pyhub.mcptools.google auth --refresh`로 토큰을 갱신하거나, `--force` 옵션으로 재인증하세요.

### Q: JSON 출력을 예쁘게 보고 싶어요
A: `jq` 명령어를 설치하고 파이프로 연결하세요: `... --json | jq .`

### Q: 특정 시트만 접근하고 싶어요
A: 범위에 시트명을 명시하세요: `'SheetName!A1:C10'`