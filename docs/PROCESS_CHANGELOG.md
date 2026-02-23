# Process Changelog

This log tracks changes to control-system process, policy, and governance artifacts.

## 2026-02-23 - Process governance hardening
- Added `scripts/process_guard.py` to enforce process-change and design-coupling rules.
- Added proposal-structure enforcement so proposal files must contain required decision sections.
- Added `DESIGN.md` with design guardrails and brainstorming protocol.
- Added `GOVERNANCE.md` with proposal-first and process-change rules.
- Added `.github/pull_request_template.md` with required governance checklist.
- Updated `SPEC.md`, `SYSTEM.md`, `AGENTS.md`, `MASTER_PLAN.md`, and CI workflow to include process guard checks.
