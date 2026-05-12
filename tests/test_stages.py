"""Tests for stage helper logic that doesn't require the API:
- has_critical_issues() correctly detects critical bullet issues
"""

from __future__ import annotations

from stitch.stages import has_critical_issues


def test_no_issues_is_not_critical():
    assert has_critical_issues({"verdict": "approve", "bullet_issues": []}) is False


def test_only_minor_issues_is_not_critical():
    review = {
        "verdict": "approve",
        "bullet_issues": [
            {"severity": "minor", "category": "phrasing"},
            {"severity": "minor", "category": "missed_keyword"},
        ],
    }
    assert has_critical_issues(review) is False


def test_one_critical_issue_is_critical():
    review = {
        "verdict": "revise",
        "bullet_issues": [
            {"severity": "minor", "category": "phrasing"},
            {"severity": "critical", "category": "fabrication"},
        ],
    }
    assert has_critical_issues(review) is True


def test_missing_severity_field_treated_as_non_critical():
    review = {"bullet_issues": [{"category": "fabrication"}]}
    assert has_critical_issues(review) is False


def test_missing_bullet_issues_field_is_safe():
    assert has_critical_issues({}) is False
