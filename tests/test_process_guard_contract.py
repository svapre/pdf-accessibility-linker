from pathlib import Path

from scripts.process_guard import check_proposal_sections, evaluate_change_coupling


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
                "## Design Guardrails Check",
                "## Decision",
                "## Risks and Mitigations",
            ]
        ),
        encoding="utf-8",
    )

    changed = {
        "core/profiler.py",
        "docs/proposals/2026-02-24-profiler-adjustment.md",
        "docs/adr/2026-02-24-profiler-adjustment.md",
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


def test_proposal_sections_fail_when_required_headings_are_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    proposal = Path("docs/proposals/2026-02-24-missing-sections.md")
    proposal.parent.mkdir(parents=True, exist_ok=True)
    proposal.write_text("# Proposal\n## Problem", encoding="utf-8")

    failures = check_proposal_sections([proposal.as_posix()])

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
                "## Design Guardrails Check",
                "## Decision",
                "## Risks and Mitigations",
            ]
        ),
        encoding="utf-8",
    )

    failures = check_proposal_sections([proposal.as_posix()])

    assert not failures
