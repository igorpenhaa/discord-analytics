import os
import discord
from confluent_kafka import Producer
from dotenv import load_dotenv
from logger_setup import get_json_logger

load_dotenv()

KAFKA_BOOTSTRAP = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC_IN', 'topico-entrada')
TOKEN = os.getenv('DISCORD_TOKEN')

logger = get_json_logger(__name__)

if not TOKEN:
	raise ValueError("Erro de Injeção: DISCORD_TOKEN não encontrado.")

class DiscordKafkaBot(discord.Client):
	def __init__(self, intents):
		super().__init__(intents=intents)
		# Configuracao do produtor com confluent-kafka
		conf = {'bootstrap.servers': KAFKA_BOOTSTRAP}
		self.producer = Producer(conf)

	async def close(self):
		logger.warning("Sinal de encerramento detectado. Drenando buffers do produtor Kafka...")
		self.producer.flush(10) # Aguarda ate 10 segundos para limpar a fila
		self.producer.close()
		logger.info("Conexao Kafka encerrada. Desconectando do Discord...")
		await super().close()

	async def on_ready(self):
		logger.info(f'Bot {self.user} online! Destino Kafka configurado: {KAFKA_TOPIC}')

	async def on_message(self, message):
		if message.author == self.user:
			return
		try:
			self.producer.produce(KAFKA_TOPIC, value=message.content.encode('utf-8'))
			self.producer.poll(0) # Aciona callbacks de entrega
			logger.info(f"Mensagem enfileirada: {message.content[:20]}...")
		except Exception as e:
			logger.error(f"Falha de I/O no Kafka: {e}")

if __name__ == "__main__":
	intents = discord.Intents.default()
	intents.messages = True
	intents.message_content = True

	client = DiscordKafkaBot(intents=intents)
	client.run(TOKEN)
