"""Pytest configuration and fixtures."""

import asyncio
import contextlib
from contextlib import asynccontextmanager

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


@asynccontextmanager
async def mcp_session():
    """A real MCP client session talking to the server over in-memory streams.

    Calling ``mcp.call_tool`` directly raises on failure; the conversion into a
    result carrying ``is_error`` happens in the request handler above it. Only a
    genuine session exercises the contract clients actually see - including the
    audit interceptor, which sits in the same layer.

    Deliberately a context manager rather than a fixture: anyio refuses to exit
    a cancel scope in a different task than it was entered in, and pytest-asyncio
    may finalize a yielding fixture from another task. Used inside the test body,
    setup and teardown stay on one task.
    """
    from mcp import ClientSession
    from mcp.shared.memory import create_client_server_memory_streams

    from qa_mcp.server import mcp

    async with create_client_server_memory_streams() as (client_streams, server_streams):
        client_read, client_write = client_streams
        server_read, server_write = server_streams

        server = mcp._lowlevel_server
        task = asyncio.create_task(
            server.run(
                server_read,
                server_write,
                server.create_initialization_options(),
                raise_exceptions=False,
            )
        )
        try:
            async with ClientSession(client_read, client_write) as session:
                await session.initialize()
                yield session
        finally:
            task.cancel()
            with contextlib.suppress(BaseException):
                await task
