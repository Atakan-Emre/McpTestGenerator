"""Consistency checks across the CI/CD configuration files.

The Jenkins pipeline, the Makefile and the SonarQube configuration reference
each other by string. Nothing else catches it when one of them drifts - a
renamed Make target or a moved report path only shows up as a red build - so
those references are asserted here.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
JENKINSFILE = REPO_ROOT / "Jenkinsfile"
MAKEFILE = REPO_ROOT / "Makefile"
SONAR_PROPERTIES = REPO_ROOT / "sonar-project.properties"
PYPROJECT = REPO_ROOT / "pyproject.toml"


def _makefile_targets() -> set[str]:
    """Target names declared in the Makefile."""
    return {
        match.group(1)
        for match in re.finditer(r"^([a-zA-Z0-9_-]+):", MAKEFILE.read_text(encoding="utf-8"), re.M)
    }


def _sonar_settings() -> dict[str, str]:
    """Parse sonar-project.properties, joining backslash continuations."""
    text = SONAR_PROPERTIES.read_text(encoding="utf-8").replace("\\\n", "")
    settings: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        settings[key.strip()] = value.strip()
    return settings


class TestFilesExist:
    def test_ci_configuration_is_present(self):
        for path in (JENKINSFILE, MAKEFILE, SONAR_PROPERTIES):
            assert path.is_file(), f"{path.name} is missing"


class TestJenkinsfile:
    """The pipeline may only call targets the Makefile actually defines."""

    def test_every_make_target_invoked_exists(self):
        invoked = set(
            re.findall(r"make\s+([a-zA-Z0-9_-]+)", JENKINSFILE.read_text(encoding="utf-8"))
        )
        assert invoked, "the pipeline no longer delegates to the Makefile"

        missing = invoked - _makefile_targets()
        assert not missing, f"Jenkinsfile calls undefined Make target(s): {sorted(missing)}"

    def test_declares_the_expected_stages(self):
        text = JENKINSFILE.read_text(encoding="utf-8")
        for stage in (
            "Environment",
            "Static Analysis",
            "Tests",
            "Security",
            "SonarQube Analysis",
            "Quality Gate",
            "Package",
        ):
            assert f"stage('{stage}')" in text, f"missing stage: {stage}"

    def test_quality_gate_aborts_the_build(self):
        """A quality gate that does not fail the build is decorative."""
        text = JENKINSFILE.read_text(encoding="utf-8")
        assert "waitForQualityGate abortPipeline: true" in text

    def test_junit_results_are_published(self):
        text = JENKINSFILE.read_text(encoding="utf-8")
        assert "junit allowEmptyResults: false" in text
        assert "junit.xml" in text


class TestSonarConfiguration:
    """Sonar must point at reports the build actually writes."""

    @pytest.mark.parametrize(
        "setting",
        [
            "sonar.python.coverage.reportPaths",
            "sonar.junit.reportPaths",
            "sonar.python.ruff.reportPaths",
            "sonar.python.mypy.reportPaths",
            "sonar.python.bandit.reportPaths",
        ],
    )
    def test_report_path_is_produced_by_the_makefile(self, setting):
        settings = _sonar_settings()
        assert setting in settings, f"{setting} is not configured"

        report_path = settings[setting]
        assert report_path.startswith("reports/"), report_path

        filename = Path(report_path).name
        makefile = MAKEFILE.read_text(encoding="utf-8")
        assert filename in makefile, f"nothing in the Makefile writes {report_path}"

    def test_sources_and_tests_directories_exist(self):
        settings = _sonar_settings()
        assert (REPO_ROOT / settings["sonar.sources"]).is_dir()
        assert (REPO_ROOT / settings["sonar.tests"]).is_dir()

    def test_project_key_matches_the_package_name(self):
        settings = _sonar_settings()
        assert settings["sonar.projectKey"] == "qa-mcp"

    def test_python_version_covers_the_supported_interpreters(self):
        """Sonar must analyse the same versions the package claims to support."""
        settings = _sonar_settings()
        declared = {v.strip() for v in settings["sonar.python.version"].split(",")}

        pyproject = PYPROJECT.read_text(encoding="utf-8")
        classifiers = set(re.findall(r"Programming Language :: Python :: (\d+\.\d+)", pyproject))

        assert declared == classifiers, (
            f"sonar.python.version {sorted(declared)} != classifiers {sorted(classifiers)}"
        )

    def test_coverage_excludes_the_test_tree(self):
        settings = _sonar_settings()
        assert "tests/**" in settings["sonar.coverage.exclusions"]


class TestMakefile:
    """Targets the pipeline and the contributor docs rely on."""

    @pytest.mark.parametrize(
        "target",
        [
            "install",
            "install-ci",
            "lint",
            "format-check",
            "typecheck",
            "test",
            "security",
            "audit",
            "build",
            "sonar",
            "ci",
            "clean",
        ],
    )
    def test_target_is_defined(self, target):
        assert target in _makefile_targets()

    def test_ci_target_chains_the_gates(self):
        makefile = MAKEFILE.read_text(encoding="utf-8")
        match = re.search(r"^ci:\s*(.+?)(?:\s*##.*)?$", makefile, re.M)
        assert match, "no `ci` target"

        prerequisites = match.group(1).split()
        for required in ("quality", "test", "security"):
            assert required in prerequisites, f"`make ci` does not run {required}"

    def test_ci_extra_provides_the_analysis_tools(self):
        """`make install-ci` installs the `ci` extra; it must carry the tools."""
        pyproject = PYPROJECT.read_text(encoding="utf-8")
        ci_extra = re.search(r"^ci = \[(.*?)\]", pyproject, re.S | re.M)
        assert ci_extra, "pyproject has no `ci` optional-dependency group"

        for tool in ("bandit", "pip-audit", "build"):
            assert tool in ci_extra.group(1), f"`ci` extra is missing {tool}"


class TestDocumentationLinks:
    """Relative links in the top-level docs must resolve."""

    @pytest.mark.parametrize("document", ["README.md", "CONTRIBUTING.md", "docs/CI-CD.md"])
    def test_relative_links_point_at_existing_files(self, document):
        text = (REPO_ROOT / document).read_text(encoding="utf-8")
        base = (REPO_ROOT / document).parent

        broken = [
            target
            for target in set(re.findall(r"\]\((?!https?:|mailto:)([^)#]+)\)", text))
            if not (base / target).exists()
        ]
        assert not broken, f"{document} has broken links: {sorted(broken)}"

    def test_readme_does_not_link_through_a_search_engine(self):
        """Regression: doc links were `google.com/search?q=USAGE.md`."""
        assert "google.com/search" not in (REPO_ROOT / "README.md").read_text(encoding="utf-8")


class TestVersionConsistency:
    """One version number, repeated in six places."""

    @staticmethod
    def _package_version() -> str:
        import qa_mcp

        return qa_mcp.__version__

    def test_pyproject_matches_the_package(self):
        pyproject = PYPROJECT.read_text(encoding="utf-8")
        declared = re.search(r'^version = "([^"]+)"', pyproject, re.M)
        assert declared and declared.group(1) == self._package_version()

    @pytest.mark.parametrize(
        ("document", "pattern"),
        [
            ("Dockerfile", r'org\.opencontainers\.image\.version="([^"]+)"'),
            ("docker-compose.yml", r"qa-mcp:\$\{VERSION:-([^}]+)\}"),
            ("DOCKERHUB.md", r"\| `([\d.]+)` \| Current stable release \|"),
        ],
    )
    def test_release_metadata_matches_the_package(self, document, pattern):
        text = (REPO_ROOT / document).read_text(encoding="utf-8")
        found = {m.group(1) for m in re.finditer(pattern, text)}

        assert found, f"no version found in {document}"
        assert found == {self._package_version()}, f"{document} declares {sorted(found)}"

    def test_changelog_documents_the_current_version(self):
        changelog = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        released = re.findall(r"^## \[(\d+\.\d+\.\d+)\]", changelog, re.M)

        assert released, "the changelog lists no releases"
        assert released[0] == self._package_version(), (
            f"newest changelog entry is {released[0]}, package is {self._package_version()}"
        )
