# Master Plan

## Objective
Build and stabilize a closed-loop engineering control system for this repository before any feature work.

## Task Board
| Step | Title | Status | Success Criteria | Evidence | Next Action |
|---|---|---|---|---|---|
| 1 | Initialize Git + project skeleton | done | Git initialized, docs scaffolding created, initial commit made | Commit `58245dd` | Step 2 |
| 2 | Define control-system architecture | done | `SYSTEM.md` and `SPEC.md` define measurable control targets | Commit `46d11a0` | Step 3 |
| 3 | Build measurement and feedback tools | done | CI, tests, and lint configured and executable | Commit `65a0487` with workflow, config, and test scaffold | Step 4 |
| 4 | Execute feedback loop to green | in_progress | Local checks pass and remote CI success exists for current `HEAD` | Local checks pass; remote CI evidence for current `HEAD` not yet established | Configure remote and push |
| 5 | Tag readiness | blocked | `control-system-ready` tag points to `HEAD` and readiness gate passes | Existing tag points to `d59a1ab`, current `HEAD` is newer | Move tag after Step 4 passes |

## Progress Log
- Step 1 completed: initialized Git, added control-document scaffolding, and committed baseline (`58245dd`).
- Step 2 completed: formalized control-loop architecture in `SYSTEM.md` and measurable pass/fail gates in `SPEC.md` (`46d11a0`).
- Step 3 completed: added CI workflow, lint config, dev dependencies, and minimum baseline tests (`65a0487`).
- Step 4 measurement cycle 1: failures detected.
  - `ruff check .` failed on undefined `json` in `core/profiler.py`.
  - `pytest -q` failed due invalid `pyproject.toml` encoding/parsing.
- Step 4 corrective actions:
  - Added module-level `import json` and removed function-local conflicting import in `core/profiler.py`.
  - Rewrote `pyproject.toml` in ASCII to remove BOM parsing issue.
- Step 4 measurement cycle 2: local checks passed.
  - `python -m pip install -r requirements.txt -r requirements-dev.txt` passed.
  - `ruff check .` passed.
  - `pytest -q` passed.
- Postmortem: readiness was previously marked done using local fallback despite no remote CI proof for current `HEAD`.
- Hardening cycle applied:
  - Added automated control gate at `scripts/control_gate.py`.
  - Tightened `SPEC.md`, `SYSTEM.md`, and `AGENTS.md` to require remote CI proof and tag freshness.
  - Added CI step `python scripts/control_gate.py --mode ci`.
- Current state after hardening:
  - Local checks are passing.
  - Readiness is intentionally reopened until remote CI for current `HEAD` is available and tag is updated.
- Hardening verification run:
  - `python scripts/control_gate.py --mode ci` passed.
  - `python scripts/control_gate.py --mode readiness` failed as expected with actionable blockers:
    - no `origin` remote configured,
    - stale `control-system-ready` tag,
    - dirty worktree during in-progress edits.
