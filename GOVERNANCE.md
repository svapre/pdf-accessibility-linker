# Governance Rules

## Purpose
This file defines how we make and validate engineering decisions, not just code changes.

## Core Rule
No significant code change is considered valid unless both are true:
1. The code passes quality gates.
2. The change process passes governance gates.

## Proposal-First Workflow
Before changing implementation files (`core/`, `main.py`, `data_models/`, `utils/`):
1. Create or update a proposal in `docs/proposals/`.
2. Include a design-compliance section in the proposal.
3. List any intentional design violations and why they are accepted.

## Design Compliance Rule
Every plan or proposed implementation must be checked against `DESIGN.md` guardrails.
If an option violates a guardrail but is still the best tradeoff, explicitly mark:
1. Violated guardrail
2. Why violation is needed
3. Risk and mitigation

## Process-Change Rule
If process files change (`SPEC.md`, `SYSTEM.md`, `AGENTS.md`, gate scripts, CI workflow):
1. Update `docs/PROCESS_CHANGELOG.md` in the same branch.
2. Explain what changed and why.

## Merge Rule
The default branch should only receive merges that pass:
1. CI checks
2. `scripts/control_gate.py --mode ci`
3. `scripts/process_guard.py --mode ci`

