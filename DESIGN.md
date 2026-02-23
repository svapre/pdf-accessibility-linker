# Design Guardrails

## Purpose
This file is the design baseline used during brainstorming and implementation reviews.

## Guardrails
1. Configuration over hardcoding:
   - Environment-specific values, thresholds, and credentials must not be hardcoded in business logic.
   - If a value must be fixed in code, document why.

2. Single source of truth for contracts:
   - Shared identifiers and formats (for example URNs) must have one canonical implementation.

3. Deterministic core pipeline:
   - Once inputs and configuration are fixed, pipeline behavior should be reproducible.

4. Fail loudly on invalid state:
   - Invalid references, bounds, or mapping assumptions should raise or log explicit faults.

5. Evidence-backed claims:
   - Architecture and process claims must reference code, tests, or CI evidence.

## Brainstorming Protocol
Every solution discussion should include:
1. Guardrails satisfied
2. Guardrails violated (if any)
3. Why the chosen tradeoff is still acceptable
4. Follow-up mitigation work

