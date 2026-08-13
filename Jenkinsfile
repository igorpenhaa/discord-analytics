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

        stage('Atualização do Manifesto (GitOps)') {
            steps {
                echo "Atualizando a versão no repositório para a tag ${IMAGE_TAG}..."

                // Identidade do Jenkins no Git
                sh """
                    git config --global user.email "jenkins@lab.local"
                    git config --global user.name "Jenkins CI"
                """

                // 'sed' para procurar a tag velha e trocar pela nova
                sh """
                    sed -i "s|image: ${DOCKER_USER}/discord-producer:.*|image: ${DOCKER_USER}/discord-producer:${IMAGE_TAG}|g" k8s/apps-deployment.yaml
                    sed -i "s|image: ${DOCKER_USER}/spark-processor:.*|image: ${DOCKER_USER}/spark-processor:${IMAGE_TAG}|g" k8s/apps-deployment.yaml
                    sed -i "s|image: ${DOCKER_USER}/elastic-consumer:.*|image: ${DOCKER_USER}/elastic-consumer:${IMAGE_TAG}|g" k8s/apps-deployment.yaml
                """

                // Push da alteracao
                withCredentials([usernamePassword(credentialsId: 'github-credentials', passwordVariable: 'GIT_PASSWORD', usernameVariable: 'GIT_USERNAME')]) {
                    sh """
                        git add k8s/apps-deployment.yaml
                        git commit -m "ci: deploy automático da versão ${IMAGE_TAG} pelo Jenkins"
                        git push https://${GIT_USERNAME}:${GIT_PASSWORD}@github.com/igorpenhaa/discord-analytics.git HEAD:main
                    """
                }
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
