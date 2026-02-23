# AGENTS Guide

## Purpose
This file tells autonomous coding agents where project control documents live and in what order to read them.

## Read Order (Required)
1. `MASTER_PLAN.md` - current task state and next action.
2. `SPEC.md` - measurable success criteria and pass/fail gates.
3. `SYSTEM.md` - control-loop architecture (sensors, controller actions, termination).
4. `DESIGN.md` - design guardrails for ideas and implementation.
5. `GOVERNANCE.md` - process requirements for proposals and process changes.
6. `docs/` - supporting runbooks, proposals, and change logs.

## Update Rules
1. Update `MASTER_PLAN.md` after each meaningful step.
2. Do not implement feature logic until Steps 1-5 in `MASTER_PLAN.md` are complete.
3. When checks fail, record failures and corrective actions before proceeding.
4. Never mark control readiness complete unless `python scripts/control_gate.py --mode readiness` passes.
5. If readiness gate fails, Step 4/5 must be marked blocked or in-progress, not done.
6. If implementation files change (`core/`, `data_models/`, `utils/`, `main.py`), update a proposal in `docs/proposals/`.
7. If process-controlled files change (`SPEC.md`, `SYSTEM.md`, `AGENTS.md`, CI, gate scripts), update `docs/PROCESS_CHANGELOG.md`.
8. During brainstorming and implementation decisions, explicitly state:
   - Which `DESIGN.md` guardrails are satisfied
   - Which guardrails are violated (if any)
   - Why violations are accepted (if any)
   - Mitigation steps
9. If an answer depends on assumptions or missing evidence, mark it `UNKNOWN` and do not present it as confirmed.

## Locations
- Core app code: `core/`, `data_models/`, `utils/`, `main.py`
- Control docs: repository root + `docs/`
- CI config: `.github/workflows/`
- Tests: `tests/`
- Control gate script: `scripts/control_gate.py`
- Process gate script: `scripts/process_guard.py`

