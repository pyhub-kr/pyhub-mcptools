# Google Sheets MCP 도구

이 문서는 pyhub-mcptools에서 제공하는 Google Sheets MCP 도구의 사용법을 설명합니다.

## 개요

Google Sheets MCP 도구는 Excel MCP 도구와 동일한 인터페이스로 Google Sheets를 조작할 수 있게 해주는 도구 모음입니다. 브라우저 기반 OAuth 2.0 인증을 통해 사용자의 Google 계정에 안전하게 접근하며, 스프레드시트 생성/조회, 데이터 읽기/쓰기, 시트 관리 등의 기능을 제공합니다.

## 주요 기능

- **스프레드시트 관리**: 목록 조회, 생성, 정보 확인
- **데이터 조작**: 셀 범위 읽기/쓰기/삭제
- **시트 관리**: 시트 추가/삭제/이름변경
- **OAuth 2.0 인증**: 브라우저 기반 안전한 인증
- **자동 토큰 관리**: 토큰 갱신 및 저장

## 설치 및 설정

### 1. 의존성 설치

```bash
pip install "pyhub-mcptools[gsheets]"
```

### 2. 환경 변수 설정

`.env` 파일에 다음 설정을 추가하세요:

```bash
# Google Sheets 활성화
USE_GOOGLE_SHEETS=true

# 선택사항: 사용자 정의 OAuth 앱
# GOOGLE_CLIENT_SECRET_PATH=/path/to/your/client_secret.json

# API 설정 (기본값 사용 권장)
GOOGLE_SHEETS_DEFAULT_TIMEOUT=30
GOOGLE_SHEETS_BATCH_SIZE=1000
GOOGLE_SHEETS_RATE_LIMIT=300
GOOGLE_SHEETS_MAX_RETRIES=5
GOOGLE_SHEETS_MAX_BACKOFF=64
```

### 3. 포트 충돌 방지

OAuth 인증 과정에서 로컬 서버가 자동으로 실행되며, 포트 충돌을 방지하기 위해 **사용 가능한 포트를 자동으로 선택**합니다. 별도의 포트 설정이 필요하지 않습니다.

- 브라우저 인증 시 `http://localhost:자동선택포트` 형태로 실행
- 시스템이 사용 가능한 포트를 자동 할당하므로 충돌 없음
- Google Cloud Console의 리디렉션 URI는 `http://localhost`만 설정하면 됨

### 4. 첫 인증

도구를 처음 사용할 때 브라우저가 자동으로 열리며 Google 로그인을 요청합니다:

```bash
# Google Sheets 도구 사용 시 자동 인증
USE_GOOGLE_SHEETS=1 uv run -m pyhub.mcptools tools-list -v 1
```

인증 정보는 `~/.pyhub-mcptools/credentials/` 디렉토리에 안전하게 저장됩니다.

## 사용 가능한 도구

### 스프레드시트 관리

#### 1. `gsheet_list_spreadsheets`
사용자가 접근 가능한 모든 스프레드시트 목록을 조회합니다.

```json
{
  "spreadsheets": [
    {
      "id": "1abc...",
      "name": "내 스프레드시트",
      "url": "https://docs.google.com/spreadsheets/d/1abc...",
      "createdTime": "2024-01-01T00:00:00Z",
      "modifiedTime": "2024-01-02T00:00:00Z"
    }
  ]
}
```

#### 2. `gsheet_search_by_name`
이름으로 스프레드시트를 검색합니다.

**인수:**
- `search_term`: 검색할 이름 또는 부분 이름
- `exact_match`: 정확히 일치하는지 여부 (기본값: False)

**반환:**
```json
{
  "matches": [
    {
      "id": "1abc...",
      "name": "판매 데이터 2024",
      "url": "https://docs.google.com/spreadsheets/d/1abc...",
      "modifiedTime": "2024-01-02T00:00:00Z"
    }
  ],
  "total": 1,
  "search_term": "판매",
  "exact_match": false
}
```

