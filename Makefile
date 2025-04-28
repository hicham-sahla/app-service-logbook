PYTHON_MINIMUN_MINOR_VER := 9
CBC_PATH := ./functions
PWD := $(shell pwd)

PYTHON_FILES := $(shell find $(CBC_PATH) -type f -name '*.py' -a ! -name 'test_*.py' -a ! -name '*_test.py')

IXON_API_BASE_URL := https://api.ayayot.com
IXON_API_VERSION := 2
IXON_API_APPLICATION_ID := 9J9IZzeT4xN4
IXON_API_COMPANY_ID :=
IXON_API_TEMPLATE_ID :=

-include .env

# ######
# Autodetect Python location and version.
# ######

# Detect echo location for command line output.
ifeq (,$(ECHO_BIN))
ifeq ($(OS),Windows_NT)
ECHO_BIN := echo
else
ECHO_BIN := $(shell which echo)
endif
endif

# Python interpreter location for the venv environment.
ifeq (,$(PYTHON_BIN))
ifeq ($(OS),Windows_NT)
PYTHON_BIN := ./venv/Scripts/python.exe
else
PYTHON_BIN := ./venv/bin/python3
endif
endif

# Python interpreter location for host machine.
ifeq (,$(wildcard $(PYTHON_BIN)))
ifeq ($(OS),Windows_NT)
HOST_PYTHON_BIN := $(shell where python)
else
HOST_PYTHON_BIN := $(shell which python3 2> /dev/null)
endif
endif

# Python interpreter version for host machine.
ifeq (,$(wildcard $(PYTHON_BIN)))
ifeq (,$(wildcard $(HOST_PYTHON_BIN)))
HOST_PYTHON_MAJOR_VER :=
HOST_PYTHON_MINOR_VER :=
else
HOST_PYTHON_MAJOR_VER := $(shell $(HOST_PYTHON_BIN) -c 'import sys ; print (sys.version_info[0])')
HOST_PYTHON_MINOR_VER := $(shell $(HOST_PYTHON_BIN) -c 'import sys ; print (sys.version_info[1])')
endif
endif

# Set the minor version to -1 if there is no minor version detected
# otherwise some future checks won't work.
ifeq (,$(HOST_PYTHON_MINOR_VER))
HOST_PYTHON_MINOR_VER := -1
endif

# ######
# Virtual Python environment setup.
# ######

$(PYTHON_BIN):
# Check if venv is already setup
ifeq (,$(wildcard $(PYTHON_BIN)))

# Check if Python could be found on the host machine.
ifeq (, $(HOST_PYTHON_MAJOR_VER))
	@echo Could not detect Python on the host system
	@false
endif

# Check Python version on the host machine is correct.
ifeq ($(HOST_PYTHON_MAJOR_VER), 2)
	@echo Python 2 is not supported
	@false
endif

# Check if HOST_PYTHON_MINOR_VER is greater than or equal to the minimun version.
ifeq ($(shell test $(HOST_PYTHON_MINOR_VER) -ge $(PYTHON_MINIMUN_MINOR_VER); echo $$?), 1)
	@echo Python version below 3.$(PYTHON_MINIMUN_MINOR_VER) in not supported
	@false
endif

# Ensure we're working with Python 3
ifeq ($(HOST_PYTHON_MAJOR_VER), 3)
	@echo Setting up virtual environment for Python 3
	$(HOST_PYTHON_BIN) -m venv ./venv
endif

	$(PYTHON_BIN) -m pip install pip setuptools wheel --upgrade
else
	@echo Venv already set up, not doing anything.
endif

# #####
# PYTEST SETTINGS
# #####

ifeq (,$(PYTEST_ROOT_DIRECTORY))
PYTEST_ROOT_DIRECTORY := tests
endif

ifeq (,$(TEST_FILES))
TEST_FILES = $(PYTEST_ROOT_DIRECTORY)
endif

# ######
# DEFAULT FLAGS
#
# These flags are set by default but can be overwritten
# ######
MYPY_DEFAULT_FLAGS := --strict

# ######
# AUTODETECTED SETTINGS FOR THE PACKAGE INFORMATION
#
# This is pretty slow and only works for packages
# ######
ifeq (,$(PYPI_PACKAGE_DIR))
PYPI_PACKAGE_DIR = functions
endif

