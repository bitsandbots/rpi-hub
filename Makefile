# SIGNAL — convenience targets. Real work lives in install.sh and the
# per-service code; this file is for one-liners during development.

SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c

.PHONY: help install uninstall lint fmt test smoke check-headers clean

help:  ## Show this help
	@awk 'BEGIN {FS = ":.*##"; printf "Targets:\n"} /^[a-zA-Z_-]+:.*##/ { printf "  %-16s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

install:  ## Run the idempotent installer (requires sudo)
	sudo ./install.sh

uninstall:  ## Reverse install.sh (requires sudo)
	sudo ./uninstall.sh

lint:  ## Run all linters (ruff, mypy, shellcheck, yamllint, markdownlint)
	pre-commit run --all-files

fmt:  ## Auto-format (black, ruff --fix, shfmt)
	pre-commit run --all-files ruff || true
	pre-commit run --all-files black || true
	pre-commit run --all-files shfmt || true

test:  ## Run pytest across api/, assistant/, indexer/, listen/, notes/
	pytest -q

smoke:  ## End-to-end healthcheck against a live device or QEMU
	./scripts/healthcheck.sh

check-headers:  ## Fail if any config/ file lacks the required header
	./scripts/check_config_header.py config/

clean:  ## Remove caches
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
