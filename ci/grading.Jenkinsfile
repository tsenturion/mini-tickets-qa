// Этот файл берётся из доверенного SHA продукта, не из MR студента.
// Ожидаемые красные JUnit внутри мутантов не публикуются как итоговый статус Jenkins.
pipeline {
    agent { label 'qa-docker' }
    options {
        skipDefaultCheckout(true)
        disableConcurrentBuilds()
        timestamps()
        timeout(time: 90, unit: 'MINUTES')
        buildDiscarder(logRotator(daysToKeepStr: '30', artifactDaysToKeepStr: '30'))
    }
    environment { PYTHONUTF8 = '1' }
    parameters {
        string(name: 'SUBMISSION_URL', description: 'Git-адрес репозитория студента')
        string(name: 'SUBMISSION_SHA', description: 'Точный коммит исходной ветки PR/MR')
        string(name: 'SUBMISSION_CREDENTIALS_ID', defaultValue: '', description: 'ID Jenkins Credentials для чтения приватной работы; не сам пароль')
        booleanParam(name: 'FULL_MATRIX', defaultValue: false, description: 'Все дефекты на всех архитектурах')
    }
    stages {
        stage('Исходники') {
            steps {
                script {
                    // GitSCM читает окружение сборки, а не только environment/withEnv текущего шага.
                    // Продукт и работа используют свои Credentials без системного кеша Git.
                    env.GIT_CONFIG_PARAMETERS = "'credential.helper='"
                }
                dir('product') { checkout scm }
                dir('submission') {
                    checkout([$class: 'GitSCM', branches: [[name: params.SUBMISSION_SHA]], userRemoteConfigs: [[url: params.SUBMISSION_URL, credentialsId: params.SUBMISSION_CREDENTIALS_ID]]])
                }
            }
        }
        stage('Оценивание') {
            steps {
                dir('product') {
                    script {
                        def full = params.FULL_MATRIX ? ' --full' : ''
                        if (isUnix()) {
                            sh 'docker build -f grader/Dockerfile -t mini-tickets-grader:1.0 .'
                            sh 'python3 scripts/freeze_release.py'
                            sh "python3 grader/run.py --submission ../submission --refs artifacts/release-lock.json${full}"
                        } else {
                            bat encoding: 'UTF-8', script: '@chcp 65001 >nul\ndocker build -f grader/Dockerfile -t mini-tickets-grader:1.0 .'
                            bat encoding: 'UTF-8', script: '@chcp 65001 >nul\npython scripts/freeze_release.py'
                            bat encoding: 'UTF-8', script: "@chcp 65001 >nul\npython grader/run.py --submission ../submission --refs artifacts/release-lock.json${full}"
                        }
                    }
                }
            }
        }
    }
    post { always { archiveArtifacts allowEmptyArchive: true, artifacts: 'product/artifacts/**' } }
}
