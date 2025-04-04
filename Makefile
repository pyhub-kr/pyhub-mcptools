.PHONY: test clean build publish docs docs-build

test:
	uv pip install -e ".[all,dev]"
	uv run pytest $(filter-out $@,$(MAKECMDGOALS))

format:
	uv pip install -e ".[all,dev]"
	uv run black ./pyhub
	uv run isort ./pyhub
	uv run ruff check ./pyhub --fix
	uv run djlint ./pyhub --reformat

lint:
	uv pip install -e ".[all,dev]"
	uv run black ./pyhub --check
	uv run isort ./pyhub --check
	uv run ruff check ./pyhub
	uv run djlint ./pyhub --check

clean:
	rm -rf dist/
	rm -rf build/
	rm -rf pyhub/*.egg-info

build: clean
	uv pip install -e ".[build]"
	uv run -m build --wheel

publish: build
	uv run -m twine upload dist/*

#
# docs
#

docs:
	uv pip install -e ".[docs]"
	uv run mkdocs serve --dev-addr localhost:8080

docs-build:
	uv pip install -e ".[docs]"
	uv run mkdocs build --clean --site-dir docs-build