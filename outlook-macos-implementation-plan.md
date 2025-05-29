# macOS Outlook 구현 계획

## 구현 가능성 검토 결과

### ✅ 구현 가능한 기능들

1. **이메일 목록 조회** (get_emails)
   - 폴더별 이메일 조회
   - 검색 필터 적용
   - 이메일 메타데이터 (제목, 발신자, 날짜 등)

2. **이메일 상세 조회** (get_email)
   - 이메일 본문 (텍스트/HTML)
   - 첨부파일 정보
   - 전체 헤더 정보

3. **이메일 발송** (send_email)
   - 계정 선택
   - To/CC/BCC 설정
   - 첨부파일 추가
   - HTML 이메일 (제한적)

4. **폴더 관리**
   - 폴더 목록 조회
   - 폴더 ID 조회

### ⚠️ 제한사항

1. **HTML 이메일**
   - 복잡한 HTML 템플릿 직접 설정 어려움
   - RTF 또는 텍스트로 우회 필요

2. **대량 데이터 처리**
   - AppleScript 성능 한계
   - 대량 이메일 조회 시 타임아웃 가능

3. **실시간 동기화**
   - Windows의 SendAndReceive 같은 직접적인 동기화 명령 없음

## 구현 방안

### 1. 프로젝트 구조

```
pyhub/mcptools/email/
├── outlook/
│   ├── macos.py          # 주요 구현
│   └── templates/         # AppleScript 템플릿 (신규)
│       ├── get_emails.applescript
│       ├── get_email_detail.applescript
│       ├── send_email.applescript
│       └── helpers.applescript
```

### 2. 핵심 함수 구현 계획

#### 2.1 get_emails() 완성

```python
def get_emails(
    max_hours: int = 12,
    query: Optional[str] = None,
    email_folder_type: Optional[EmailFolderType] = None,
    email_folder_name: Optional[str] = None,
    connection: Optional[Any] = None,  # macOS에서는 사용 안함
) -> list[Email]:
    """이메일 목록 조회 - Windows와 동일한 인터페이스"""

    # AppleScript 템플릿 사용
    template = get_template("get_emails.applescript")
    context = {
        'max_hours': max_hours,
        'query': query,
        'folder_type': email_folder_type,
        'folder_name': email_folder_name,
    }

    script = template.render(**context)
    result = applescript_run_sync(script)

    # CSV 형식 파싱
    return parse_email_list(result)
```

#### 2.2 get_email() 구현

```python
def get_email(
    identifier: str,
    connection: Optional[Any] = None,
) -> Email:
    """특정 이메일 상세 조회"""

    template = get_template("get_email_detail.applescript")
    script = template.render(email_id=identifier)
    result = applescript_run_sync(script)

    return parse_email_detail(result)
```

#### 2.3 send_email() 구현

```python
def send_email(
    subject: str,
    message: str,
    from_email: str,
    recipient_list: list[str],
    html_message: Optional[str] = None,
    cc_list: Optional[list[str]] = None,
    bcc_list: Optional[list[str]] = None,
    connection: Optional[Any] = None,
    force_sync: bool = True,  # macOS에서는 무시
) -> bool:
    """이메일 발송 - Windows와 동일한 인터페이스"""

    template = get_template("send_email.applescript")
    context = {
        'subject': escape_applescript_string(subject),
        'message': escape_applescript_string(message),
        'from_email': from_email,
        'recipients': recipient_list,
        'cc_list': cc_list or [],
        'bcc_list': bcc_list or [],
        'use_html': bool(html_message),
    }

    script = template.render(**context)
    result = applescript_run_sync(script)

    return "SUCCESS" in result
```

### 3. AppleScript 템플릿 예시

#### get_emails.applescript

