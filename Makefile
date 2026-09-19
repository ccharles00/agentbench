PY := .venv/Scripts/python.exe
SPLIT ?= public

.PHONY: help setup fonts generate selfcheck run score test clean

help:
	@echo "setup      - create venv, install locked dependencies + Chromium"
	@echo "fonts      - download pinned Noto fonts (see fonts.lock)"
	@echo "generate   - generate the $(SPLIT) split (SPLIT=private for the private split)"
	@echo "selfcheck  - run the B2.8 self-checks on the $(SPLIT) split"
	@echo "run        - cost estimate only (add CONFIRM=1 to execute paid runs)"
	@echo "score      - score cached results into results/$(SPLIT)"
	@echo "test       - unit tests"

setup:
	python -m venv .venv
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r requirements.lock
	$(PY) -m playwright install chromium

fonts:
	$(PY) scripts/fetch_fonts.py

generate:
	$(PY) -m core.cli generate --category invoices --split $(SPLIT)

selfcheck:
	$(PY) -m core.cli selfcheck --category invoices --split $(SPLIT)

run:
ifdef CONFIRM
	$(PY) -m core.cli run --category invoices --split $(SPLIT) --tools all --variants all --confirm
else
	$(PY) -m core.cli run --category invoices --split $(SPLIT) --tools all --variants all --dry-run
endif

score:
	$(PY) -m core.cli score --category invoices --split $(SPLIT)

test:
	$(PY) -m pytest -q
