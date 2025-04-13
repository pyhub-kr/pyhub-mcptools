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

build-onedir: clean
	uv pip install --upgrade -e ".[build,all]"
	uv pip install --upgrade pyinstaller
	uv run pyinstaller --console --onedir --collect-all mcp_proxy --collect-all pyhub.mcptools --name pyhub.mcptools pyhub/mcptools/__main__.py

#
# docs
#

docs:
	uv pip install -e ".[docs]"
	uv run mkdocs serve --dev-addr localhost:8080

docs-build:
	uv pip install -e ".[docs]"
	uv run mkdocs build --clean --site-dir docs-build
