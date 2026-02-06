# Contributing to QA-MCP

Thank you for your interest in contributing to QA-MCP! 🎉

This document provides guidelines for contributing to the project.

## 🚀 Getting Started

### Prerequisites

- Python 3.11 or higher
- Git
- `uv` package manager (recommended) or `pip`

### Development Environment Setup

1. **Fork and clone the repository**

```bash
git clone https://github.com/YOUR-USERNAME/McpTestGenerator.git
cd McpTestGenerator
```

2. **Create a virtual environment**

```bash
# Using Python's venv
python -m venv .venv

# Activate on macOS/Linux
source .venv/bin/activate

# Activate on Windows
.venv\Scripts\activate
```

3. **Install dependencies**

```bash
# Using uv (recommended - faster, uses locked dependencies)
pip install uv
uv pip install -e ".[dev]"

# Or using pip
pip install -e ".[dev]"
```

4. **Install pre-commit hooks**

```bash
pre-commit install
```

## 🧪 Running Tests

### Run all tests

```bash
pytest tests/ -v
```

### Run tests with coverage

```bash
pytest tests/ --cov=qa_mcp --cov-report=html --cov-report=term
```

Coverage report will be generated in `htmlcov/` directory.

**Minimum coverage requirement: 80%**

### Run specific test file

```bash
pytest tests/test_specific.py -v
```

## 🔍 Code Quality

We use automated tools to maintain code quality:

### Linting with Ruff

```bash
# Check for linting issues
ruff check src/

# Auto-fix linting issues
ruff check src/ --fix
```

### Formatting with Ruff

```bash
# Check formatting
ruff format --check src/

# Auto-format code
ruff format src/
```

### Type Checking with MyPy

```bash
mypy src/qa_mcp --ignore-missing-imports
```

### Run all checks at once

The pre-commit hooks will run all checks automatically before each commit. To run them manually:

```bash
pre-commit run --all-files
```

## 📝 Coding Standards

### Code Style

- Follow PEP 8 guidelines
- Use type hints for function parameters and return values
- Maximum line length: 100 characters
- Use descriptive variable and function names

### Documentation

- Add docstrings to all public functions, classes, and modules
- Use Google-style docstrings format
- Update README.md if adding new features
- Update CHANGELOG.md following [Keep a Changelog](https://keepachangelog.com/) format

### Example Docstring

```python
def generate_test_case(feature: str, criteria: list[str]) -> TestCase:
    """Generate a standardized test case from feature description.
    
    Args:
        feature: Feature description or user story
        criteria: List of acceptance criteria
        
    Returns:
        Standardized test case object
        
    Raises:
        ValidationError: If feature or criteria are invalid
    """
    pass
```

## 🌿 Branching Strategy

### Branch Naming Convention

- `feature/` - New features (e.g., `feature/add-negative-scenarios`)
- `bugfix/` - Bug fixes (e.g., `bugfix/fix-xray-export`)
- `docs/` - Documentation updates (e.g., `docs/update-contributing`)
- `refactor/` - Code refactoring (e.g., `refactor/cleanup-validators`)
- `test/` - Test additions/improvements (e.g., `test/add-integration-tests`)

### Workflow

1. Create a new branch from `main`
```bash
git checkout -b feature/your-feature-name
```

2. Make your changes and commit
```bash
git add .
git commit -m "feat: add new feature"
```

3. Push to your fork
```bash
git push origin feature/your-feature-name
```

4. Open a Pull Request

## 📬 Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### Examples

```bash
feat(testcase): add negative scenario generation
fix(xray): correct field mapping for manual tests
docs(readme): update installation instructions
test(lint): add edge case tests for lint rules
```

## 🔄 Pull Request Process

### Before Submitting

- [ ] Run all tests and ensure they pass
- [ ] Run linters and formatters (`pre-commit run --all-files`)
- [ ] Update documentation if needed
- [ ] Add or update tests for new functionality
- [ ] Update CHANGELOG.md with your changes
- [ ] Ensure code coverage is maintained (minimum 80%)

### Pull Request Template

When opening a PR, include:

1. **Description**: What does this PR do?
2. **Related Issues**: Link to any related issues
3. **Type of Change**: Feature, bugfix, docs, etc.
4. **Testing**: How was this tested?
5. **Screenshots**: If applicable (for UI changes)
6. **Checklist**: Use the checklist above

### Review Process

1. At least one maintainer review is required
2. All CI checks must pass
3. Code coverage must not decrease
4. Documentation must be updated if needed

## 🐛 Reporting Bugs

### Before Reporting

- Check if the bug has already been reported
- Ensure you're using the latest version
- Verify the bug is reproducible

### Bug Report Template

```markdown
**Describe the bug**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. ...
2. ...

**Expected behavior**
What you expected to happen.

**Actual behavior**
What actually happened.

**Environment**
- OS: [e.g., macOS 13.0]
- Python version: [e.g., 3.11.5]
- QA-MCP version: [e.g., 1.0.0]

**Additional context**
Any other relevant information.
```

## 💡 Feature Requests

We welcome feature requests! Please:

1. Check if the feature has already been requested
2. Provide a clear use case
3. Explain why this feature would be useful
4. Consider if it aligns with the project's goals

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

## 🤝 Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inspiring community for all.

### Our Standards

- Be respectful and inclusive
- Accept constructive criticism gracefully
- Focus on what's best for the community
- Show empathy towards others

### Unacceptable Behavior

- Harassment or discriminatory language
- Trolling or insulting comments
- Personal or political attacks
- Publishing others' private information

## 📞 Getting Help

- 💬 **Discussions**: Use GitHub Discussions for questions
- 🐛 **Issues**: Use GitHub Issues for bug reports
- 📧 **Email**: satakanemre@gmail.com

## 🙏 Thank You!

Your contributions are what make QA-MCP better. We appreciate your time and effort!

---

**Happy Contributing!** 🚀
