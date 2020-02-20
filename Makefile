SYSTEM_PYTHON = python2.7
VENV_PYTHON = ./venv/bin/python
TESTER = ./venv/bin/nosetests
LINTER = ./venv/bin/flake8

.PHONY: all
all: install test
	@echo Done.

.PHONY: lint
lint: install
	$(LINTER) .

.PHONY: test
test: test-unit test-integ
	@echo Finished running Tests

.PHONY: test-unit
test-unit: install
	$(TESTER) tests/unit

.PHONY: test-integ
test-integ: install
	$(TESTER) tests/integration/cases/

.PHONY: install
install:
	$(SYSTEM_PYTHON) ./install
