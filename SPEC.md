# Engineering Spec

## Scope
This specification defines measurable acceptance criteria for the repository control system setup phase.

## Required Artifacts
The following files must exist and be maintained:
1. `MASTER_PLAN.md`
2. `AGENTS.md`
3. `SYSTEM.md`
4. `SPEC.md`
5. CI workflow at `.github/workflows/ci.yml`
6. Lint and test configuration (`pyproject.toml` or equivalent)
7. Test scaffolding under `tests/`
8. Control gate validator at `scripts/control_gate.py`

## Required Commands (Local)
All commands are run from repository root.

1. Dependency install
- Command: `python -m pip install -r requirements.txt -r requirements-dev.txt`
- Pass criteria: exit code `0`

2. Lint
- Command: `ruff check .`
- Pass criteria: exit code `0`, no lint violations under configured rules

3. Tests
- Command: `pytest -q`
- Pass criteria: exit code `0`, no test failures or errors

4. Control gate (readiness)
- Command: `python scripts/control_gate.py --mode readiness`
- Pass criteria: exit code `0`

## CI Gate Criteria
Primary gate:
1. GitHub Actions workflow `.github/workflows/ci.yml` executes dependency install, lint, tests, and `python scripts/control_gate.py --mode ci` successfully.

No local fallback gate is allowed for declaring readiness.

Any failed required gate is a hard fail.

## Green State Definition
Green state is achieved when:
1. All local required commands pass.
2. CI workflow has a successful run for current `HEAD` commit.
3. `MASTER_PLAN.md` records completion status for current step with evidence.

## Zero-Error Control State
Zero-error state for this phase means:
1. No failing required checks.
2. No unresolved TODOs in the master plan for Steps 1-5.
3. Readiness tag `control-system-ready` exists and points to `HEAD`.

## Enforcement Rules
1. Do not add new application feature logic before `control-system-ready` is reached.
2. Any change that causes required checks to fail must be corrected before continuing.
3. `MASTER_PLAN.md` must be updated after each completed step with evidence.
4. If readiness preconditions are missing (for example no remote origin or no successful CI run for `HEAD`), readiness cannot be marked complete.

## Minimum Test Baseline
Before readiness tag, test suite must include at least:
1. One schema contract test.
2. One utility contract test.
3. One pipeline import/smoke test.
4. One control-gate contract test.

## Readiness Tag Criteria
Tag `control-system-ready` may be created or moved only when:
1. Steps 1-4 are complete and validated.
2. `python scripts/control_gate.py --mode readiness` passes.
3. Step 5 is marked complete in `MASTER_PLAN.md`.
