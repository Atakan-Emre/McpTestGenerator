"""
Test Case Standards and Templates.

Defines the rules and structure for standardized test cases.
"""

from typing import Any

from pydantic import BaseModel, Field


class FieldRequirement(BaseModel):
    """Requirement definition for a field."""

    required: bool = True
    min_length: int | None = None
    max_length: int | None = None
    allowed_values: list[str] | None = None
    pattern: str | None = None
    description: str = ""


class TestCaseStandard(BaseModel):
    """
    Test case standard definition.

    This defines what makes a "good" test case according to organizational standards.
    """

    version: str = Field("1.0", description="Standard version")
    name: str = Field("QA-MCP Test Case Standard", description="Standard name")

    # Field requirements
    fields: dict[str, FieldRequirement] = Field(
        default_factory=lambda: {
            "title": FieldRequirement(
                required=True,
                min_length=10,
                max_length=200,
                description="Clear, descriptive title that indicates what is being tested",
            ),
            "description": FieldRequirement(
                required=True,
                min_length=20,
                description="Detailed description explaining the purpose and scope",
            ),
            "preconditions": FieldRequirement(
                required=True,
                min_length=1,  # At least one precondition
                description="Conditions that must be true before execution",
            ),
            "steps": FieldRequirement(
                required=True,
                min_length=1,
                description="At least one test step with action and expected result",
            ),
            "expected_result": FieldRequirement(
                required=True, min_length=10, description="Clear, verifiable expected outcome"
            ),
            "test_data": FieldRequirement(
                required=False, description="Specific data values used in testing"
            ),
            "risk_level": FieldRequirement(
                required=True,
                allowed_values=["low", "medium", "high", "critical"],
                description="Risk classification",
            ),
            "priority": FieldRequirement(
                required=True,
                allowed_values=["P0", "P1", "P2", "P3"],
                description="Execution priority",
            ),
            "tags": FieldRequirement(required=False, description="Categorization tags"),
            "labels": FieldRequirement(
                required=False, description="Suite labels (smoke, regression, etc.)"
            ),
        }
    )

    # Quality rules
    quality_rules: dict[str, Any] = Field(
        default_factory=lambda: {
            "title": {
                "no_generic_words": ["test", "check", "verify"],  # Should be more specific
                "must_contain_action": True,
            },
            "steps": {
                "max_steps": 15,
                "min_steps": 1,
                "each_step_has_expected": True,
            },
            "test_data": {
                "boundary_values_recommended": True,
                "negative_cases_recommended": True,
            },
            "coverage": {
                "positive_scenario_required": True,
                "negative_scenario_recommended": True,
                "boundary_testing_recommended": True,
            },
        }
    )

    # Scoring weights
    scoring_weights: dict[str, int] = Field(
        default_factory=lambda: {
            "title_quality": 10,
            "description_quality": 10,
            "preconditions_present": 15,
            "steps_quality": 20,
            "expected_result_quality": 15,
            "test_data_present": 10,
            "risk_level_set": 5,
            "priority_set": 5,
            "tags_present": 5,
            "traceability": 5,
        }
    )

    # Minimum passing score
    minimum_score: int = Field(60, description="Minimum score to pass lint")

    @classmethod
    def get_default(cls) -> "TestCaseStandard":
        """Get the default standard."""
        return cls()

    def get_field_requirement(self, field_name: str) -> FieldRequirement | None:
        """Get requirement for a specific field."""
        return self.fields.get(field_name)

    def is_field_required(self, field_name: str) -> bool:
        """Check if a field is required."""
        req = self.fields.get(field_name)
        return req.required if req else False


