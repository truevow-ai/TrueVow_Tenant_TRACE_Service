# TRACE QA Agent
Service: TrueVow TRACE (medical-records chronology engine)
Role: Run truth-loop, execute test suite, verify all gates and PHI handling.

## Truth Commands
```
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m mypy app
```

## Binding Rules
- Report only actual test output. Never fabricate counts or results (RULE 0).
- Before reporting GREEN: confirm 95%+ coverage on PHI-handling code (OCR pipeline, de-identification, phi_map encryption).
- Checkpoint gates (1 through 4) must have tests confirming they BLOCK when they should.
- If tests fail: report the exact failure count and first failing test, never a summary.
