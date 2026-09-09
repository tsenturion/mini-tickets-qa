// Агент с доступом к Docker работает на хосте; контроллеру Docker socket не требуется.
def prepareCheckout() {
    // Настройка относится только к checkout задания. GitSCM не наследует withEnv текущего шага.
    // Явный init не позволяет Git изменить настройки родительского репозитория на чистом стенде.
    if (isUnix()) {
        sh "git init .\ngit config --local credential.helper ''"
    } else {
        bat encoding: 'UTF-8', script: '@chcp 65001 >nul\ngit init . || exit /b 1\ngit config --local credential.helper ""'
    }
}

pipeline {
    agent { label 'qa-docker' }
    options {
        skipDefaultCheckout(true)
        disableConcurrentBuilds()
        timestamps()
        timeout(time: 25, unit: 'MINUTES')
        buildDiscarder(logRotator(daysToKeepStr: '30', artifactDaysToKeepStr: '30'))
    }
    environment { PYTHONUTF8 = '1' }
    stages {
        stage('Исходники') {
            steps {
                script {
                    prepareCheckout()
                }
                checkout scm
            }
        }
        stage('Изолированная подготовка и проверка') {
            steps {
                script {
                    if (isUnix()) {
                        sh 'python3 ci/bootstrap.py'
                    } else {
                        bat encoding: 'UTF-8', script: '@chcp 65001 >nul\npython ci/bootstrap.py'
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
