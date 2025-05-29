# Apple Native Apps MCP Tools

Apple 네이티브 앱들과 통합된 MCP 도구들을 제공합니다. macOS에서만 사용 가능하며, AppleScript를 통해 시스템 앱들과 상호작용합니다.

!!! warning "실험적 기능"
    이 도구들은 실험적(experimental) 기능입니다. 사용하려면 환경변수 `PYHUB_MCPTOOLS_EXPERIMENTAL=1`을 설정해야 합니다.

## 사용 가능한 도구들

### 1. Apple Mail

이메일 발송 및 조회 기능을 제공합니다.

- **`apple_mail`**: 이메일 발송 및 목록 조회
  - Operations: `send`, `list`

### 2. Apple Messages

메시지 앱을 통한 SMS/iMessage 기능을 제공합니다.

- **`apple_messages`**: 메시지 발송, 예약, 읽지 않은 메시지 확인
  - Operations: `send`, `schedule`, `unread`
  - **참고**: macOS 개인정보 보호 정책으로 인해 메시지 내용 읽기 기능은 지원되지 않습니다.

### 3. Apple Notes

노트 앱의 노트 관리 기능을 제공합니다.

- **`apple_notes`**: 노트 목록, 검색, 생성, 조회, 폴더 관리
  - Operations: `list`, `search`, `create`, `get`, `folders`

### 4. Apple Contacts

연락처 앱의 연락처 관리 기능을 제공합니다.

- **`apple_contacts`**: 연락처 검색, 조회, 생성
  - Operations: `search`, `get`, `create`

## 설정 방법

### 1. 실험적 기능 활성화

```bash
# 환경변수 설정
export PYHUB_MCPTOOLS_EXPERIMENTAL=1

# 또는 .env 파일에 추가
echo "PYHUB_MCPTOOLS_EXPERIMENTAL=1" >> ~/.pyhub.mcptools/.env
```

### 2. Claude Desktop 설정

Claude Desktop의 설정에서 Apple 도구들이 활성화되도록 설정합니다:

```bash
# 설정 추가
pyhub.mcptools setup-add --experimental
```

### 3. 권한 설정

macOS에서 각 앱에 대한 자동화 권한이 필요합니다. 첫 실행 시 권한 요청 대화상자가 표시됩니다.

## 사용 예제

### Mail 사용 예제

```python
# 이메일 발송
result = await apple_mail(
    operation="send",
    subject="회의 안내",
    message="내일 오후 3시에 회의가 있습니다.",
    from_email="me@example.com",
    recipient_list="team@example.com, boss@example.com",
    cc_list="colleague@example.com"
)

# 이메일 목록 조회
emails = await apple_mail(
    operation="list",
    folder="inbox",
    max_hours=48,
    query="프로젝트"
)
```

### Messages 사용 예제

```python
# 메시지 발송
result = await apple_messages(
    operation="send",
    phone_number="+1234567890",
    message="안녕하세요!",
    service="iMessage"
)

# 메시지 예약 (주의: 시간대 이슈 있음)
result = await apple_messages(
    operation="schedule",
    phone_number="+821012345678",
    message="예약 메시지",
    scheduled_time="2025-05-30T18:00:00+09:00"
)
# ⚠️ 경고: macOS와 iOS의 Reminders 앱 간 시간대 처리 차이로 인해
# 예약 시간이 각 기기에서 다르게 표시될 수 있습니다.

# 읽지 않은 메시지 수 확인
unread = await apple_messages(operation="unread")
```

### Notes 사용 예제

```python
# 노트 생성
result = await apple_notes(
    operation="create",
    title="회의 메모",
    body="오늘 회의 내용입니다...",
    folder_name="Work"
)

# 노트 검색
notes = await apple_notes(
    operation="search",
    search_text="회의",
    limit=5
)

# 폴더 목록
folders = await apple_notes(operation="folders")
```

### Contacts 사용 예제

```python
# 연락처 검색
contacts = await apple_contacts(
    operation="search",
    name="홍길동",
    limit=10
)

# 연락처 생성
result = await apple_contacts(
    operation="create",
    first_name="홍",
    last_name="길동",
    email="hong@example.com",
    phone="+82-10-1234-5678"
)
```

## 주의사항

1. **macOS 전용**: 이 도구들은 macOS에서만 작동합니다.
2. **권한 필요**: 각 앱에 대한 자동화 권한이 필요합니다.
3. **실험적 기능**: 안정성이 완전히 보장되지 않습니다.
4. **AppleScript 의존**: 시스템 언어 설정에 따라 동작이 달라질 수 있습니다.

## 문제 해결

### 권한 오류

"System Events got an error: pyhub.mcptools is not allowed assistive access" 오류가 발생하면:

1. 시스템 설정 > 개인정보 보호 및 보안 > 손쉬운 사용
2. pyhub.mcptools 또는 Claude Desktop 추가
3. 체크박스 활성화

### AppleScript 오류

AppleScript 실행 오류가 발생하면:

1. 해당 앱이 실행 중인지 확인
2. 시스템 언어가 영어로 설정되어 있는지 확인
3. 앱의 자동화 권한이 허용되어 있는지 확인