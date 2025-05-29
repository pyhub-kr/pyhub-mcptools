# setup-add 명령 개선: Python 모듈 실행 방식 적용

## 문제점
기존 방식에서는 `setup-add` 명령이 다음과 같은 설정을 생성했습니다:

```json
{
    "mcpServers": {
        "pyhub.mcptools": {
            "command": "/Users/allieus/Work/pyhub-mcptools/.venv/bin/python3",
            "args": [
                "/Users/allieus/Work/pyhub-mcptools/pyhub/mcptools/__main__.py",
                "run",
                "stdio"
            ],
            "env": {}
        }
    }
}
```

이 방식의 문제점:
- `__main__.py`를 직접 실행하면 현재 작업 디렉토리가 `pyhub/mcptools/`가 됨
- 프로젝트 루트 기준의 상대 경로가 작동하지 않음

## 해결 방법

### 1. Python 모듈 실행 방식 사용 (-m 옵션)
`setup-add` 명령이 생성하는 설정을 다음과 같이 변경:

```json
{
    "mcpServers": {
        "pyhub.mcptools": {
            "command": "/Users/allieus/Work/pyhub-mcptools/.venv/bin/python3",
            "args": [
                "-m",
                "pyhub.mcptools",
                "run",
                "stdio"
            ],
            "env": {}
        }
    }
}
```

### 2. 구현 변경사항

#### pyhub/mcptools/core/cli.py
```python
if getattr(sys, "frozen", False):
    # 패키징된 실행 파일인 경우
    current_exe_path = sys.executable
    if transport == TransportChoices.STDIO:
        run_command = f"{current_exe_path} run stdio"
    else:
        run_command = f"{current_exe_path} run-sse-proxy {sse_url}"
else:
    # 개발 환경에서 소스 실행인 경우 - Python 모듈로 실행
    python_exe = sys.executable
    if transport == TransportChoices.STDIO:
        run_command = f"{python_exe} -m pyhub.mcptools run stdio"
    else:
        run_command = f"{python_exe} -m pyhub.mcptools run-sse-proxy {sse_url}"
```

## 장점

1. **작업 디렉토리 일관성**
   - `-m` 옵션을 사용하면 Python이 자동으로 프로젝트 루트에서 실행
   - 상대 경로가 예상대로 작동

2. **표준 Python 실행 방식**
   - Python 모듈 실행의 표준 방식 준수
   - 더 깔끔하고 이해하기 쉬운 명령어 구조

3. **유지보수성**
   - `__main__.py`에 작업 디렉토리 변경 코드가 불필요
   - 코드가 더 단순하고 명확

## 사용 예시

### 기존 설정 제거 및 재설정
```bash
# 기존 설정 제거
pyhub.mcptools setup-remove

# 새로운 방식으로 재설정
pyhub.mcptools setup-add
```

### 수동으로 실행 테스트
```bash
# 개발 환경에서 테스트
python -m pyhub.mcptools run stdio

# 또는 venv 활성화 후
python -m pyhub.mcptools run stdio
```

## 결론
이 변경으로 `setup-add` 명령이 생성하는 MCP 서버 설정이 더 안정적이고 표준적인 방식으로 작동하게 되었습니다. 프로젝트 루트 기준의 모든 경로가 올바르게 해석되어 파일 접근 문제가 해결됩니다.