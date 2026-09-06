pipeline {
    agent { label 'qa-docker' }
    options {
        skipDefaultCheckout(true)
        timestamps()
        timeout(time: 90, unit: 'MINUTES')
        buildDiscarder(logRotator(daysToKeepStr: '30', artifactDaysToKeepStr: '30'))
    }
    parameters {
        string(name: 'SUBMISSION_URL', description: 'Git-адрес репозитория студента')
        string(name: 'SUBMISSION_SHA', description: 'Точный коммит исходной ветки PR/MR')
        booleanParam(name: 'FULL_MATRIX', defaultValue: false, description: 'Все дефекты на всех архитектурах')
    }
    stages {
        stage('Исходники') {
            steps {
                dir('product') { checkout scm }
                dir('submission') {
                    checkout([$class: 'GitSCM', branches: [[name: params.SUBMISSION_SHA]], userRemoteConfigs: [[url: params.SUBMISSION_URL]]])
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
                            bat 'docker build -f grader/Dockerfile -t mini-tickets-grader:1.0 .'
                            bat 'python scripts/freeze_release.py'
                            bat "python grader/run.py --submission ../submission --refs artifacts/release-lock.json${full}"
                        }
                    }
                }
            }
        }
    }
    post { always { archiveArtifacts allowEmptyArchive: true, artifacts: 'product/artifacts/**' } }
}
