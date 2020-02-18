PYTHON_VERSION = python2.7

.PHONY: all
all: install test
	@echo Done.

#.PHONY: lint
#lint: install
#	flake8 .

.PHONY: test
test: test-unit test-integ
	@echo Finished running Tests

.PHONY: test-unit
test-unit: install
	nosetests tests/unit

.PHONY: test-integ
test-integ: install
	nosetests tests/integration/cases/

.PHONY: install
install:
	$(PYTHON_VERSION) ./install