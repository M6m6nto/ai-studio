PY := python3

.PHONY: smoke test scout ref

smoke:
	$(PY) -m engines.common.smoke

test:
	$(PY) -m pytest -q

scout:
	$(PY) -m engines.scout.cli $(ARGS)

ref:
	$(PY) -m engines.ref.cli $(ARGS)
