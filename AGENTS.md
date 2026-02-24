# AGENTS Guide

## Purpose
This file tells autonomous coding agents where project control documents live and in what order to read them.

## Read Order (Required)
1. `MASTER_PLAN.md` - current task state and next action.
2. `SPEC.md` - measurable success criteria and pass/fail gates.
3. `SYSTEM.md` - control-loop architecture (sensors, controller actions, termination).
4. `DESIGN.md` - design guardrails for ideas and implementation.
5. `GOVERNANCE.md` - process requirements for proposals and process changes.
6. `.control-loop/policy.json` - project process policy overrides.
7. `.control-loop/ai_settings.json` - AI behavior settings and global process switch.
8. `docs/USER_CONTEXT.md` - user background and communication preferences.
9. `docs/CONTEXT_INDEX.md` - context priority tiers to avoid context drift.
10. `docs/` - supporting runbooks, proposals, session logs, and change logs.

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
9. Accept solutions with design-parameter violations only when proposal evidence shows the option is best overall for current constraints.
10. If an answer depends on assumptions or missing evidence, mark it `UNKNOWN` and do not present it as confirmed.
11. Use plain language by default:
   - Expand acronyms on first use (example: Pull Request (PR))
   - Briefly define version-control and industry terms before using them
   - Avoid unexplained jargon unless the user asks for technical depth
12. Follow `docs/USER_CONTEXT.md` communication preferences in both implementation and brainstorming turns.
13. Use explicit work modes:
   - `routine` for low-risk implementation, lint/test, and repository operations
   - `design` for architecture, tradeoff, and unclear requirements
14. Ambiguity stop rule:
   - If requirements are unclear and implementation would rely on assumptions, ask the user before coding.
   - Do not proceed with assumption-based implementation unless user confirmation evidence is documented.
15. Policy is configuration-driven:
   - Read `.control-loop/policy.json` (or toolkit defaults) for process rules instead of hardcoding behavior.
16. AI behavior is configuration-driven:
   - Read `.control-loop/ai_settings.json` for response style, confirmation, and enforcement mode.
17. If changed files match AI-settings session triggers, update `docs/sessions/` with approval and correction evidence.

## Locations
- Core app code: `core/`, `data_models/`, `utils/`, `main.py`
- Control docs: repository root + `docs/`
- CI config: `.github/workflows/`
- Tests: `tests/`
- Process policy: `.control-loop/policy.json`
- AI settings: `.control-loop/ai_settings.json`
- Shared toolkit submodule: `tooling/control-loop-kit`
- Control gate script: `scripts/control_gate.py`
- Process gate script: `scripts/process_guard.py`

