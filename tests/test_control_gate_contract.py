from scripts.control_gate import find_successful_run_for_head


def test_find_successful_run_for_head_returns_matching_ci_run():
    runs = [
        {
            "headSha": "abc",
            "status": "completed",
            "conclusion": "failure",
            "workflowName": "ci",
            "url": "https://example.invalid/1",
        },
        {
            "headSha": "abc",
            "status": "completed",
            "conclusion": "success",
            "workflowName": "ci",
            "url": "https://example.invalid/2",
        },
    ]

    hit = find_successful_run_for_head(runs, "abc", "ci")

    assert hit is not None
    assert hit["url"] == "https://example.invalid/2"


def test_find_successful_run_for_head_returns_none_when_no_match():
    runs = [
        {
            "headSha": "abc",
            "status": "in_progress",
            "conclusion": None,
            "workflowName": "ci",
            "url": "https://example.invalid/3",
        }
    ]

    assert find_successful_run_for_head(runs, "abc", "ci") is None