# Predefined templates for different test types
TEST_TEMPLATES = {
    "api_test": {
        "title_pattern": "[API] {endpoint} - {scenario}",
        "required_tags": ["api"],
        "recommended_preconditions": [
            "API endpoint is accessible",
            "Authentication token is valid",
        ],
        "step_template": {
            "action": "Send {method} request to {endpoint} with {data}",
            "expected_result": "Response status is {status}, body contains {expected}",
        },
    },
    "ui_test": {
        "title_pattern": "[UI] {page} - {action}",
        "required_tags": ["ui", "e2e"],
        "recommended_preconditions": [
            "User is logged in",
            "Browser is {browser}",
        ],
        "step_template": {
            "action": "Navigate to {page}, {interaction}",
            "expected_result": "{element} is {state}",
        },
    },
    "integration_test": {
        "title_pattern": "[Integration] {system_a} ↔ {system_b} - {scenario}",
        "required_tags": ["integration"],
        "recommended_preconditions": [
            "Both systems are running",
            "Network connectivity is available",
        ],
    },
    "security_test": {
        "title_pattern": "[Security] {vulnerability_type} - {target}",
        "required_tags": ["security"],
        "recommended_preconditions": [
            "Test environment is isolated",
            "Security testing is authorized",
        ],
    },
    "performance_test": {
        "title_pattern": "[Performance] {metric} - {scenario}",
        "required_tags": ["performance", "non-functional"],
        "recommended_preconditions": [
            "Baseline metrics are established",
            "Load testing tools are configured",
        ],
    },
}


# Negative scenario patterns
NEGATIVE_SCENARIO_PATTERNS = [
    {
        "category": "input_validation",
        "patterns": [
            "Empty input",
            "Null value",
            "Special characters",
            "SQL injection attempt",
            "XSS attempt",
            "Exceeds maximum length",
            "Below minimum length",
            "Invalid format",
            "Invalid type",
        ],
    },
    {
        "category": "authentication",
        "patterns": [
            "Invalid credentials",
            "Expired session",
            "Missing token",
            "Invalid token",
            "Insufficient permissions",
        ],
    },
    {
        "category": "boundary",
        "patterns": [
            "Minimum value",
            "Maximum value",
            "Just below minimum",
            "Just above maximum",
            "Zero",
            "Negative number",
        ],
    },
    {
        "category": "error_handling",
        "patterns": [
            "Network timeout",
            "Server error (5xx)",
            "Resource not found (404)",
            "Rate limit exceeded",
            "Database connection failure",
        ],
    },
    {
        "category": "concurrency",
        "patterns": [
            "Simultaneous requests",
            "Race condition",
            "Deadlock scenario",
            "Data consistency under load",
        ],
    },
]


# Suite composition rules
SUITE_RULES = {
    "smoke": {
        "description": "Critical path tests that must pass for a build to be viable",
        "max_duration_minutes": 15,
        "priority_filter": ["P0"],
        "risk_filter": ["critical", "high"],
        "max_tests": 20,
        "selection_criteria": [
            "Core functionality",
            "Login/Authentication",
            "Main user journeys",
            "Critical integrations",
        ],
    },
    "sanity": {
        "description": "Quick check after deployment to verify basic functionality",
        "max_duration_minutes": 30,
        "priority_filter": ["P0", "P1"],
        "risk_filter": ["critical", "high"],
        "max_tests": 30,
        "selection_criteria": [
            "Recently changed features",
            "Smoke tests",
            "API health checks",
        ],
    },
    "regression": {
        "description": "Comprehensive test suite to catch regressions",
        "max_duration_minutes": 240,
        "priority_filter": ["P0", "P1", "P2"],
        "risk_filter": ["critical", "high", "medium"],
        "max_tests": 200,
        "selection_criteria": [
            "All functional areas",
            "Integration points",
            "Previously found bugs",
            "Edge cases",
        ],
    },
    "e2e": {
        "description": "End-to-end user journey tests",
        "max_duration_minutes": 120,
        "priority_filter": ["P0", "P1"],
        "risk_filter": ["critical", "high", "medium"],
        "max_tests": 50,
        "selection_criteria": [
            "Complete user workflows",
            "Cross-system integrations",
            "Business-critical paths",
        ],
    },
    "integration": {
        "description": "Contract and data-flow tests between components or systems",
        "max_duration_minutes": 90,
        "priority_filter": ["P0", "P1", "P2"],
        "risk_filter": ["critical", "high", "medium"],
        "max_tests": 80,
        "selection_criteria": [
            "Service-to-service contracts",
            "Third-party integrations",
            "Message queue and event flows",
            "Database interaction boundaries",
        ],
    },
    "performance": {
        "description": "Non-functional tests for latency, throughput, and resource use",
        "max_duration_minutes": 180,
        "priority_filter": ["P0", "P1", "P2"],
        "risk_filter": ["critical", "high"],
        "max_tests": 40,
        "selection_criteria": [
            "Response time under expected load",
            "Throughput at peak concurrency",
            "Resource consumption and leaks",
            "Degradation beyond capacity",
        ],
    },
}
