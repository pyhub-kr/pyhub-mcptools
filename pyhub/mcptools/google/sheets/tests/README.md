# Google Sheets MCP Tools 테스트

이 디렉토리는 Google Sheets MCP 도구들에 대한 pytest 기반 테스트를 포함합니다.

## 테스트 구조

- `test_basic_operations.py` - 기본 CRUD 작업 테스트
- `test_batch_operations.py` - 배치 및 청크 작업 테스트
- `test_error_handling.py` - 에러 처리 및 예외 상황 테스트
- `test_integration.py` - 통합 테스트 및 워크플로우 테스트
- `conftest.py` - pytest 설정 및 fixtures

## 환경 설정

테스트 실행 전 다음 환경 변수를 설정해야 합니다:

```bash
export USE_GOOGLE_SHEETS=1
export GOOGLE_CLIENT_SECRET_PATH=./google_client_secret.json
```

## 테스트 실행

### 의존성 설치
```bash
pip install -r requirements-test.txt
```

### 전체 테스트 실행
```bash
# 느린 테스트 제외하고 실행
pytest pyhub/mcptools/google/sheets/tests/ -v -m "not slow"

# 모든 테스트 실행
pytest pyhub/mcptools/google/sheets/tests/ -v
```

### 특정 테스트 실행
```bash
# 기본 작업만 테스트
pytest pyhub/mcptools/google/sheets/tests/test_basic_operations.py -v

# 배치 작업만 테스트
pytest pyhub/mcptools/google/sheets/tests/test_batch_operations.py -v -m batch

# 에러 처리만 테스트
pytest pyhub/mcptools/google/sheets/tests/test_error_handling.py -v -m error_handling

# 통합 테스트만 실행
pytest pyhub/mcptools/google/sheets/tests/test_integration.py -v -m integration
```

### Makefile 사용
```bash
# 도움말 보기
make -f Makefile.sheets help

# 기본 테스트 실행
make -f Makefile.sheets test

# 모든 테스트 실행 (느린 테스트 포함)
make -f Makefile.sheets test-all

# 병렬로 테스트 실행
make -f Makefile.sheets test-parallel

# 커버리지와 함께 테스트 실행
make -f Makefile.sheets test-coverage
```

## 테스트 마커

- `@pytest.mark.integration` - 실제 Google Sheets API를 사용하는 통합 테스트
- `@pytest.mark.batch` - 배치 작업 테스트
- `@pytest.mark.error_handling` - 에러 처리 테스트
- `@pytest.mark.slow` - 느리게 실행되는 테스트
- `@pytest.mark.asyncio` - 비동기 테스트

## 주의사항

1. **실제 API 사용**: 이 테스트들은 실제 Google Sheets API를 사용합니다.
2. **테스트 스프레드시트**: 테스트 실행 시 Google Drive에 테스트용 스프레드시트가 생성됩니다.
3. **수동 정리**: 테스트 완료 후 생성된 스프레드시트는 수동으로 삭제해야 합니다.
4. **API 할당량**: 많은 테스트를 연속으로 실행하면 Google API 할당량에 도달할 수 있습니다.

## 예시 테스트 실행

```bash
# 환경 변수 설정
export USE_GOOGLE_SHEETS=1
export GOOGLE_CLIENT_SECRET_PATH=./google_client_secret.json

# 빠른 테스트만 실행
pytest pyhub/mcptools/google/sheets/tests/ -v -m "not integration and not slow"

# 통합 테스트만 실행
pytest pyhub/mcptools/google/sheets/tests/ -v -m integration

# 특정 테스트 함수만 실행
pytest pyhub/mcptools/google/sheets/tests/test_basic_operations.py::test_write_and_read_data -v
```

## 트러블슈팅

### Django 설정 오류
- `conftest.py`에서 Django 설정이 자동으로 처리됩니다.

### 환경 변수 오류
- `USE_GOOGLE_SHEETS=1`과 `GOOGLE_CLIENT_SECRET_PATH`가 설정되어 있는지 확인하세요.

### API 인증 오류
- `google_client_secret.json` 파일이 올바른 경로에 있는지 확인하세요.
- Google Cloud Console에서 API가 활성화되어 있는지 확인하세요.

### 의존성 오류
- `pip install -r requirements-test.txt`로 테스트 의존성을 설치하세요.