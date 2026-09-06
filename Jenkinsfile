pipeline {
    agent { label 'qa-docker' }
    options {
        timestamps()
        timeout(time: 25, unit: 'MINUTES')
        buildDiscarder(logRotator(daysToKeepStr: '30', artifactDaysToKeepStr: '30'))
    }
    stages {
        stage('Зависимости') {
            steps {
                script {
                    if (isUnix()) {
                        sh 'python3 -m pip install -r requirements-test.txt -c requirements-test.lock && python3 -m playwright install --with-deps chromium'
                    } else {
                        bat 'python -m pip install -r requirements-test.txt -c requirements-test.lock && python -m playwright install chromium'
                    }
                }
            }
        }
        stage('Проверка стенда') {
            steps {
                script {
                    if (isUnix()) { sh 'python3 ci/verify.py' } else { bat 'python ci/verify.py' }
                }
            }
        }
    }
    post {
        always {
            junit allowEmptyResults: true, testResults: 'artifacts/*/tests.xml'
            archiveArtifacts allowEmptyArchive: true, artifacts: 'artifacts/**'
        }
    }
}
