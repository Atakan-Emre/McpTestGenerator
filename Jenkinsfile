// QA-MCP Jenkins pipeline.
//
// Every stage delegates to a Makefile target, so a failing build can be
// reproduced locally with the same command (`make lint`, `make test`, ...).
//
// Nothing here is hardcoded to one organisation. Every name a company has to
// own - the SonarQube server, the scanner tool, credential ids, the registry -
// is a build parameter with a sensible default, so a team can run this pipeline
// by filling in its own values rather than editing the file.
//
// Required Jenkins plugins:
//   - Pipeline, Pipeline: Stage View
//   - JUnit
//   - SonarQube Scanner for Jenkins   (withSonarQubeEnv / waitForQualityGate)
//   - HTML Publisher                  (coverage report)
//   - Workspace Cleanup
//   - Credentials Binding             (only if PUBLISH_IMAGE is used)
//
// Required Jenkins configuration:
//   - A SonarQube server whose name matches the SONARQUBE_ENV parameter
//     (Manage Jenkins -> System -> SonarQube servers)
//   - A SonarScanner installation whose name matches SONAR_SCANNER_TOOL
//     (Manage Jenkins -> Tools -> SonarQube Scanner installations)
//   - A webhook in SonarQube pointing at <jenkins-url>/sonarqube-webhook/,
//     otherwise the Quality Gate stage blocks until its timeout
//
// See docs/CI-CD.md for the full setup, including how to run the same analysis
// locally against a disposable SonarQube.

pipeline {
    agent any

    options {
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '30', artifactNumToKeepStr: '10'))
        disableConcurrentBuilds()
        skipDefaultCheckout(false)
    }

    parameters {
        string(
            name: 'SONARQUBE_ENV',
            defaultValue: 'SonarQube',
            description: 'Name of the SonarQube server configured in Manage Jenkins -> System.'
        )
        string(
            name: 'SONAR_SCANNER_TOOL',
            defaultValue: 'SonarScanner',
            description: 'Name of the SonarScanner installation in Manage Jenkins -> Tools.'
        )
        string(
            name: 'SONAR_PROJECT_KEY',
            defaultValue: 'qa-mcp',
            description: 'Overrides sonar.projectKey, for organisations that namespace their projects.'
        )
        string(
            name: 'PYTHON',
            defaultValue: 'python3.11',
            description: 'Interpreter used to build the virtualenv on the agent.'
        )
        booleanParam(
            name: 'RUN_SONAR',
            defaultValue: true,
            description: 'Run SonarQube analysis and wait for the quality gate.'
        )
        booleanParam(
            name: 'PUBLISH_IMAGE',
            defaultValue: false,
            description: 'Push the Docker image to DOCKER_REGISTRY after a successful build.'
        )
        string(
            name: 'DOCKER_REGISTRY',
            defaultValue: '',
            description: 'Registry host for the published image, e.g. registry.acme.com. Empty means local only.'
        )
        string(
            name: 'DOCKER_CREDENTIALS_ID',
            defaultValue: 'docker-registry',
            description: 'Jenkins credentials id used to authenticate to DOCKER_REGISTRY.'
        )
        string(
            name: 'QUALITY_GATE_TIMEOUT_MINUTES',
            defaultValue: '10',
            description: 'How long to wait for the SonarQube quality gate.'
        )
    }

    environment {
        VENV = '.venv'
        REPORTS = 'reports'

        // Keep pip quiet and reproducible on agents.
        PIP_DISABLE_PIP_VERSION_CHECK = '1'
        PYTHONDONTWRITEBYTECODE = '1'
    }

    stages {

        stage('Environment') {
            steps {
                sh """
                    set -eu
                    ${params.PYTHON} --version
                    make install-ci PYTHON=${params.PYTHON} VENV=\$VENV
                    \$VENV/bin/qa-mcp --version
                    \$VENV/bin/qa-mcp --check-config
                """
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
            when { expression { params.RUN_SONAR } }
            steps {
                script {
                    def scannerHome = tool name: params.SONAR_SCANNER_TOOL, type: 'hudson.plugins.sonar.SonarRunnerInstallation'
                    def projectVersion = sh(
                        script: '"$VENV"/bin/python -c "import qa_mcp; print(qa_mcp.__version__)"',
                        returnStdout: true
                    ).trim()

                    withSonarQubeEnv(params.SONARQUBE_ENV) {
                        sh """
                            ${scannerHome}/bin/sonar-scanner \
                              -Dsonar.projectKey=${params.SONAR_PROJECT_KEY} \
                              -Dsonar.projectVersion=${projectVersion} \
                              -Dsonar.branch.name=${env.BRANCH_NAME ?: 'main'}
                        """
                    }
                }
            }
        }

        stage('Quality Gate') {
            when { expression { params.RUN_SONAR } }
            steps {
                // Blocks on the SonarQube webhook; fails the build if the gate
                // does not pass.
                timeout(time: params.QUALITY_GATE_TIMEOUT_MINUTES.toInteger(), unit: 'MINUTES') {
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
                    def prefix = params.DOCKER_REGISTRY ? "${params.DOCKER_REGISTRY}/" : ''
                    def image = "${prefix}qa-mcp"

                    sh "docker build -t ${image}:${version} -t ${image}:ci-${env.BUILD_NUMBER} ."
                    // The image must at least start and report its own version.
                    sh "docker run --rm ${image}:${version} --version"

                    if (params.PUBLISH_IMAGE) {
                        if (!params.DOCKER_REGISTRY) {
                            error 'PUBLISH_IMAGE is set but DOCKER_REGISTRY is empty.'
                        }
                        docker.withRegistry("https://${params.DOCKER_REGISTRY}", params.DOCKER_CREDENTIALS_ID) {
                            sh "docker push ${image}:${version}"
                        }
                    }
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
