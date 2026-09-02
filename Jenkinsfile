// QA-MCP Jenkins pipeline.
//
// Every stage delegates to a Makefile target, so a failing build can be
// reproduced locally with the same command (`make lint`, `make test`, ...).
//
// Required Jenkins plugins:
//   - Pipeline, Pipeline: Stage View
//   - JUnit
//   - SonarQube Scanner for Jenkins   (withSonarQubeEnv / waitForQualityGate)
//   - Warnings Next Generation        (optional; see the Static Analysis stage)
//
// Required Jenkins configuration:
//   - A SonarQube server named by SONARQUBE_ENV below
//     (Manage Jenkins -> System -> SonarQube servers)
//   - A SonarScanner tool named by SONAR_SCANNER_TOOL below
//     (Manage Jenkins -> Tools -> SonarQube Scanner installations)

pipeline {
    agent any

    options {
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '30', artifactNumToKeepStr: '10'))
        disableConcurrentBuilds()
        skipDefaultCheckout(false)
    }

    environment {
        // Interpreter used to create the build virtualenv.
        PYTHON = 'python3.11'
        VENV = '.venv'
        REPORTS = 'reports'

        // Names configured in Jenkins global settings.
        SONARQUBE_ENV = 'SonarQube'
        SONAR_SCANNER_TOOL = 'SonarScanner'

        // Keep pip quiet and reproducible on agents.
        PIP_DISABLE_PIP_VERSION_CHECK = '1'
        PYTHONDONTWRITEBYTECODE = '1'
    }

    stages {

        stage('Environment') {
            steps {
                sh '''
                    set -eu
                    "$PYTHON" --version
                    make install-ci PYTHON="$PYTHON" VENV="$VENV"
                    "$VENV"/bin/qa-mcp --version
                '''
            }
        }

        stage('Static Analysis') {
            parallel {
                stage('Ruff Lint') {
                    steps {
                        // The report has to exist even when the check fails, so
                        // SonarQube and the archive step still see the findings.
                        script {
                            def status = sh(script: 'make lint', returnStatus: true)
                            if (status != 0) {
                                unstable(message: 'Ruff reported lint violations')
                            }
                        }
                    }
                }
                stage('Format Check') {
                    steps {
                        sh 'make format-check'
                    }
                }
                stage('Type Check') {
                    steps {
                        script {
                            def status = sh(script: 'make typecheck', returnStatus: true)
                            if (status != 0) {
                                unstable(message: 'MyPy reported type errors')
                            }
                        }
                    }
                }
            }
        }

        stage('Tests') {
            steps {
                sh 'make test'
            }
            post {
                always {
                    junit allowEmptyResults: false, testResults: "${REPORTS}/junit.xml"
                    publishHTML(target: [
                        reportDir: "${REPORTS}/htmlcov",
                        reportFiles: 'index.html',
                        reportName: 'Coverage Report',
                        keepAll: true,
                        alwaysLinkToLastBuild: true,
                        allowMissing: true
                    ])
                }
            }
        }

        stage('Security') {
            parallel {
                stage('Bandit') {
                    steps {
                        sh 'make security'
                    }
                }
                stage('Dependency Audit') {
                    steps {
                        // Advisories appear without warning and are not the
                        // author's regression, so they mark the build unstable
                        // rather than failing it.
                        script {
                            def status = sh(script: 'make audit', returnStatus: true)
                            if (status != 0) {
                                unstable(message: 'pip-audit found vulnerable dependencies')
                            }
                        }
                    }
                }
            }
        }

        stage('SonarQube Analysis') {
            steps {
                script {
                    def scannerHome = tool name: env.SONAR_SCANNER_TOOL, type: 'hudson.plugins.sonar.SonarRunnerInstallation'
                    def projectVersion = sh(
                        script: '"$VENV"/bin/python -c "import qa_mcp; print(qa_mcp.__version__)"',
                        returnStdout: true
                    ).trim()

                    withSonarQubeEnv(env.SONARQUBE_ENV) {
                        sh """
                            ${scannerHome}/bin/sonar-scanner \
                              -Dsonar.projectVersion=${projectVersion} \
                              -Dsonar.branch.name=${env.BRANCH_NAME ?: 'main'}
                        """
                    }
                }
            }
        }

        stage('Quality Gate') {
            steps {
                // Blocks on the SonarQube webhook; fails the build if the gate
                // does not pass.
                timeout(time: 10, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        stage('Package') {
            steps {
                sh 'make build'
            }
            post {
                success {
                    archiveArtifacts artifacts: 'dist/*', fingerprint: true
                }
            }
        }

        stage('Docker Build') {
            when {
                expression { sh(script: 'command -v docker', returnStatus: true) == 0 }
            }
            steps {
                script {
                    def version = sh(
                        script: '"$VENV"/bin/python -c "import qa_mcp; print(qa_mcp.__version__)"',
                        returnStdout: true
                    ).trim()
                    sh "docker build -t qa-mcp:${version} -t qa-mcp:ci-${env.BUILD_NUMBER} ."
                    sh "docker run --rm qa-mcp:${version} --version"
                }
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: "${REPORTS}/**", allowEmptyArchive: true, fingerprint: false
        }
        cleanup {
            cleanWs(deleteDirs: true, notFailBuild: true)
        }
    }
}
