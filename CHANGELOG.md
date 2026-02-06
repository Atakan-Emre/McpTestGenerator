# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Pre-commit hooks configuration for automated code quality checks
- Comprehensive CONTRIBUTING.md guide
- Dependency locking with uv

### Changed
- Enhanced README badges with CI status and code coverage

### Documentation
- Added PyPI publishing workflow and documentation
- Created GitHub release template

---

## [1.0.0] - 2025-01-15

### Added

- Initial release of QA-MCP
- **Tools:**
  - `testcase.generate` - Feature açıklamasından test case üretimi
  - `testcase.lint` - Test case kalite analizi ve skorlama
  - `testcase.normalize` - Farklı formatları standarda çevirme
  - `testcase.to_xray` - Xray import formatına dönüştürme
  - `suite.compose` - Smoke/Regression/E2E suite kompozisyonu
  - `suite.coverage_report` - Kapsama raporu oluşturma
- **Resources:**
  - `qa://standards/testcase/v1` - Test case standardı
  - `qa://checklists/lint-rules/v1` - Lint kuralları
  - `qa://mappings/xray/v1` - Xray alan eşlemesi
  - `qa://examples/good/*` - İyi test case örnekleri
  - `qa://examples/bad/*` - Kötü test case örnekleri
- **Prompts:**
  - `create-manual-test` - Manual test oluşturma şablonu
  - `select-smoke-tests` - Smoke test seçim şablonu
  - `generate-negative-scenarios` - Negatif senaryo üretim şablonu
  - `review-test-coverage` - Kapsam analizi şablonu
- **Infrastructure:**
  - Docker multi-arch support (amd64/arm64)
  - stdio transport (default)
  - Audit logging
  - Environment-based configuration

### Security

- Default stdio-only transport for maximum security
- Tool allowlist approach
- Parameter validation on all inputs
- Audit logging for all tool invocations
