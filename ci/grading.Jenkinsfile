// Этот файл берётся из доверенного SHA продукта, не из MR студента.
// Ожидаемые красные JUnit внутри мутантов не публикуются как итоговый статус Jenkins.
def prepareCheckout() {
    // Изолируем Credentials продукта и работы от системного кеша Git только в их checkout.
    // GitSCM читает настройки репозитория, но не withEnv текущего шага Pipeline.
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
                dir('product') {
                    script { prepareCheckout() }
                    checkout scm
                }
                dir('submission') {
                    script { prepareCheckout() }
                    checkout([$class: 'GitSCM', branches: [[name: params.SUBMISSION_SHA]], userRemoteConfigs: [[url: params.SUBMISSION_URL, credentialsId: params.SUBMISSION_CREDENTIALS_ID]]])
                }
            }
        }
        stage('Оценивание') {
            steps {
                dir('product') {
                    script {
                        def full = params.FULL_MATRIX ? ' --full' : ''
                        // Новый каталог для каждой сборки исключает выдачу старой оценки после отказа checkout.
                        def report = "artifacts/grading-${env.BUILD_NUMBER}"
                        if (isUnix()) {
                            sh 'docker build -f grader/Dockerfile -t mini-tickets-grader:1.0 .'
                            sh 'python3 scripts/freeze_release.py'
                            sh "python3 grader/run.py --submission ../submission --output ${report} --refs artifacts/release-lock.json${full}"
                        } else {
                            bat encoding: 'UTF-8', script: '@chcp 65001 >nul\ndocker build -f grader/Dockerfile -t mini-tickets-grader:1.0 .'
                            bat encoding: 'UTF-8', script: '@chcp 65001 >nul\npython scripts/freeze_release.py'
                            bat encoding: 'UTF-8', script: "@chcp 65001 >nul\npython grader/run.py --submission ../submission --output ${report} --refs artifacts/release-lock.json${full}"
                        }
                    }
                }
            }
        }
    }
    post {
        always {
            archiveArtifacts allowEmptyArchive: true, artifacts: "product/artifacts/grading-${env.BUILD_NUMBER}/**"
        }
    }
}
