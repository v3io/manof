VENV_PYTHON = ./venv/bin/python
TESTER = ./venv/bin/nosetests
LINTER = ./venv/bin/flake8

.PHONY: all
all: venv lint test
	@echo Done.

.PHONY: lint
lint: venv
	$(LINTER) .

.PHONY: test
test: test-unit test-integ
	@echo Finished running Tests

.PHONY: test-unit
test-unit: venv
	$(TESTER) tests/unit

.PHONY: test-integ
test-integ: venv
	$(TESTER) tests/integration/cases/

.PHONY: install
install: venv
	@echo Installed

.PHONY: install-ci
install-ci: install-venv install

venv:
	python ./install --dev
	$(VENV_PYTHON) -m pip install -e ./tools/flake8_plugin

.PHONY: install-venv
install-venv:
	python -m pip install --upgrade pip
	python -m pip install virtualenv
