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
ifeq ($(OS),Windows_NT)
	@echo "Cleaning on Windows..."
	@powershell -NoProfile -Command "Get-ChildItem -Path . -Filter __pycache__ -Recurse -Directory -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue; exit 0"
	@powershell -NoProfile -Command "if (Test-Path dist) { Remove-Item -Path dist -Recurse -Force }; exit 0"
	@powershell -NoProfile -Command "if (Test-Path build) { Remove-Item -Path build -Recurse -Force }; exit 0"
	@powershell -NoProfile -Command "Remove-Item -Path *.egg-info, *.spec, .pytest_cache, .mypy_cache, .ruff_cache -Recurse -Force -ErrorAction SilentlyContinue; exit 0"
else
	@echo "Cleaning on Unix..."
	find . -name __pycache__ | xargs rm -rf
	rm -rf dist/ build/ *.egg-info *.spec .pytest_cache .mypy_cache .ruff_cache
endif

build: clean
	uv pip install -e ".[build]"
	uv run -m build --wheel

publish: build
	uv run -m twine upload dist/*

# OS-specific settings
ifeq ($(OS),Windows_NT)
    PYTHON_WARNINGS = set PYTHONWARNINGS=ignore::UserWarning:altgraph &&
else
    PYTHON_WARNINGS = PYTHONWARNINGS=ignore::UserWarning:altgraph
endif

# Build executable with PyInstaller
build-onedir: clean
	uv pip install --upgrade -e ".[build,all]"
	uv pip install --upgrade pyinstaller
	-uv pip install cryptography sqlalchemy pyOpenSSL
	@echo "Building executable..."
	$(PYTHON_WARNINGS) uv run pyinstaller --console --onedir \
		--additional-hooks-dir=pyinstaller_hooks \
		--collect-all mcp_proxy \
		--collect-all dns \
		--collect-all eventlet \
		--collect-all pyhub.mcptools \
		--name pyhub.mcptools \
		pyhub/mcptools/__main__.py

# Build optimized executable with minimal locale files
build-onedir-optimized: clean
	uv pip install --upgrade -e ".[build,all]"
	uv pip install --upgrade pyinstaller
	-uv pip install cryptography sqlalchemy pyOpenSSL
	@echo "Building optimized executable with minimal locales..."
	$(PYTHON_WARNINGS) uv run pyinstaller --console --onedir \
		--additional-hooks-dir=pyinstaller_hooks \
		--collect-all mcp_proxy \
		--collect-all dns \
		--collect-all eventlet \
		--collect-all pyhub.mcptools \
		--exclude-module django.contrib.gis \
		--exclude-module django.contrib.postgres \
		--exclude-module django.db.backends.mysql \
		--exclude-module django.db.backends.postgresql \
		--exclude-module django.db.backends.oracle \
		--exclude-module django.test \
		--name pyhub.mcptools \
		pyhub/mcptools/__main__.py

#
# docs
#

docs:
	uv pip install -e ".[docs]"
ifeq ($(OS),Windows_NT)
	@powershell -ExecutionPolicy Bypass -File ./scripts/download-fonts.ps1
else
	sh ./scripts/download-fonts.sh
endif
	uv run mkdocs serve --dev-addr localhost:8080

docs-build:
	uv pip install -e ".[docs]"
ifeq ($(OS),Windows_NT)
	@powershell -ExecutionPolicy Bypass -File ./scripts/download-fonts.ps1
else
	sh ./scripts/download-fonts.sh
endif
	uv run mkdocs build --clean --site-dir docs-build
