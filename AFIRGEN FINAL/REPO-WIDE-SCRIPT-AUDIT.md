# Repo-Wide Script Audit (Full Sweep)

Date: 2026-02-21
Scope: Entire repository code scripts (`*.py`, `*.js`, `*.sh`, `*.json`, `*.yml`, `*.yaml`) excluding `node_modules` for executable linting.

## What was checked

1. Python compile check across all Python scripts.
2. JavaScript parse check across all JS scripts.
3. Shell syntax check across all bash scripts.
4. JSON validity check (repo-owned JSON files; excluding `node_modules` JSONC-like files).
5. YAML parse check across all YAML files.
6. Spot-check grep for known structural anti-patterns found earlier (`to_response()`, duplicated middleware declarations, known signature mismatch sites).

## Results Summary

- Python: **44 scanned, 1 failed**.
- JavaScript: **77 scanned, 0 failed**.
- Shell: **7 scanned, 0 failed**.
- JSON (excluding `node_modules`): **9 scanned, 0 failed**.
- YAML: **66 scanned, 0 failed**.
- PowerShell (`*.ps1`): syntax check **not executed** because `pwsh` is unavailable in this environment.

## Errors Found

### Python (1)

1. `AFIRGEN FINAL/main backend/agentv5.py`
   - `IndentationError: expected an indented block after class definition on line 1693 (line 1695)`
   - This is a backend startup/import blocker and remains the only syntax-level compile failure found in the full-script sweep.

## Additional structural/code-quality red flags confirmed during full sweep

Even beyond syntax checks, these code-level issues are still present and should be fixed:

1. Invalid `HTTPException(...).to_response()` usage in middleware path.
2. Duplicated/nested middleware declarations in `agentv5.py` around auth/request-tracking.
3. `get_fir_data` call-site signature mismatch (`2 args` passed to `1 arg` function).

## Conclusion

- The full repository script sweep found **one hard syntax blocker** (`agentv5.py`) and no parse/syntax errors in other Python/JS/shell/YAML/owned-JSON scripts.
- Remaining major risks are now primarily **runtime/contract/structural** issues concentrated in `AFIRGEN FINAL/main backend/agentv5.py` and frontend↔backend API contract alignment, as documented in the detailed frontend/backend review artifact.


## Re-check After User Changes (2026-02-22)

A full verification sweep was re-run after the latest user-side updates.

- Python: **44 scanned, 1 failed** (unchanged: `AFIRGEN FINAL/main backend/agentv5.py` `IndentationError` at line 1695).
- JavaScript: **77 scanned, 0 failed**.
- Shell: **7 scanned, 0 failed**.
- JSON (excluding `node_modules`): **9 scanned, 0 failed**.
- YAML: **66 scanned, 0 failed**.

### Delta vs previous sweep

- No new syntax/parse failures were introduced.
- The original hard blocker in `agentv5.py` is still present and must be fixed for backend startup/import.


## Re-check After User Changes (2026-02-22, pass 2)

Second verification sweep after additional user updates.

- Python: **44 scanned, 1 failed** (`AFIRGEN FINAL/main backend/agentv5.py` still fails with `IndentationError` at line 1695).
- JavaScript: **77 scanned, 0 failed**.
- Shell: **7 scanned, 0 failed**.
- JSON (excluding `node_modules`): **9 scanned, 0 failed**.
- YAML: **66 scanned, 0 failed**.

### Delta vs prior re-check

- No new parser/compiler/syntax issues introduced.
- Existing backend startup blocker remains unresolved.
