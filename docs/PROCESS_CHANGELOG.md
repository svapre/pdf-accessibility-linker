# Process Changelog

This log tracks changes to control-system process, policy, and governance artifacts.

## 2026-02-23 - Process governance hardening
- Added `scripts/process_guard.py` to enforce process-change and design-coupling rules.
- Added proposal-structure enforcement so proposal files must contain required decision sections.
- Added `DESIGN.md` with design guardrails and brainstorming protocol.
- Added `GOVERNANCE.md` with proposal-first and process-change rules.
- Added `.github/pull_request_template.md` with required governance checklist.
- Updated `SPEC.md`, `SYSTEM.md`, `AGENTS.md`, `MASTER_PLAN.md`, and CI workflow to include process guard checks.

## 2026-02-23 - Communication profile codification
- Added `docs/USER_CONTEXT.md` to persist user background and plain-language communication preferences.
- Updated `AGENTS.md` read order and update rules to require plain-language, acronym expansion, and terminology definitions.
- Updated `GOVERNANCE.md` with a communication contract tied to process quality.
- Updated `SPEC.md` to include user-context communication expectations.
- Updated `scripts/control_gate.py` and `scripts/process_guard.py` to require `docs/USER_CONTEXT.md`.
- Updated `docs/README.md` index for discoverability.
