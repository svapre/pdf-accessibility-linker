# AGENTS Guide

## Purpose
This file tells autonomous coding agents where project control documents live and in what order to read them.

## Read Order (Required)
1. `MASTER_PLAN.md` - current task state and next action.
2. `SPEC.md` - measurable success criteria and pass/fail gates.
3. `SYSTEM.md` - control-loop architecture (sensors, controller actions, termination).
4. `docs/` - supporting runbooks, decisions, and templates.

## Update Rules
1. Update `MASTER_PLAN.md` after each meaningful step.
2. Do not implement feature logic until Steps 1-5 in `MASTER_PLAN.md` are complete.
3. When checks fail, record failures and corrective actions before proceeding.
4. Never mark control readiness complete unless `python scripts/control_gate.py --mode readiness` passes.
5. If readiness gate fails, Step 4/5 must be marked blocked or in-progress, not done.

## Locations
- Core app code: `core/`, `data_models/`, `utils/`, `main.py`
- Control docs: repository root + `docs/`
- CI config: `.github/workflows/`
- Tests: `tests/`
- Control gate script: `scripts/control_gate.py`
