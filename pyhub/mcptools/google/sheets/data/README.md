# Google Sheets 크레덴셜 데이터 디렉토리

이 디렉토리는 배포용 OAuth 크레덴셜을 저장하는 곳입니다.

## 배포 프로세스

1. **개발자 전용 크레덴셜 준비**
    ```bash
    # 실제 google_client_secret.json을 암호화
    python scripts/encrypt_credentials.py
    ```

2. **암호화된 파일 생성**
    - `encrypted_client_secret.bin` - 암호화된 크레덴셜
    - 빌드 시에만 복호화 키 접근 가능

3. **설치 시 복호화**
    - 설치 프로그램이 적절한 위치에 복호화하여 저장

## 주의사항

- 이 디렉토리의 실제 크레덴셜은 절대 Git에 커밋하지 마세요
- `.gitignore`에 포함되어 있는지 확인하세요
