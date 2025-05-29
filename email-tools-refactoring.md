# Email Tools COM 초기화 리팩토링

## 개요
Windows에서 반복되는 COM 초기화 코드를 `run_with_com_if_windows` 헬퍼 함수로 통합하여 코드 중복을 제거했습니다.

## 리팩토링 전 (예시)
```python
if OS.current_is_windows():
    def _get_emails_in_thread():
        import pythoncom
        pythoncom.CoInitialize()
        try:
            return outlook.get_emails(
                max_hours=max_hours,
                query=query or None,
                email_folder_type=EmailFolderType.INBOX,
            )
        finally:
            pythoncom.CoUninitialize()

    loop = asyncio.get_event_loop()
    email_list = await loop.run_in_executor(_com_thread_pool, _get_emails_in_thread)
else:
    # macOS doesn't need COM threading
    email_list = await sync_to_async(outlook.get_emails)(
        max_hours=max_hours,
        query=query or None,
        email_folder_type=EmailFolderType.INBOX,
    )
```

## 리팩토링 후
```python
email_list = await run_with_com_if_windows(
    outlook.get_emails,
    max_hours=max_hours,
    query=query or None,
    email_folder_type=EmailFolderType.INBOX,
)
```

## 구현된 헬퍼 함수
```python
async def run_with_com_if_windows(func: Callable[..., T], *args, **kwargs) -> T:
    """
    Windows에서는 COM 초기화와 함께 전용 스레드에서 실행하고,
    다른 OS에서는 일반 async로 실행
    """
    if OS.current_is_windows():
        def _run_in_com_thread():
            import pythoncom
            pythoncom.CoInitialize()
            try:
                return func(*args, **kwargs)
            finally:
                pythoncom.CoUninitialize()

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_com_thread_pool, _run_in_com_thread)
    else:
        # macOS/Linux doesn't need COM threading
        return await sync_to_async(func)(*args, **kwargs)
```

## 장점

1. **코드 중복 제거**
   - 3개의 함수에서 반복되던 COM 초기화 코드를 하나로 통합
   - 약 60줄의 코드가 15줄로 감소

2. **유지보수성 향상**
   - COM 초기화 로직이 한 곳에 집중됨
   - 변경사항이 있을 때 한 곳만 수정하면 됨

3. **가독성 개선**
   - 비즈니스 로직에 집중할 수 있음
   - 플랫폼별 처리가 추상화됨

4. **타입 안전성**
   - TypeVar를 사용하여 제네릭 타입 지원
   - 함수의 반환 타입이 보존됨

## 적용된 함수들

1. `outlook__list_recent_inbox_emails`
2. `outlook__get_email`
3. `outlook__send_email`

모든 Outlook 관련 함수들이 이제 동일한 패턴으로 COM 초기화를 처리합니다.