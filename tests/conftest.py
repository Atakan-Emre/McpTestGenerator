"""Pytest configuration and fixtures."""

import pytest


@pytest.fixture
def sample_testcase_dict():
    """Provide a sample test case dictionary."""
    return {
        "id": "TC-SAMPLE-001",
        "title": "Sample Test Case for Testing",
        "description": "This is a sample test case used for testing the QA-MCP tools.",
        "module": "sample",
        "feature": "sample-feature",
        "scenario_type": "positive",
        "risk_level": "medium",
        "priority": "P2",
        "preconditions": [
            "Sample precondition one",
            "Sample precondition two",
        ],
        "steps": [
            {
                "step_number": 1,
                "action": "Perform the first sample action",
                "expected_result": "First expected result is observed",
            },
            {
                "step_number": 2,
                "action": "Perform the second sample action",
                "expected_result": "Second expected result is observed",
            },
        ],
        "test_data": [
            {"name": "sample_input", "value": "test_value"},
        ],
        "expected_result": "Sample test case completes successfully",
        "tags": ["sample", "test"],
        "labels": ["regression"],
        "estimated_duration_minutes": 5,
        "requirements": ["REQ-SAMPLE-001"],
    }


@pytest.fixture
def minimal_testcase_dict():
    """Provide a minimal test case dictionary."""
    return {
        "title": "Minimal Test Case Title",
        "description": "Minimal test case description",
        "preconditions": ["Ready"],
        "steps": [
            {
                "step_number": 1,
                "action": "Do action",
                "expected_result": "See result",
            }
        ],
        "expected_result": "Test passes",
    }


@pytest.fixture
def sample_testcases_batch():
    """Provide a batch of test cases."""
    return [
        {
            "id": f"TC-BATCH-{i:03d}",
            "title": f"Batch Test Case Number {i}",
            "description": f"Description for batch test case {i}",
            "preconditions": ["Ready"],
            "steps": [
                {
                    "step_number": 1,
                    "action": f"Action for test {i}",
                    "expected_result": f"Result for test {i}",
                }
            ],
            "expected_result": f"Test {i} passes",
            "risk_level": "medium" if i % 2 == 0 else "high",
            "priority": "P1" if i % 3 == 0 else "P2",
            "module": f"module_{i % 3}",
        }
        for i in range(1, 6)
    ]
