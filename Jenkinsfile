// Агент с доступом к Docker работает на хосте; контроллеру Docker socket не требуется.
pipeline {
    agent { label 'qa-docker' }
    options {
        skipDefaultCheckout(true)
        disableConcurrentBuilds()
        timestamps()
        timeout(time: 25, unit: 'MINUTES')
        buildDiscarder(logRotator(daysToKeepStr: '30', artifactDaysToKeepStr: '30'))
    }
    environment {
        PYTHONUTF8 = '1'
        // Используем Credentials задания, не сохранённый на компьютере пароль другого проекта.
        // Одна непустая переменная: Windows/Jenkins могут удалить пустое GIT_CONFIG_VALUE_0.
        GIT_CONFIG_PARAMETERS = "'credential.helper='"
    }
    stages {
        stage('Исходники') {
            steps { checkout scm }
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