./venv/pip-dev.done: $(PYTHON_BIN) requirements*.txt
	@echo Installing application dependencies
	$(PYTHON_BIN) -m pip install --requirement requirements-dev.txt
	echo > $@

# ######
# Scripts
# ######

# Setup virtual Python environment
py-venv-dev: ./venv/pip-dev.done

# ######
# TEST AND TYPE CHECKS
# ######

py-unittest: py-venv-dev ## Run unit tests on Python code
	$(PYTHON_BIN) -m pytest \
		$(if $(SKIP_COV),, \
			$(foreach dir, \
				$(PYTEST_ROOT_DIRECTORY), \
				$(if $(wildcard $(dir)/.coveragerc),--cov-config $(abspath $(dir)/.coveragerc))) \
			--cov-branch \
			--cov-report html --cov-report term --cov-report xml --cov=$(PYPI_PACKAGE_DIR) \
		) \
		$(TEST_FLAGS) \
		$(TEST_FILES)

py-typecheck: py-venv-dev ## Run type checker on Python code
	$(PYTHON_BIN) -m mypy $(MYPY_DEFAULT_FLAGS) $(MYPY_FLAGS) $(PYPI_PACKAGE_DIR)

py-unittest-typecheck: py-venv-dev ## Run typecheck on Python unit test helpers (not on tests themselves)
	$(PYTHON_BIN) -m mypy $(MYPY_DEFAULT_FLAGS) $(MYPY_FLAGS) --exclude='test_([^/\\]+).py$$' $(TEST_FILES)

py-ruff: py-venv-dev ## Run linter on Python code
	$(PYTHON_BIN) -m ruff check $(PYPI_PACKAGE_DIR) $(RUFF_FLAGS)

py-format: py-venv-dev ## Run formatter on Python code
	$(PYTHON_BIN) -m ruff format $(PYPI_PACKAGE_DIR) $(if $(FORMAT_CHECK_ONLY),--check --diff) $(RUFF_FORMAT_FLAGS)

py-unittest-ruff: py-venv-dev ## Run linter on Python tests
	$(PYTHON_BIN) -m ruff check $(TEST_FILES) $(RUFF_FLAGS)

py-unittest-format: py-venv-dev ## Run formatter on Python tests
	$(PYTHON_BIN) -m ruff format $(TEST_FILES) $(if $(FORMAT_CHECK_ONLY),--check --diff) $(RUFF_FORMAT_FLAGS)

py-bandit: py-venv-dev ## Run bandit on Python code
	$(PYTHON_BIN) -m bandit \
		$(if $(wildcard pyproject.toml),-c pyproject.toml) \
		-r $(PYPI_PACKAGE_DIR)

py-test: py-unittest py-typecheck py-ruff py-unittest-typecheck py-unittest-ruff py-bandit ## Run all tests on Python code

# Clean up virtual Python environment
py-distclean:
	rm -rf ./venv

bundle:
ifeq ($(wildcard requirements.txt),)
	$(error No requirements.txt file found!!)
endif
ifeq ($(PYTHON_FILES),)
	$(error No Python files found!!)
endif
	rm -f bundle.zip
	zip $(PWD)/$@ requirements.txt
	zip $(PWD)/$@ $(PYTHON_FILES)

deploy: bundle
ifeq ($(IXON_API_COMPANY_ID),)
	$(error IXON Cloud Company ID not set, create .env and add IXON_API_COMPANY_ID=...)
endif
ifeq ($(IXON_API_TEMPLATE_ID),)
	$(error IXON Cloud Backend Component Template ID not set, create .env and add IXON_API_TEMPLATE_ID=...)
endif
ifeq ($(wildcard .accesstoken),)
	$(error No .accesstoken file found; create .accesstoken and enter a valid access token)
endif
	curl -X POST \
		-H "api-version: $(IXON_API_VERSION)" \
		-H "api-application: $(IXON_API_APPLICATION_ID)" \
		-H "api-company: $(IXON_API_COMPANY_ID)" \
		-H "authorization: Bearer $(shell cat .accesstoken)" \
		--data-binary @bundle.zip \
		$(IXON_API_BASE_URL)/backend-component-templates/$(IXON_API_TEMPLATE_ID)/version-upload

# Run the ixoncdkingress
run: py-venv-dev
	CBC_PATH=$(CBC_PATH) $(PYTHON_BIN) -m ixoncdkingress
