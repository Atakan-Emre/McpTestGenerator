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
ENV_EXAMPLE = REPO_ROOT / ".env.example"

CI_FILES = (JENKINSFILE, MAKEFILE, SONAR_PROPERTIES, ENV_EXAMPLE)

# These assert properties of the repository, not of the installed package, so
# they are meaningless where the source tree is absent - the development Docker
# image, for instance, copies only `src/` and `tests/`. Skip only when none of
# the files are there: a checkout missing just one of them is a real defect and
# must still fail.
pytestmark = pytest.mark.skipif(
    not any(path.exists() for path in CI_FILES),
    reason="not a source checkout - CI configuration files are not present",
)


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

    def test_configurable_names_are_parameters_not_literals(self):
        """An organisation must be able to run this without editing the file."""
        text = JENKINSFILE.read_text(encoding="utf-8")

        for parameter in (
            "SONARQUBE_ENV",
            "SONAR_SCANNER_TOOL",
            "SONAR_PROJECT_KEY",
            "PYTHON",
            "DOCKER_REGISTRY",
            "DOCKER_CREDENTIALS_ID",
        ):
            assert f"name: '{parameter}'" in text, f"{parameter} is not a build parameter"
            assert f"params.{parameter}" in text, f"{parameter} is declared but never used"

    def test_image_publishing_is_opt_in(self):
        """A build must not push to a registry unless asked to."""
        text = JENKINSFILE.read_text(encoding="utf-8")
        assert "name: 'PUBLISH_IMAGE'" in text
        assert "defaultValue: false" in text
        assert "params.PUBLISH_IMAGE" in text

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
            "check-config",
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


class TestSettingsDocumentation:
    """`.env.example` is the contract an organisation reads; keep it honest."""

    def test_every_setting_is_documented(self):
        """A setting nobody can discover may as well not exist."""
        from qa_mcp.config import LintSettings, Settings, XraySettings

        text = ENV_EXAMPLE.read_text(encoding="utf-8")
        documented = set(re.findall(r"^#?\s*(QA_MCP_[A-Z_]+)=", text, re.M))

        declared = set()
        for model, prefix in (
            (Settings, "QA_MCP_"),
            (LintSettings, "QA_MCP_LINT_"),
            (XraySettings, "QA_MCP_XRAY_"),
        ):
            for name in model.model_fields:
                if name in ("lint", "xray"):
                    continue
                declared.add(prefix + name.upper())

        assert not declared - documented, f"undocumented settings: {sorted(declared - documented)}"
        assert not documented - declared, f"documented but unknown: {sorted(documented - declared)}"

    def test_the_example_stays_offline_by_default(self):
        """Copying the file must not switch on a tenant or write access."""
        text = ENV_EXAMPLE.read_text(encoding="utf-8")
        assert "QA_MCP_XRAY_ENABLED=false" in text
        assert "QA_MCP_ENABLE_WRITE_TOOLS=false" in text
