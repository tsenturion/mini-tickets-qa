// Агент с доступом к Docker работает на хосте; контроллеру Docker socket не требуется.
pipeline {
    agent { label 'qa-docker' }
    options {
        timestamps()
        timeout(time: 25, unit: 'MINUTES')
        buildDiscarder(logRotator(daysToKeepStr: '30', artifactDaysToKeepStr: '30'))
    }
    stages {
        stage('Изолированная подготовка и проверка') {
            steps {
                script {
                    if (isUnix()) {
                        sh 'python3 ci/bootstrap.py'
                    } else {
                        bat 'python ci/bootstrap.py'
                    }
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