#### 3. `gsheet_create_spreadsheet`
새 스프레드시트를 생성합니다.

**인수:**
- `name`: 스프레드시트 이름

**반환:**
```json
{
  "id": "1abc...",
  "name": "새 스프레드시트",
  "url": "https://docs.google.com/spreadsheets/d/1abc..."
}
```

#### 4. `gsheet_get_spreadsheet_info`
스프레드시트의 정보와 포함된 시트 목록을 조회합니다.

**인수:**
- `spreadsheet_id`: 스프레드시트 ID

**반환:**
```json
{
  "id": "1abc...",
  "name": "스프레드시트 이름",
  "url": "https://docs.google.com/spreadsheets/d/1abc...",
  "sheets": [
    {
      "id": 0,
      "name": "Sheet1",
      "index": 0,
      "rowCount": 1000,
      "columnCount": 26
    }
  ]
}
```

### 데이터 조작

#### 5. `gsheet_get_values_from_range`
지정된 범위의 데이터를 읽어옵니다. Excel과 같은 expand 모드를 지원합니다.

**인수:**
- `spreadsheet_id`: 스프레드시트 ID
- `sheet_range`: 범위 (예: "Sheet1!A1:C10", "Sheet1" 전체)
- `expand_mode`: 확장 모드 (선택사항)
  - `"table"`: 연속된 데이터 블록 감지
  - `"down"`: 아래로만 확장
  - `"right"`: 오른쪽으로만 확장

**반환:**
```json
{
  "values": [
    ["헤더1", "헤더2", "헤더3"],
    ["값1", "값2", "값3"]
  ],
  "range": "Sheet1!A1:C10",
  "rowCount": 2,
  "columnCount": 3,
  "expand_mode": "table"
}
```

#### 6. `gsheet_set_values_to_range`
지정된 범위에 데이터를 씁니다.

**인수:**
- `spreadsheet_id`: 스프레드시트 ID
- `sheet_range`: 범위 (예: "Sheet1!A1:C2")
- `values`: 2차원 배열 데이터

**예시:**
```json
{
  "spreadsheet_id": "1abc...",
  "sheet_range": "Sheet1!A1:C2",
  "values": [
    ["헤더1", "헤더2", "헤더3"],
    ["값1", "값2", "값3"]
  ]
}
```

#### 7. `gsheet_clear_range`
지정된 범위의 데이터를 삭제합니다.

**인수:**
- `spreadsheet_id`: 스프레드시트 ID
- `sheet_range`: 범위 (예: "Sheet1!A1:C10")

### 시트 관리

#### 8. `gsheet_add_sheet`
새 시트를 추가합니다.

**인수:**
- `spreadsheet_id`: 스프레드시트 ID
- `name`: 새 시트 이름
- `index`: 시트 위치 (선택사항)

#### 9. `gsheet_delete_sheet`
시트를 삭제합니다.

**인수:**
- `spreadsheet_id`: 스프레드시트 ID
- `sheet_name`: 삭제할 시트 이름

#### 10. `gsheet_rename_sheet`
시트 이름을 변경합니다.

**인수:**
- `spreadsheet_id`: 스프레드시트 ID
- `sheet_name`: 현재 시트 이름
- `new_name`: 새 시트 이름

## 주요 개선사항

### 1. 지수 백오프를 통한 자동 재시도
API 할당량 초과 시 자동으로 재시도합니다:
- 429, 403, RESOURCE_EXHAUSTED 오류 감지
- 최대 5회 재시도 (설정 가능)
- 지수 백오프: 1초, 2초, 4초... 최대 64초 대기

### 2. Expand 모드 지원
Excel과 동일한 데이터 확장 기능:
```json
{
  "spreadsheet_id": "1abc...",
  "sheet_range": "Sheet1!A1",
  "expand_mode": "table"
}
```

