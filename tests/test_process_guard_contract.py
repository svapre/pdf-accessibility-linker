from pathlib import Path

from scripts.process_guard import check_proposal_sections, evaluate_change_coupling, load_policy


def test_implementation_change_requires_proposal_and_design_update():
    changed = {"core/profiler.py"}
    failures = evaluate_change_coupling(changed)

    assert any("proposal update" in item for item in failures)
    assert any("DESIGN.md" in item or "docs/adr/" in item for item in failures)


def test_implementation_change_with_required_design_artifacts_passes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    proposal = Path("docs/proposals/2026-02-24-profiler-adjustment.md")
    proposal.parent.mkdir(parents=True, exist_ok=True)
    proposal.write_text(
        "\n".join(
            [
                "# Proposal",
                "## Problem",
                "## Options Considered",
                "## Work Mode",
                "- Selected work mode: design",
                "- Why this mode: architecture and tradeoff analysis required",
                "## Design Parameter Compliance",
                "- Structural correctness:",
                "- Deterministic behavior:",
                "- Traceable decisions:",
                "- No silent guessing:",
                "- Configuration over hardcoding:",
                "- Config externalization evidence: values loaded from config files",
                "- Generality scope: chaptered textbooks and policy documents",
                "- Validation coverage evidence: validated on three representative documents",
                "- Holdout validation evidence: one unseen PDF validated without failures",
                "- Single-case exception: NONE",
                "- Manual review evidence: N/A",
                "- Determinism evidence: repeated run produced same output hash",
                "- Idempotent processing:",
                "- Idempotency evidence: second run produced no additional bookmarks/links",
                "- Fail loudly on invalid state:",
                "- Performance budget awareness:",
                "- Extensible module boundaries:",
                "- Evidence-backed claims:",
                "## Exception Register",
                "- Violated parameter(s):",
                "- Why alternatives are worse:",
                "- Risk:",
                "- Mitigation:",
                "- Rollback plan:",
                "## Decision Scorecard",
                "- Correctness impact:",
                "- Reliability impact:",
                "- Complexity impact:",
                "- Delivery speed impact:",
                "- Operational risk:",
                "- Why this is best overall now:",
                "## Assumptions and Unknowns",
                "- Assumptions made: NONE",
                "- Unknowns: NONE",
                "- Clarifying questions for user: NONE",
                "## Approval Checkpoint",
                "- User confirmation required before implementation: no",
                "- User confirmation evidence: N/A",
                "## Decision",
                "## Risks and Mitigations",
                "## Validation Plan",
            ]
        ),
        encoding="utf-8",
    )
    session_log = Path("docs/sessions/2026-02-24-profiler-adjustment.md")
    session_log.parent.mkdir(parents=True, exist_ok=True)
    session_log.write_text(
        "\n".join(
            [
                "# Session Log",
                "## Request",
                "- Session ID: test-session",
                "- Selected work mode: design",
                "- Task summary: profiler adjustment",
                "## Planned Actions",
                "- Files planned to change: core/profiler.py",
                "- Why these changes: improve architecture",
                "- Workflow phase: implement",
                "- Change scope: project",
                "- Implementation approval token: APPROVE_IMPLEMENT",
                "## User Approval",
                "- User approval status: yes",
                "- User approval evidence: approved in test setup",
                "## AI Settings Applied",
                "- confirm_before_changes: true",
                "- assumption_policy: ask_first",
                "- process_enforcement_mode: strict",
                "## Execution Log",
                "- Failure observed: none",
                "- Corrective change made: n/a",
                "- Validation checks run: pytest",
                "## Results and Feedback",
                "- Feedback received: none",
                "- Feedback applied: none",
            ]
        ),
        encoding="utf-8",
    )

    changed = {
        "core/profiler.py",
        "docs/proposals/2026-02-24-profiler-adjustment.md",
        "docs/adr/2026-02-24-profiler-adjustment.md",
        "docs/sessions/2026-02-24-profiler-adjustment.md",
    }
    failures = evaluate_change_coupling(changed)

    assert not failures


def test_process_change_requires_process_changelog_update():
    changed = {"SPEC.md"}
    failures = evaluate_change_coupling(changed)

    assert any("PROCESS_CHANGELOG" in item for item in failures)


def test_process_change_with_changelog_update_passes():
    changed = {"SPEC.md", "docs/PROCESS_CHANGELOG.md"}
    failures = evaluate_change_coupling(changed)

    assert not failures


def test_template_change_requires_process_changelog_update():
    changed = {"docs/proposals/TEMPLATE.md"}
    failures = evaluate_change_coupling(changed)

    assert any("PROCESS_CHANGELOG" in item for item in failures)


def test_proposal_sections_fail_when_required_headings_are_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    proposal = Path("docs/proposals/2026-02-24-missing-sections.md")
    proposal.parent.mkdir(parents=True, exist_ok=True)
    proposal.write_text("# Proposal\n## Problem", encoding="utf-8")

    failures = check_proposal_sections([proposal.as_posix()], load_policy())

    assert any("Options Considered" in item for item in failures)


