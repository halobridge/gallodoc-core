.PHONY: release-gate test test-v3 release-gate-clean

release-gate:
	python3 scripts/release_safety_gate.py

release-gate-clean:
	rm -f release_safety_report.json

test:
	python3 -m pytest tests/ -q --tb=short

test-v3:
	python3 -m pytest tests/v3_0/ -q --tb=short
