# Windows Outlook 안정성 개선 방안

## 1. COM 접근 안정성 개선

### 현재 문제점
- `pythoncom.CoInitialize()` 호출 후 `CoUninitialize()` 미호출
- COM 에러 처리가 너무 일반적
- 타임아웃 처리 없음

### 개선 코드

```python
import pythoncom
import pywintypes
from contextlib import contextmanager
import time
from typing import Optional, Generator

@contextmanager
def outlook_connection(timeout: int = 30) -> Generator[OutlookConnection, None, None]:
    """개선된 Outlook 연결 관리자

    Args:
        timeout: 연결 타임아웃 (초)
    """
    pythoncom.CoInitialize()
    application = None

    try:
        # COM 객체 생성 재시도 로직
        for attempt in range(3):
            try:
                application = win32com.client.Dispatch("Outlook.Application")
                break
            except pywintypes.com_error as e:
                if attempt == 2:
                    raise
                time.sleep(1)

        # MAPI 연결
        outlook = application.GetNamespace("MAPI")

        # 연결 확인 (폴더 접근 테스트)
        try:
            _ = outlook.GetDefaultFolder(6)  # olFolderInbox
        except pywintypes.com_error:
            raise ConnectionError("Outlook MAPI 연결 실패")

        yield OutlookConnection(application=application, outlook=outlook)

    except pywintypes.com_error as e:
        error_code = e.args[0] if e.args else None
        if error_code == -2147221005:  # 0x800401F3
            raise RuntimeError("Outlook이 설치되지 않았거나 접근할 수 없습니다")
        else:
            raise RuntimeError(f"Outlook COM 오류: {e}")
    finally:
        # COM 리소스 정리
        if application:
            try:
                # Outlook 객체 릴리즈
                del application
            except:
                pass
        pythoncom.CoUninitialize()
```

## 2. 이메일 발송 Outbox 문제 해결

### 현재 문제점
- `Send()` 호출 후 실제 발송 확인 없음
- Outlook 동기화 상태 미확인
- 오프라인 모드 처리 없음

### 개선 코드

```python
def send_email(
    to: str,
    subject: str,
    body: str,
    cc: Optional[str] = None,
    bcc: Optional[str] = None,
    body_format: BodyFormat = "html",
    from_email: Optional[str] = None,
    connection: Optional[OutlookConnection] = None,
    force_sync: bool = True,  # 새 파라미터
) -> bool:
    """개선된 이메일 발송 함수"""

    if connection is None:
        with outlook_connection() as conn:
            return send_email(
                to=to, subject=subject, body=body, cc=cc, bcc=bcc,
                body_format=body_format, from_email=from_email,
                connection=conn, force_sync=force_sync
            )

    application = connection.application
    outlook = connection.outlook

    # 온라인 상태 확인
    if not outlook.Offline:
        # 동기화 강제 실행
        if force_sync:
            try:
                outlook.SendAndReceive(False)  # 백그라운드 동기화
            except:
                pass

    # 메일 생성
    mail = application.CreateItem(OutlookItemType.olMailItem)

    # ... 기존 메일 설정 코드 ...

    # 발송 전 저장
    mail.Save()

    # 발송
    try:
        mail.Send()

        # 발송 확인 (Outbox 체크)
        if force_sync:
            outbox = outlook.GetDefaultFolder(4)  # olFolderOutbox
            start_time = time.time()

            # 최대 10초간 Outbox 확인
            while time.time() - start_time < 10:
                outbox_items = outbox.Items
                found = False

                for item in outbox_items:
                    if item.Subject == subject and item.To == to:
                        found = True
                        break

                if not found:
                    # Outbox에서 사라짐 = 발송됨
                    return True

                # 수동 동기화 시도
                try:
                    outlook.SendAndReceive(True)  # 대기하며 동기화
                except:
                    pass

                time.sleep(1)

            # 10초 후에도 Outbox에 있으면 경고
            logger.warning(f"이메일이 Outbox에 남아있습니다: {subject}")

    except pywintypes.com_error as e:
        logger.error(f"이메일 발송 실패: {e}")
        raise

    return True
```

## 3. 추가 안정성 개선사항

### 3.1 에러 복구 메커니즘

```python
def safe_folder_access(folder_func, default=None, max_retries=3):
    """폴더 접근 시 안전한 재시도 로직"""
    for attempt in range(max_retries):
        try:
            return folder_func()
        except pywintypes.com_error as e:
            if attempt == max_retries - 1:
                if default is not None:
                    return default
                raise
            time.sleep(0.5 * (attempt + 1))
```

### 3.2 연결 상태 모니터링

```python
class OutlookConnectionPool:
    """연결 풀링 및 상태 관리"""

    def __init__(self):
        self._connection = None
        self._last_check = 0

    def get_connection(self):
        now = time.time()

        # 30초마다 연결 상태 확인
        if self._connection and now - self._last_check > 30:
            if not self._check_connection():
                self._connection = None

        if not self._connection:
            self._connection = self._create_connection()

        self._last_check = now
        return self._connection

    def _check_connection(self):
        """연결 상태 확인"""
        try:
            # 간단한 작업으로 연결 테스트
            self._connection.outlook.GetDefaultFolder(6)
            return True
        except:
            return False
```

### 3.3 비동기 처리 개선

```python
# tools.py 개선
@tool
async def outlook__send_email(...):
    """개선된 비동기 이메일 발송"""
    # COM은 STA 스레드에서만 동작하므로 전용 스레드 풀 사용
    loop = asyncio.get_event_loop()

    # ThreadPoolExecutor를 사용하여 별도 스레드에서 실행
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = loop.run_in_executor(
            executor,
            lambda: _send_email_in_thread(to, subject, body, ...)
        )
        return await future

def _send_email_in_thread(...):
    """별도 스레드에서 COM 초기화 후 실행"""
    pythoncom.CoInitialize()
    try:
        return outlook.send_email(...)
    finally:
        pythoncom.CoUninitialize()
```

## 4. 구현 우선순위

1. **즉시 적용 가능**
   - COM 초기화/해제 개선
   - 에러 처리 세분화
   - 발송 후 Outbox 확인 로직

2. **단계적 적용**
   - 연결 풀링
   - 재시도 로직
   - 타임아웃 처리

3. **장기 개선**
   - 완전한 비동기 처리
   - 상태 모니터링
   - 로깅 강화

## 5. 테스트 시나리오

1. **Outlook 미설치 환경**
2. **Outlook 오프라인 모드**
3. **대량 메일 발송**
4. **동시 다발적 요청**
5. **네트워크 불안정 상황**

이러한 개선사항들을 적용하면 COM 접근 안정성과 이메일 발송 신뢰성이 크게 향상될 것입니다.