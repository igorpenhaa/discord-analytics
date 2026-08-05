import os
import json
import signal
import sys
from dotenv import load_dotenv
from confluent_kafka import Consumer, KafkaError
from elasticsearch import Elasticsearch
from logger_setup import get_json_logger

load_dotenv()

# config de ambiente
KAFKA_BOOTSTRAP = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
TOPICO_SAIDA = os.getenv('KAFKA_TOPIC_OUT', 'topico-saida')
ELASTICSEARCH_URL = os.getenv('ELASTICSEARCH_URL', 'http://elasticsearch:9200')
INDEX_NAME = os.getenv('ELASTICSEARCH_INDEX', 'palavras-discord')

logger = get_json_logger(__name__)
# flag de controle de estado
is_running = True

def handle_sigterm(signum, frame):
	# intercepta o sinal SIGTERM e sinaliza para a thread principal parar
	global is_running
	logger.warning("Sinal de interrupcao recebido. Iniciando shutdown...", extra={"signum": signum})
	is_running = False

def main():
	signal.signal(signal.SIGTERM, handle_sigterm)
	signal.signal(signal.SIGINT, handle_sigterm)

	es = Elasticsearch([ELASTICSEARCH_URL])

	# Configuração do Consumidor confluent-kafka
	conf = {
			'bootstrap.servers': KAFKA_BOOTSTRAP,
			'group.id': 'elastic_bridge_group',
			'auto.offset.reset': 'earliest'
			}
	consumer = Consumer(conf)
	consumer.subscribe([TOPICO_SAIDA])

	if not es.indices.exists(index=INDEX_NAME):
		es.indices.create(index=INDEX_NAME, ignore=400)
		logger.info("Índice criado no Elasticsearch.", extra={"index": INDEX_NAME})

	logger.info("Ponte Kafka-Elastic iniciada.", extra={"topic": TOPICO_SAIDA})

	try:
		while is_running:
			# Le uma mensagem por vez com timeout de 1 segundo
			msg = consumer.poll(1.0)

			if msg is None:
				continue
			if msg.error():
				if msg.error().code() == KafkaError._PARTITION_EOF:
					# Fim da partição (comportamento normal)
					continue
				else:
					logger.error("Erro na leitura da mensagem", extra={"error": msg.error().str()})
					continue

			# Decodifica e indexa a mensagem
			try:
				doc = json.loads(msg.value().decode('utf-8'))
				if 'palavra' in doc:
					es.index(index=INDEX_NAME, id=doc['palavra'], body=doc)
					logger.info("Palavra indexada", extra={"palavra": doc['palavra'], "count": doc['count']})
			except json.JSONDecodeError:
				logger.error("Falha ao decodificar JSON", extra={"payload": msg.value()})

	except Exception as e:
		logger.error("Falha critica no processamento da ponte", exc_info=True)
	finally:
		logger.info("Fechando conexao com o broker Kafka...")
		consumer.close()
		logger.info("Shutdown concluido.")
		sys.exit(0)

if __name__ == "__main__":
	main()
