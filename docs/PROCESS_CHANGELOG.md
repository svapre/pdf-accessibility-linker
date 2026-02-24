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

## 2026-02-23 - Design-parameter and operating-model hardening
- Expanded `DESIGN.md` into explicit project design parameters and added formal exception rule.
- Updated `GOVERNANCE.md` with human-AI operating model, two work modes, and evidence-based acceptance rule.
- Upgraded `docs/proposals/TEMPLATE.md` to require:
  - design-parameter compliance section
  - exception register
  - decision scorecard
  - validation plan
- Updated `scripts/process_guard.py` to enforce new proposal sections and field markers.
- Extended process-controlled file list in `scripts/process_guard.py` to include proposal/process templates.
- Updated `tests/test_process_guard_contract.py` for new proposal contract and process-change coverage.
- Updated `SPEC.md` and `AGENTS.md` to reflect new acceptance and brainstorming constraints.

## 2026-02-24 - Process extraction and policy-driven upgrade test
- Created separate reusable process repository: `svapre/control-loop-kit`.
- Integrated toolkit in this project as a pinned submodule: `tooling/control-loop-kit`.
- Replaced local gate implementations with compatibility wrappers:
  - `scripts/control_gate.py`
  - `scripts/process_guard.py`
- Updated CI checkout to initialize submodules.
- Published toolkit `v0.2.0` with:
  - policy-driven rules (`default_policy.json` + override support),
  - work-mode enforcement (`routine`/`design`),
  - ambiguity/no-assumption stop rule requiring confirmation evidence.
- Added project policy override at `.control-loop/policy.json`.
- Updated proposal template and governance/spec rules to include:
  - work mode declaration,
  - assumptions/unknowns,
  - approval checkpoint and confirmation evidence.
- Updated process-guard contract tests for new rule set.

## 2026-02-24 - Toolkit documentation release adoption
- Upgraded toolkit submodule from `v0.2.0` to `v0.2.1`.
- Adopted toolkit docs release containing:
  - `docs/CONTROL_TOOLKIT_GUIDE.md` (single-file human + AI onboarding),
  - `docs/QUICKSTART.md` (manual integration steps),
  - `docs/POLICY_SCHEMA.md` (policy structure reference).

## 2026-02-24 - Toolkit policy governance upgrade adoption
- Upgraded toolkit submodule from `v0.2.1` to `v0.3.0`.
- Adopted toolkit runtime policy validation and controlled override modes:
  - partial override merge mode,
  - full override mode with mandatory waiver metadata.
- Added explicit project override directive in `.control-loop/policy.json`:
  - `"policy_override": { "mode": "partial" }`
- Adopted toolkit self-CI and toolkit-level tests for policy/process enforcement.

## 2026-02-24 - AI settings and session evidence enforcement
- Added project AI settings file at `.control-loop/ai_settings.json`.
- Added context-priority index at `docs/CONTEXT_INDEX.md`.
- Added session evidence workflow:
  - `docs/sessions/README.md`
  - `docs/sessions/TEMPLATE.md`
  - session log for this change
- Updated policy required artifact lists to include AI settings, context index, and session docs.
- Extended shared toolkit (submodule working tree) with:
  - AI settings loader and schema validation,
  - global strict/advisory process switch,
  - session evidence checks in `process_guard`,
  - reusable templates for AI settings/context/session files.
