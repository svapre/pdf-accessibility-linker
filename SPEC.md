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

## CI Gate Criteria
CI is considered passing only when the workflow:
1. Installs dependencies successfully.
2. Runs lint command and passes.
3. Runs tests and passes.

Any failed job is a hard fail.

## Green State Definition
Green state is achieved when:
1. All local required commands pass.
2. CI gate passes.
3. `MASTER_PLAN.md` records completion status for current step.

## Zero-Error Control State
Zero-error state for this phase means:
1. No failing required checks.
2. No unresolved TODOs in the master plan for Steps 1-5.
3. Repository has a readiness tag `control-system-ready` after Step 5.

## Enforcement Rules
1. Do not add new application feature logic before `control-system-ready` is reached.
2. Any change that causes required checks to fail must be corrected before continuing.
3. `MASTER_PLAN.md` must be updated after each completed step with evidence.

## Minimum Test Baseline
Before readiness tag, test suite must include at least:
1. One schema contract test.
2. One utility contract test.
3. One pipeline import/smoke test.

## Readiness Tag Criteria
Tag `control-system-ready` may be created only when:
1. Steps 1-4 are complete and validated.
2. Local and CI checks pass.
3. Step 5 is marked complete in `MASTER_PLAN.md`.
