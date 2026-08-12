pipeline {
    // Permite que a pipeline rode no proprio servidor Jenkins
    agent any

    environment {
        DOCKER_CREDS = credentials('docker-hub-credentials')
        DOCKER_USER = "${DOCKER_CREDS_USR}"

        // Versionamento dinamico
        IMAGE_TAG = "v1.0.${BUILD_NUMBER}"
    }

    stages {
        stage('Checkout do Código') {
            steps {
                // Baixa a versao mais recente do seu repo do GitHub
                checkout scm
            }
        }

        stage('Construção (Build)') {
            steps {
                echo "Empacotando as aplicações Python e Spark..."
                sh "docker build -t ${DOCKER_USER}/discord-producer:${IMAGE_TAG} -f Dockerfile.app ."
                sh "docker build -t ${DOCKER_USER}/spark-processor:${IMAGE_TAG} -f Dockerfile.spark ."
                sh "docker build -t ${DOCKER_USER}/elastic-consumer:${IMAGE_TAG} -f Dockerfile.app ."
            }
        }

        stage('Autenticação de Segurança') {
            steps {
                echo "Acessando o cofre para login no Docker Hub..."
                sh "echo ${DOCKER_CREDS_PSW} | docker login -u ${DOCKER_CREDS_USR} --password-stdin"
            }
        }

        stage('Entrega (Push)') {
            steps {
                echo "Enviando os contêineres para a nuvem..."
                sh "docker push ${DOCKER_USER}/discord-producer:${IMAGE_TAG}"
                sh "docker push ${DOCKER_USER}/spark-processor:${IMAGE_TAG}"
                sh "docker push ${DOCKER_USER}/elastic-consumer:${IMAGE_TAG}"
            }
        }

        stage('Limpeza do Agente') {
            steps {
                echo "Removendo imagens locais..."
                sh "docker logout"
                sh "docker rmi ${DOCKER_USER}/discord-producer:${IMAGE_TAG}"
                sh "docker rmi ${DOCKER_USER}/spark-processor:${IMAGE_TAG}"
                sh "docker rmi ${DOCKER_USER}/elastic-consumer:${IMAGE_TAG}"
            }
        }
    }

    post {
        always {
            cleanWs() // Limpa o diretorio de trabalho do Jenkins
        }
        success {
            echo "Pipeline concluída com sucesso! Imagens atualizadas na tag ${IMAGE_TAG}."
        }
        failure {
            echo "Falha na esteira. Verifique os logs de compilação."
        }
    }
}
