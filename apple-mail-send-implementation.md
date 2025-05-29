# Apple Mail 이메일 발송 기능 구현

## 개요
Apple Mail에 이메일 발송 기능을 추가했습니다. Outlook과 동일한 인터페이스를 제공하여 일관성을 유지했습니다.

## 구현된 기능

### 1. apple_mail 모듈 (`pyhub/mcptools/email/apple_mail/__init__.py`)
```python
async def send_email(
    subject: str,
    message: str,
    from_email: str,
    recipient_list: list[str],
    html_message: Optional[str] = None,
    cc_list: Optional[list[str]] = None,
    bcc_list: Optional[list[str]] = None,
    connection: Optional[any] = None,  # For compatibility
    force_sync: bool = True,  # For compatibility
) -> bool:
```

#### 주요 특징
- **Outlook과 동일한 인터페이스**: 모든 매개변수가 Outlook과 동일
- **AppleScript 활용**: macOS 네이티브 스크립팅
- **계정 자동 선택**: from_email과 일치하는 계정 자동 찾기
- **다중 수신자 지원**: TO, CC, BCC 모두 지원
- **HTML 변환**: HTML 메시지는 plain text로 자동 변환

### 2. MCP Tool (`pyhub/mcptools/email/tools.py`)
```python
@mcp.tool(enabled=OS.current_is_macos(), experimental=EXPERIMENTAL)
async def apple_mail__send_email(
    subject: str,
    message: str,
    from_email: str,
    recipient_list: str,  # Comma-separated
    html_message: str = "",
    cc_list: str = "",
    bcc_list: str = "",
) -> dict[str, bool]:
```

#### 특징
- **macOS 전용**: `OS.current_is_macos()`로 활성화
- **쉼표 구분 목록**: MCP 인터페이스는 문자열로 받아서 파싱
- **성공 여부 반환**: `{"success": true/false}`

## AppleScript 구현 세부사항

### 1. 메시지 생성
```applescript
set newMessage to make new outgoing message with properties {
    subject:"제목",
    content:"내용"
}
```

### 2. 발신 계정 설정
```applescript
repeat with acc in accounts
    set accEmails to email addresses of acc
    repeat with accEmail in accEmails
        if accEmail as string is equal to "sender@email.com" then
            set sender of newMessage to acc
            exit repeat
        end if
    end repeat
end repeat
```

### 3. 수신자 추가
```applescript
tell newMessage
    make new to recipient with properties {address:"recipient@email.com"}
    make new cc recipient with properties {address:"cc@email.com"}
    make new bcc recipient with properties {address:"bcc@email.com"}
end tell
```

### 4. 메시지 발송
```applescript
send newMessage
```

## 제한사항

1. **HTML 이메일**
   - AppleScript가 직접적인 HTML 설정을 지원하지 않음
   - HTML은 plain text로 변환되어 발송됨
   - 향후 RTF 형식 지원 검토 필요

2. **첨부파일**
   - 현재 미구현
   - AppleScript로는 구현 가능하나 추가 작업 필요

3. **발송 확인**
   - 동기 발송만 지원
   - 발송 상태 추적 제한적

## 사용 예시

### Python 직접 호출
```python
import asyncio
from pyhub.mcptools.email import apple_mail

async def main():
    success = await apple_mail.send_email(
        subject="테스트 이메일",
        message="이것은 테스트 메시지입니다.",
        from_email="sender@icloud.com",
        recipient_list=["recipient@example.com"],
        cc_list=["cc@example.com"],
    )
    print(f"발송 성공: {success}")

asyncio.run(main())
```

### MCP Tool 사용
```python
# Claude 또는 MCP 클라이언트에서
result = await apple_mail__send_email(
    subject="테스트 이메일",
    message="이것은 테스트 메시지입니다.",
    from_email="sender@icloud.com",
    recipient_list="recipient1@example.com, recipient2@example.com",
    cc_list="cc@example.com",
)
print(result)  # {"success": true}
```

## 향후 개선사항

1. **첨부파일 지원**
   ```applescript
   make new attachment with properties {file name:"/path/to/file"}
   ```

2. **RTF/HTML 지원 개선**
   - RTF 형식으로 서식 있는 이메일 지원
   - HTML to RTF 변환기 구현

3. **발송 상태 추적**
   - 발송 큐 모니터링
   - 실패 시 상세 에러 메시지

4. **템플릿 시스템**
   - 이메일 템플릿 지원
   - 서명 자동 추가

## 결론

Apple Mail 이메일 발송 기능이 성공적으로 구현되었습니다. Outlook과 동일한 인터페이스를 제공하여 사용자가 플랫폼에 관계없이 일관된 경험을 할 수 있습니다. AppleScript의 제약으로 인해 일부 고급 기능은 제한적이지만, 기본적인 이메일 발송 기능은 완벽하게 작동합니다.