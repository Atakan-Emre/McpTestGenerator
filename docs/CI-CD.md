# CI/CD: Jenkins & SonarQube

QA-MCP ships two independent pipelines:

| Pipeline | File | Purpose |
| --- | --- | --- |
| GitHub Actions | [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) | Public PR checks, matrix builds, Docker build |
| Jenkins | [`Jenkinsfile`](../Jenkinsfile) | Internal builds with SonarQube analysis and a blocking quality gate |

Both drive the same checks. The Jenkins pipeline delegates every stage to a
[`Makefile`](../Makefile) target, so any failing stage can be reproduced
locally with the identical command.

---

## Running the pipeline locally

```bash
make install-ci
make ci
```

`make ci` runs static analysis, the test suite and the security scan, writing
every machine-readable report into `reports/`:

| File | Produced by | Consumed by |
| --- | --- | --- |
| `reports/junit.xml` | `make test` | Jenkins `junit`, `sonar.junit.reportPaths` |
| `reports/coverage.xml` | `make test` | `sonar.python.coverage.reportPaths` |
| `reports/htmlcov/` | `make test` | Jenkins `publishHTML` |
| `reports/ruff.json` | `make lint` | `sonar.python.ruff.reportPaths` |
| `reports/mypy.txt` | `make typecheck` | `sonar.python.mypy.reportPaths` |
| `reports/bandit.json` | `make security` | `sonar.python.bandit.reportPaths` |
| `reports/pip-audit.json` | `make audit` | Build artifact |

`reports/` is git-ignored and excluded from the Docker build context.

Individual targets:

```bash
make help
```

---

## Jenkins setup

### Required plugins

| Plugin | Used for |
| --- | --- |
| Pipeline | Declarative pipeline support |
| JUnit | `junit` step — test result trends |
| SonarQube Scanner for Jenkins | `withSonarQubeEnv`, `waitForQualityGate`, `tool` |
| HTML Publisher | `publishHTML` — coverage report |
| Workspace Cleanup | `cleanWs` |

### Required global configuration

1. **Manage Jenkins → System → SonarQube servers**
   Add a server named **`SonarQube`** with its URL and an authentication token.
   Tick *Enable injection of SonarQube server configuration*.
   The name must match `SONARQUBE_ENV` in the `Jenkinsfile`.

2. **Manage Jenkins → Tools → SonarQube Scanner installations**
   Add an installation named **`SonarScanner`**.
   The name must match `SONAR_SCANNER_TOOL` in the `Jenkinsfile`.

3. **SonarQube → Administration → Configuration → Webhooks**
   Add a webhook pointing at `<jenkins-url>/sonarqube-webhook/`.
   Without it the `Quality Gate` stage blocks until its 10-minute timeout.

4. **Agent requirements**
   `python3.11` (or whatever `PYTHON` is set to), `make`, and `git` on `PATH`.
   Docker is optional — the `Docker Build` stage is skipped when the `docker`
   binary is absent.

### Pipeline stages

| Stage | Command | On failure |
| --- | --- | --- |
| Environment | `make install-ci` | **fail** |
| Static Analysis → Ruff Lint | `make lint` | unstable |
| Static Analysis → Format Check | `make format-check` | **fail** |
| Static Analysis → Type Check | `make typecheck` | unstable |
| Tests | `make test` | **fail** |
| Security → Bandit | `make security` | **fail** (medium severity and above) |
| Security → Dependency Audit | `make audit` | unstable |
| SonarQube Analysis | `sonar-scanner` | **fail** |
| Quality Gate | `waitForQualityGate` | **fail** |
| Package | `make build` | **fail** |
| Docker Build | `docker build` | **fail** (skipped without Docker) |

Lint and type findings mark the build *unstable* rather than failing it: the
reports are already written and handed to SonarQube, which owns the decision
through the quality gate. Formatting and tests fail outright, because those are
unambiguous and always fixable by the author.

---

## SonarQube

Analysis is configured in [`sonar-project.properties`](../sonar-project.properties).
Nothing is analysed twice: Sonar runs its own Python rules and additionally
*imports* the Ruff, MyPy and Bandit findings produced by the build.

> **Version note.** `sonar.python.ruff.reportPaths` requires SonarQube 10.2 or
> newer. On an older server, delete that line instead of leaving it pointing at
> a report nothing reads.

`sonar.projectVersion` is not hardcoded — the `sonar` Make target and the
Jenkins pipeline both read it from `qa_mcp.__version__`, so it cannot drift from
the released version.

### Local SonarQube

```bash
docker compose -f docker-compose.sonarqube.yml up -d
# wait for http://localhost:9000 to answer (admin / admin)
# create a user token, then:

make ci
SONAR_TOKEN=<token> SONAR_HOST_URL=http://localhost:9000 make sonar
```

Or run the scanner in a container, without installing it:

```bash
make ci
SONAR_TOKEN=<token> docker compose -f docker-compose.sonarqube.yml --profile scan run --rm scanner
```

The compose stack uses default credentials and no backups. It is for local
configuration work only — never expose it.

### Suggested quality gate

The default *Sonar way* gate works as-is. For this project, tighten coverage on
new code:

| Metric | Condition |
| --- | --- |
| Coverage on new code | ≥ 80 % |
| Duplicated lines on new code | ≤ 3 % |
| Maintainability / Reliability / Security rating on new code | A |
| Security hotspots reviewed | 100 % |

---

## Keeping the configuration honest

[`tests/test_ci_config.py`](../tests/test_ci_config.py) asserts the references
between these files as part of the normal test suite:

- every `make <target>` the `Jenkinsfile` invokes is defined in the `Makefile`
- every `sonar.*.reportPaths` entry points at a report the `Makefile` writes
- `sonar.python.version` matches the Python classifiers in `pyproject.toml`
- the `ci` extra carries the tools `make install-ci` expects
- the quality gate is configured to abort the build

So a renamed target or a moved report path fails a test instead of quietly
producing an empty SonarQube analysis.
