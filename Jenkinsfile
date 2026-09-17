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
        // Автоматический checkout отключён: сначала prepareCheckout создаёт
        // локальный Git-контекст и сбрасывает credential.helper, затем SCM
        // получает исходники без наследования credentials хоста.
        skipDefaultCheckout(true)
        // Один job использует общий workspace, .runtime/ci-venv и artifacts.
        // Сериализация исключает одновременное изменение этих каталогов двумя
        // сборками одного Pipeline.
        disableConcurrentBuilds()
        timestamps()
        // Timeout останавливает зависший Docker build/healthcheck, а discarder
        // независимо ограничивает срок жизни журналов и артефактов 30 днями.
        timeout(time: 25, unit: 'MINUTES')
        buildDiscarder(logRotator(daysToKeepStr: '30', artifactDaysToKeepStr: '30'))
    }
    // Одинаковая кодировка нужна прежде всего Windows-агенту: кириллица в
    // путях, JUnit и диагностике не должна зависеть от системной code page.
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
                    // Команды разделены по ОС, потому что shell, активация
                    // Python launcher и распространение exit code у sh и bat
                    // несовместимы. ci/bootstrap.py остаётся общей логикой.
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
            // Результаты публикуются и после отказа подготовки или тестов.
            // allowEmpty* допускает ранний сбой до создания XML/артефактов и
            // не заменяет исходный статус сборки ошибкой post-блока.
            junit allowEmptyResults: true, testResults: 'artifacts/*/tests.xml'
            archiveArtifacts allowEmptyArchive: true, artifacts: 'artifacts/**'
        }
    }
}