def test_proposal_sections_pass_with_required_headings(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    proposal = Path("docs/proposals/2026-02-24-complete.md")
    proposal.parent.mkdir(parents=True, exist_ok=True)
    proposal.write_text(
        "\n".join(
            [
                "# Proposal",
                "## Problem",
                "## Options Considered",
                "## Work Mode",
                "- Selected work mode: routine",
                "- Why this mode: routine implementation and validation tasks",
                "## Design Parameter Compliance",
                "- Structural correctness:",
                "- Deterministic behavior:",
                "- Traceable decisions:",
                "- No silent guessing:",
                "- Configuration over hardcoding:",
                "- Config externalization evidence: values loaded from config files",
                "- Generality scope: chaptered textbooks and policy documents",
                "- Validation coverage evidence: validated on three representative documents",
                "- Holdout validation evidence: one unseen PDF validated without failures",
                "- Single-case exception: NONE",
                "- Manual review evidence: N/A",
                "- Determinism evidence: repeated run produced same output hash",
                "- Idempotent processing:",
                "- Idempotency evidence: second run produced no additional bookmarks/links",
                "- Fail loudly on invalid state:",
                "- Performance budget awareness:",
                "- Extensible module boundaries:",
                "- Evidence-backed claims:",
                "## Exception Register",
                "- Violated parameter(s):",
                "- Why alternatives are worse:",
                "- Risk:",
                "- Mitigation:",
                "- Rollback plan:",
                "## Decision Scorecard",
                "- Correctness impact:",
                "- Reliability impact:",
                "- Complexity impact:",
                "- Delivery speed impact:",
                "- Operational risk:",
                "- Why this is best overall now:",
                "## Assumptions and Unknowns",
                "- Assumptions made: NONE",
                "- Unknowns: NONE",
                "- Clarifying questions for user: NONE",
                "## Approval Checkpoint",
                "- User confirmation required before implementation: no",
                "- User confirmation evidence: N/A",
                "## Decision",
                "## Risks and Mitigations",
                "## Validation Plan",
            ]
        ),
        encoding="utf-8",
    )

    failures = check_proposal_sections([proposal.as_posix()], load_policy())

    assert not failures


def test_non_none_assumptions_require_confirmation_and_evidence(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    proposal = Path("docs/proposals/2026-02-24-assumptions.md")
    proposal.parent.mkdir(parents=True, exist_ok=True)
    proposal.write_text(
        "\n".join(
            [
                "# Proposal",
                "## Problem",
                "## Options Considered",
                "## Work Mode",
                "- Selected work mode: design",
                "- Why this mode: design decision needed",
                "## Design Parameter Compliance",
                "- Structural correctness:",
                "- Deterministic behavior:",
                "- Traceable decisions:",
                "- No silent guessing:",
                "- Configuration over hardcoding:",
                "- Config externalization evidence: values loaded from config files",
                "- Generality scope: chaptered textbooks and policy documents",
                "- Validation coverage evidence: validated on three representative documents",
                "- Holdout validation evidence: one unseen PDF validated without failures",
                "- Single-case exception: NONE",
                "- Manual review evidence: N/A",
                "- Determinism evidence: repeated run produced same output hash",
                "- Idempotent processing:",
                "- Idempotency evidence: second run produced no additional bookmarks/links",
                "- Fail loudly on invalid state:",
                "- Performance budget awareness:",
                "- Extensible module boundaries:",
                "- Evidence-backed claims:",
                "## Exception Register",
                "- Violated parameter(s):",
                "- Why alternatives are worse:",
                "- Risk:",
                "- Mitigation:",
                "- Rollback plan:",
                "## Decision Scorecard",
                "- Correctness impact:",
                "- Reliability impact:",
                "- Complexity impact:",
                "- Delivery speed impact:",
                "- Operational risk:",
                "- Why this is best overall now:",
                "## Assumptions and Unknowns",
                "- Assumptions made: we expect API responses to be stable",
                "- Unknowns: production load profile",
                "- Clarifying questions for user: expected latency target",
                "## Approval Checkpoint",
                "- User confirmation required before implementation: no",
                "- User confirmation evidence: N/A",
                "## Decision",
                "## Risks and Mitigations",
                "## Validation Plan",
            ]
        ),
        encoding="utf-8",
    )

    failures = check_proposal_sections([proposal.as_posix()], load_policy())

    assert any("lists assumptions but does not require user confirmation" in item for item in failures)


def test_implementation_change_requires_session_log_update():
    changed = {"core/profiler.py", "docs/proposals/2026-02-24-profiler-adjustment.md", "docs/adr/2026-02-24.md"}
    failures = evaluate_change_coupling(changed)

    assert any("session log update" in item.lower() for item in failures)


def test_static_guard_detects_absolute_path_literal_as_failure(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    policy = load_policy(repo_root=tmp_path)
    static_cfg = policy.setdefault("process_guard", {}).setdefault("static_guard_rules", {})
    static_cfg.update(
        {
            "enabled": True,
            "scan_extensions": [".py"],
            "include_prefixes": ["core/"],
            "include_files": ["main.py"],
            "rules": [
                {
                    "name": "absolute-path-literal",
                    "pattern": r"[A-Za-z]:\\\\",
                    "message": "absolute path literal detected; use config inputs instead",
                    "enforcement": "strict",
                }
            ],
        }
    )

    core_file = Path("core/profiler.py")
    core_file.parent.mkdir(parents=True, exist_ok=True)
    core_file.write_text("BASE = 'C:\\\\temp\\\\pdfs'\n", encoding="utf-8")

    failures = evaluate_change_coupling({core_file.as_posix()}, policy)

    assert any("absolute path literal" in item.lower() for item in failures)