```applescript
tell application "Microsoft Outlook"
    {% if folder_name %}
    set targetFolder to folder "{{ folder_name }}"
    {% else %}
    set targetFolder to inbox
    {% endif %}

    set cutoffDate to (current date) - ({{ max_hours }} * hours)
    set messageList to messages of targetFolder whose time received > cutoffDate

    {% if query %}
    set filteredList to {}
    repeat with aMessage in messageList
        if subject of aMessage contains "{{ query }}" then
            set end of filteredList to aMessage
        end if
    end repeat
    set messageList to filteredList
    {% endif %}

    set csvData to ""
    repeat with aMessage in messageList
        set msgId to id of aMessage as string
        set msgSubject to my escape_csv(subject of aMessage)
        set msgSender to my escape_csv(name of sender of aMessage)
        set msgSenderEmail to email address of address of sender of aMessage
        set msgDate to (time received of aMessage) as string

        set csvLine to msgId & "," & msgSubject & "," & msgSender & "," & msgSenderEmail & "," & msgDate
        set csvData to csvData & csvLine & linefeed
    end repeat

    return csvData
end tell

on escape_csv(str)
    if str contains "," or str contains "\"" or str contains linefeed then
        set str to "\"" & my replace_text(str, "\"", "\"\"") & "\""
    end if
    return str
end escape_csv
```

#### send_email.applescript

```applescript
tell application "Microsoft Outlook"
    set theMessage to make new outgoing message with properties {subject:"{{ subject }}", content:"{{ message }}"}

    {% if from_email %}
    set theAccount to first exchange account whose email address is "{{ from_email }}"
    set account of theMessage to theAccount
    {% endif %}

    {% for recipient in recipients %}
    make new recipient at theMessage with properties {email address:{address:"{{ recipient }}"}}
    {% endfor %}

    {% for cc in cc_list %}
    make new cc recipient at theMessage with properties {email address:{address:"{{ cc }}"}}
    {% endfor %}

    {% for bcc in bcc_list %}
    make new bcc recipient at theMessage with properties {email address:{address:"{{ bcc }}"}}
    {% endfor %}

    send theMessage
    return "SUCCESS"
end tell
```

### 4. 유틸리티 함수

```python
def parse_email_list(csv_data: str) -> list[Email]:
    """CSV 데이터를 Email 객체 리스트로 변환"""
    emails = []
    for line in csv.reader(csv_data.strip().splitlines()):
        if len(line) >= 5:
            email = Email(
                identifier=line[0],
                subject=line[1],
                sender_name=line[2],
                sender_email=line[3],
                received_at=parse_outlook_date(line[4]),
            )
            emails.append(email)
    return emails

def escape_applescript_string(text: str) -> str:
    """AppleScript 문자열 이스케이프"""
    return text.replace('"', '\\"').replace('\n', '\\n')
```

### 5. 구현 우선순위

1. **Phase 1** (즉시)
   - get_emails() 완성
   - get_email() 구현
   - 기본 에러 처리

2. **Phase 2** (다음)
   - send_email() 구현
   - 첨부파일 처리
   - 계정 선택 기능

3. **Phase 3** (추후)
   - HTML 이메일 개선
   - 성능 최적화
   - 캐싱 메커니즘

### 6. 테스트 계획

1. **단위 테스트**
   - AppleScript 템플릿 렌더링
   - CSV 파싱 로직
   - 날짜 변환 함수

2. **통합 테스트**
   - 실제 Outlook 연동
   - 다양한 이메일 형식 처리
   - 에러 시나리오

## 결론

macOS Outlook은 AppleScript를 통해 Windows 버전과 거의 동일한 기능을 구현할 수 있습니다. Excel 모듈의 패턴을 따라 템플릿 기반 접근과 구조화된 데이터 파싱을 사용하면 안정적이고 유지보수가 쉬운 구현이 가능합니다.

주요 차이점은:
- COM 대신 AppleScript 사용
- 연결 관리가 불필요 (connection 파라미터 무시)
- HTML 이메일 처리에 약간의 제약

하지만 MCP tools의 인터페이스 관점에서는 Windows와 동일하게 동작하도록 구현 가능합니다.