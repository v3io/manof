# Copyright 2018 Iguazio
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
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
	$(VENV_PYTHON) -m black --skip-string-normalization --exclude='.*venv.*' .

.PHONY: fmt-check
fmt-check:
	@echo "Running black fmt check..."
	$(VENV_PYTHON) -m black --skip-string-normalization --check --diff -S --exclude='.*venv.*' .

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