### 3. 이름으로 스프레드시트 검색
ID를 모를 때 이름으로 검색 가능:
```json
{
  "search_term": "판매",
  "exact_match": false
}
```

### 4. 진정한 비동기 처리 (gspread-asyncio)
`gspread-asyncio`를 사용하여 완전한 비동기 처리를 제공합니다:
- **자동 재시도 및 rate limiting**: 라이브러리 내장 기능
- **객체 캐싱**: Client/Spreadsheet/Worksheet 자동 캐싱
- **토큰 자동 갱신**: 45분마다 자동으로 갱신
- **성능 향상**: 진정한 비동기로 다중 요청 효율성 증가

## Excel에서 Google Sheets로 마이그레이션

### 도구 이름 대응표

| Excel 도구 | Google Sheets 도구 | 설명 |
|-----------|-------------------|------|
| `excel_get_opened_workbooks` | `gsheet_list_spreadsheets` | 워크북/스프레드시트 목록 |
| `excel_get_info` | `gsheet_get_spreadsheet_info` | 파일 정보 조회 |
| `excel_get_values` | `gsheet_get_values_from_range` | 셀 값 읽기 |
| `excel_set_values` | `gsheet_set_values_to_range` | 셀 값 쓰기 |
| `excel_add_sheet` | `gsheet_add_sheet` | 시트 추가 |

### 마이그레이션 예시

**Excel:**
```python
excel_get_values(workbook_name="data.xlsx", sheet_name="Sheet1", range_str="A1:C10")
```

**Google Sheets:**
```python
gsheet_get_values_from_range(spreadsheet_id="1abc...", sheet_range="Sheet1!A1:C10")
```

## 고급 설정

### 사용자 정의 OAuth 앱 사용

**중요: 각 사용자는 반드시 자신의 Google Cloud 프로젝트에서 OAuth 클라이언트를 생성해야 합니다. 절대로 `google_client_secret.json` 파일을 공유하거나 공개 저장소에 커밋하지 마세요!**

#### 1. Google Cloud Console 설정

