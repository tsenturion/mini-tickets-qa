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
        // Checkout отключён, чтобы до первого сетевого обращения применить
        // локальные настройки Git из prepareCheckout(), а не довериться
        // состоянию переиспользуемого workspace агента.
        skipDefaultCheckout(true)
        // Grader использует фиксированный Docker-тег и общие ресурсы одного
        // агента. Два запуска этого job не должны одновременно пересобирать
        // образ или смешивать состояние workspace.
        disableConcurrentBuilds()
        timestamps()
        timeout(time: 90, unit: 'MINUTES')
        // Журналы могут содержать диагностические данные работы, поэтому срок
        // хранения сборок и артефактов ограничен теми же 30 днями, что и логи
        // приложения.
        buildDiscarder(logRotator(daysToKeepStr: '30', artifactDaysToKeepStr: '30'))
    }
    environment { PYTHONUTF8 = '1' }
    parameters {
        string(name: 'SUBMISSION_URL', description: 'Git-адрес репозитория студента')
        string(name: 'SUBMISSION_SHA', description: 'Точный коммит исходной ветки PR/MR')
        string(name: 'SUBMISSION_CREDENTIALS_ID', defaultValue: '', description: 'ID Jenkins Credentials для checkout работы; оставьте пустым, если они не требуются')
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
                    // Проверяется неизменяемый SHA, а не имя ветки: source-
                    // ветка PR/MR может получить новый commit уже после старта
                    // сборки. Credentials применяются только к этому checkout
                    // и не становятся доступом к доверенному продукту.
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
                        // Dockerfile, оценщик и release-lock всегда берутся из
                        // доверенного checkout product. Submission лишь
                        // передаётся runner как проверяемые тесты и не может
                        // заменить логику оценивания своим Dockerfile.
                        // Манифест превращается в lock точных ревизий шести
                        // вариантов: вся матрица одной сборки проверяет один
                        // воспроизводимый выпуск, а не движущиеся ветки.
                        // FULL_MATRIX расширяет дорогой mutant-прогон на три
                        // архитектуры; обычный режим сохраняет полный fixed-
                        // baseline, но ограничивает число мутаций.
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
            // Артефакты нужны прежде всего при падении, поэтому архивирование
            // выполняется независимо от результата stage. allowEmptyArchive
            // допускает ранний инфраструктурный отказ до создания каталога и
            // не маскирует исходный статус сборки новой ошибкой post-блока.
            archiveArtifacts allowEmptyArchive: true, artifacts: "product/artifacts/grading-${env.BUILD_NUMBER}/**"
        }
    }
}
