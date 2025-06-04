#!/bin/bash

# PyHub MCP Tools Docker Entrypoint Script
set -e

echo "Starting PyHub MCP Tools..."
echo "Version: $(python -c 'import pyhub.mcptools; from pyhub.mcptools.core.versions import PackageVersionChecker; print(PackageVersionChecker.get_installed_version("pyhub-mcptools"))')"

# 환경변수 검증
if [ -z "$OPENAI_API_KEY" ] && [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "Warning: No API keys configured. Some features may not work."
fi

# 데이터 디렉토리 권한 확인
if [ -d "/app/data" ]; then
    echo "Data directory found: /app/data"
else
    echo "Creating data directory..."
    mkdir -p /app/data
fi

# 로그 디렉토리 확인
if [ -d "/app/logs" ]; then
    echo "Logs directory found: /app/logs"
else
    echo "Creating logs directory..."
    mkdir -p /app/logs
fi

# MCP 도구 실행
echo "Launching MCP Tools..."
exec "$@"