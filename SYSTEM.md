# System Control Model

## Purpose
Define the closed-loop engineering control system for this repository. The loop governs how changes are proposed, measured, corrected, and accepted.

## Control Framing
- Controller: autonomous development agent (Codex).
- Plant: repository code, tests, lint config, CI workflow, and dependency setup.
- Reference signal: pass targets defined in `SPEC.md`.
- Feedback signals: local command exit codes and CI workflow results.
- Error vector: the set of failing checks vs target pass state.

## Loop Components
### Sensors (Measurements)
1. Lint sensor: `ruff check .`
2. Test sensor: `pytest -q`
3. CI sensor: GitHub Actions workflow status for the same checks.
4. Repository state sensor: `git status --short` for dirty state visibility.

### Actuators (Corrections)
1. Edit source/config/test files.
2. Add or adjust tooling config (`pyproject.toml`, workflow files, test scaffolds).
3. Add or pin developer dependencies needed for measurement.
4. Update documentation (`MASTER_PLAN.md`, `SPEC.md`, runbooks) to keep control intent explicit.

### Controller Logic
1. Measure all sensors.
2. Compare measured state to `SPEC.md` pass targets.
3. Identify smallest corrective change set needed to reduce error.
4. Apply corrections.
5. Re-run sensors.
6. Commit when stable improvement is achieved.
7. Repeat until all required sensors report pass.

## Operating Modes
1. Bootstrap mode: establish tooling and measurements (Steps 1-3 in `MASTER_PLAN.md`).
2. Stabilization mode: iterate until full green state (Step 4).
3. Maintenance mode: future work must keep loop green; regressions trigger return to stabilization mode.

## Termination Criteria
Control loop is considered closed and stable when:
1. Local lint and tests pass with zero failures.
2. CI workflow passes on the same checks.
3. `MASTER_PLAN.md` marks Steps 1-5 complete.
4. Readiness tag `control-system-ready` is created.

## Disturbances and Failure Handling
Common disturbances:
1. Dependency drift or missing tooling.
2. Syntax/runtime import failures.
3. Configuration mismatch between local and CI.

Failure handling policy:
1. Any failing sensor is treated as non-zero control error.
2. Do not advance steps while unresolved failures exist for the current step goal.
3. Record failure and correction in `MASTER_PLAN.md` progress log.

## Guardrails
1. No feature development before control system readiness is tagged.
2. Each meaningful artifact is committed with explicit commit message.
3. Plans and specs are source-controlled and updated alongside implementation changes.
