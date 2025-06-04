# PyHub MCP Tools Docker Image
FROM python:3.13-slim

# 메타데이터
LABEL maintainer="Chinseok Lee <me@pyhub.kr>"
LABEL description="PyHub MCP Tools - 파이썬사랑방 MCP 도구"
LABEL version="0.9.7a3"

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    # Build tools
    build-essential \
    # Git for potential git-based dependencies
    git \
    # Cleanup
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 관리 도구 설치
RUN pip install --no-cache-dir uv

# 애플리케이션 파일 복사
COPY pyproject.toml ./
COPY README.md ./
COPY pyhub/ ./pyhub/

# Python 의존성 설치
RUN uv venv && \
    . .venv/bin/activate && \
    uv pip install -e ".[all]"

# 비root 사용자 생성
RUN groupadd -r mcpuser && useradd -r -g mcpuser -m mcpuser
RUN chown -R mcpuser:mcpuser /app
USER mcpuser

# 환경변수 설정
ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:$PATH"

# 포트 노출 (MCP 서버가 사용할 포트)
EXPOSE 8000

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import pyhub.mcptools; print('OK')" || exit 1

# 실행 명령
CMD [".venv/bin/python", "-m", "pyhub.mcptools"]