1. **프로젝트 생성**
   - [Google Cloud Console](https://console.cloud.google.com/)에서 새 프로젝트 생성 또는 기존 프로젝트 선택

2. **API 활성화**
   - "API 및 서비스" > "라이브러리"로 이동
   - "Google Sheets API" 검색 후 활성화
   - "Google Drive API"도 활성화 (파일 목록 조회용)

3. **OAuth 2.0 클라이언트 ID 생성**
   - "API 및 서비스" > "사용자 인증 정보"로 이동
   - "+ 사용자 인증 정보 만들기" > "OAuth 클라이언트 ID" 선택
   - **애플리케이션 유형**: "데스크톱 애플리케이션" 선택
   - **이름**: 임의의 이름 입력 (예: "pyhub-mcptools")
   - **승인된 JavaScript 원본**: 설정하지 않음 (데스크톱 앱이므로 불필요)
   - **승인된 리디렉션 URI**: `http://localhost` 추가
     - "URI 추가" 클릭 후 `http://localhost` 입력
     - 포트 번호는 입력하지 않음 (자동으로 사용 가능한 포트 선택됨)

4. **OAuth 동의 화면 설정** (중요!)
   - "API 및 서비스" > "OAuth 동의 화면"으로 이동
   - **사용자 유형**: "외부" 선택 후 "만들기"
   - **필수 정보 입력**:
     - 앱 이름: "pyhub-mcptools" (또는 원하는 이름)
     - 사용자 지원 이메일: 본인 이메일 주소
     - 개발자 연락처 정보: 본인 이메일 주소
   - "저장 후 계속" 클릭
   - **테스트 사용자 추가**:
     - "테스트 사용자" 탭으로 이동
     - "+ 사용자 추가" 클릭
     - **본인의 Google 계정 이메일 주소 추가**
     - "저장 후 계속" 클릭

5. **인증 정보 다운로드**
   - 생성된 OAuth 클라이언트에서 "JSON 다운로드" 클릭
   - 파일을 `google_client_secret.json` 이름으로 저장
   - **절대로 이 파일을 Git에 커밋하거나 공유하지 마세요!**

#### 2. 환경 변수 설정

```bash
GOOGLE_CLIENT_SECRET_PATH=/path/to/your/google_client_secret.json
```

## 문제 해결

### 일반적인 문제

#### 1. OAuth 동의 화면 오류
```
403 오류: access_denied
앱은 현재 테스트 중이며 개발자가 승인한 테스터만 앱에 액세스할 수 있습니다.
```

**해결방법:**
Google Cloud Console에서 OAuth 동의 화면을 설정하고 테스트 사용자에 본인 이메일을 추가해야 합니다:

1. [Google Cloud Console](https://console.cloud.google.com/) > "API 및 서비스" > "OAuth 동의 화면"
2. "외부" 사용자 유형 선택
3. 앱 이름, 사용자 지원 이메일, 개발자 연락처 정보 입력
4. "테스트 사용자" 탭에서 본인 Google 계정 이메일 추가

#### 2. 인증 오류
```
AuthenticationError: 인증 토큰을 갱신할 수 없습니다
```

**해결방법:**
```bash
# 저장된 토큰 삭제 후 재인증
rm -rf ~/.pyhub-mcptools/credentials/google_sheets_token.json
```

#### 3. 권한 오류
```
GoogleSheetsError: 권한이 없습니다
```

**해결방법:**
- 스프레드시트 소유자인지 확인
- 공유 설정에서 편집 권한이 있는지 확인

#### 4. API 할당량 초과
```
RateLimitError: API 호출 한도를 초과했습니다
```

**해결방법:**
- `GOOGLE_SHEETS_RATE_LIMIT` 값을 낮춤 (기본값: 300)
- 사용자 정의 OAuth 앱으로 더 높은 할당량 확보

#### 5. 스프레드시트를 찾을 수 없음
```
SpreadsheetNotFoundError: 요청한 리소스를 찾을 수 없습니다
```

**해결방법:**
- 스프레드시트 ID가 올바른지 확인
- 스프레드시트에 대한 접근 권한이 있는지 확인

### 로그 확인

문제 진단을 위해 로그를 확인할 수 있습니다:

```bash
# 디버그 모드로 실행
DEBUG=true USE_GOOGLE_SHEETS=1 uv run -m pyhub.mcptools tools-list -v 1
```

## 보안 고려사항

1. **토큰 저장**: 인증 토큰은 `~/.pyhub-mcptools/credentials/`에 저장되며, 파일 권한이 소유자만 읽기/쓰기로 설정됩니다.

2. **토큰 만료**: 토큰은 자동으로 갱신되며, 갱신 실패 시 재인증이 필요합니다.

3. **OAuth 스코프**: 최소 권한 원칙에 따라 필요한 스코프만 요청합니다:
   - `https://www.googleapis.com/auth/spreadsheets`: 스프레드시트 읽기/쓰기
   - `https://www.googleapis.com/auth/drive.metadata.readonly`: 파일 목록 조회

4. **네트워크 보안**: 모든 API 통신은 HTTPS를 통해 암호화됩니다.

## API 제한사항

- **속도 제한**: 분당 300회 요청 (조정 가능)
- **배치 크기**: 한 번에 최대 1000개 셀 처리
- **파일 크기**: Google Sheets 자체 제한 (셀 개수 500만개)
- **동시 접근**: 여러 사용자가 동시에 편집 가능

## 지원 및 문의

문제가 발생하거나 기능 개선 제안이 있으시면 GitHub Issues를 통해 문의해 주세요.

- GitHub: https://github.com/pyhub-kr/pyhub-mcptools
- 문서: https://mcp.pyhub.kr