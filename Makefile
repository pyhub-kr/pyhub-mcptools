.PHONY: test clean build publish docs docs-build

test:
	uv pip install -e ".[all,dev]"
	uv run pytest $(filter-out $@,$(MAKECMDGOALS))

format:
	uv pip install -e ".[all,dev]"
	uv run black $(or $(filter-out $@,$(MAKECMDGOALS)),./pyhub)
	uv run isort $(or $(filter-out $@,$(MAKECMDGOALS)),./pyhub)
	uv run ruff check $(or $(filter-out $@,$(MAKECMDGOALS)),./pyhub) --fix

lint:
	uv pip install -e ".[all,dev]"
	uv run black $(or $(filter-out $@,$(MAKECMDGOALS)),./pyhub) --check
	uv run isort $(or $(filter-out $@,$(MAKECMDGOALS)),./pyhub) --check
	uv run ruff check $(or $(filter-out $@,$(MAKECMDGOALS)),./pyhub)
	uv run djlint $(or $(filter-out $@,$(MAKECMDGOALS)),./pyhub) --check

clean:
	find . -name __pycache__ | xargs rm -rf
	rm -rf dist/ build/ *.egg-info *.spec .pytest_cache .mypy_cache .ruff_cache

build: clean
	uv pip install -e ".[build]"
	uv run -m build --wheel

publish: build
	uv run -m twine upload dist/*

# OS별 설정
ifeq ($(OS),Windows_NT)
    PYTHON_WARNINGS = set PYTHONWARNINGS=ignore::UserWarning:altgraph,ignore::PydanticJsonSchemaWarning &&
else
    PYTHON_WARNINGS = PYTHONWARNINGS=ignore::UserWarning:altgraph,ignore::PydanticJsonSchemaWarning
endif

build-onedir: clean
	uv pip install --upgrade -e ".[build,all]"
	uv pip install --upgrade pyinstaller
	# Windows 빌드 시 필요한 추가 의존성 설치 (에러 무시)
	-uv pip install cryptography sqlalchemy pyOpenSSL
	# spec 파일 사용 또는 기본 옵션으로 빌드
ifeq ($(wildcard pyhub.mcptools.spec),pyhub.mcptools.spec)
	@echo "Building with spec file..."
	$(PYTHON_WARNINGS) uv run pyinstaller pyhub.mcptools.spec --clean
else
	@echo "Building with default options..."
	$(PYTHON_WARNINGS) uv run pyinstaller --console --onedir \
		--collect-all celery \
		--collect-all mcp_proxy \
		--collect-all kombu \
		--collect-all dns \
		--collect-all eventlet \
		--collect-all pyhub.mcptools \
		--name pyhub.mcptools \
		pyhub/mcptools/__main__.py
endif

#
# docs
#

docs:
	uv pip install -e ".[docs]"
	sh ./scripts/download-fonts.sh
	uv run mkdocs serve --dev-addr localhost:8080

docs-build:
	uv pip install -e ".[docs]"
	sh ./scripts/download-fonts.sh
	uv run mkdocs build --clean --site-dir docs-build
