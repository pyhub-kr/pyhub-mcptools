# Microsoft Tools

Microsoft 애플리케이션과의 통합을 위한 MCP 도구들입니다.

## Outlook Tools

Microsoft Outlook과의 이메일 작업을 위한 도구입니다.

### 통합 도구 (권장)

#### `outlook`

모든 Outlook 이메일 작업을 위한 통합 도구입니다.

**Parameters:**
- `operation`: 수행할 작업 ("list", "get", "send")
- List 작업 파라미터:
  - `max_hours`: 조회할 최대 시간 범위 (기본값: 24)
  - `query`: 제목으로 필터링할 검색어
  - `folder`: 이메일 폴더 (inbox, sent, drafts, trash 또는 사용자 정의 폴더명)
- Get 작업 파라미터:
  - `identifier`: 조회할 이메일의 고유 식별자
- Send 작업 파라미터:
  - `subject`: 이메일 제목
  - `message`: 이메일 본문 (텍스트)
  - `from_email`: 발신자 이메일 주소
  - `recipient_list`: 수신자 이메일 주소 (쉼표로 구분)
  - `html_message`: HTML 본문 (선택사항)
  - `cc_list`: 참조 수신자 (선택사항, 쉼표로 구분)
  - `bcc_list`: 숨은 참조 수신자 (선택사항, 쉼표로 구분)
  - `compose_only`: true로 설정 시 작성 창만 열기

**Examples:**

```python
# 이메일 목록 조회
await outlook(
    operation="list",
    max_hours=48,
    query="meeting",
    folder="inbox"
)

# 특정 이메일 조회
await outlook(
    operation="get",
    identifier="123456"
)

# 이메일 전송
await outlook(
    operation="send",
    subject="프로젝트 업데이트",
    message="안녕하세요, 프로젝트 진행 상황을 공유드립니다.",
    from_email="sender@example.com",
    recipient_list="team@example.com",
    cc_list="manager@example.com"
)

# 작성 창만 열기
await outlook(
    operation="send",
    subject="초안",
    message="초안 내용",
    from_email="sender@example.com",
    recipient_list="recipient@example.com",
    compose_only=True
)
```


## 플랫폼 지원

- **Windows**: 완전 지원 (COM 인터페이스 사용)
- **macOS**: 완전 지원 (AppleScript 사용)

## 주의사항

- 처음 사용 시 Outlook 앱에 대한 접근 권한을 요청할 수 있습니다
- Outlook 앱이 설치되어 있고 계정이 설정되어 있어야 합니다
- 이메일 폴더명은 시스템 언어에 따라 다를 수 있습니다