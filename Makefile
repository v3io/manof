VENV_PYTHON = ./venv/bin/python

.PHONY: all
all: venv lint test
	@echo Done.

.PHONY: lint
lint: venv flake8 fmt-check

.PHONY: flake8
flake8:
	@echo "Running flake8 lint..."
	$(VENV_PYTHON) -m flake8 .

.PHONY: fmt
fmt:
	@echo "Running black fmt..."
	$(VENV_PYTHON) -m black --skip-string-normalization .

.PHONY: fmt-check
fmt-check:
	@echo "Running black fmt check..."
	$(VENV_PYTHON) -m black --skip-string-normalization --check --diff -S .

.PHONY: test
test: test-unit test-integ
	@echo Finished running Tests

.PHONY: test-unit
test-unit: venv
	$(VENV_PYTHON) -m nose tests/unit

.PHONY: test-integ
test-integ: venv
	$(VENV_PYTHON) -m nose tests/integration/cases/

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
