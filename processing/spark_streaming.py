import os
import sys
from dotenv import load_dotenv
from pyspark.sql import SparkSession
from pyspark.sql.functions import explode, split, col, to_json, struct
from logger_setup import get_json_logger

load_dotenv()
logger = get_json_logger(__name__)

KAFKA_BOOTSTRAP = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
TOPICO_ENTRADA = os.getenv('KAFKA_TOPIC_IN', 'topico-entrada')
TOPICO_SAIDA = os.getenv('KAFKA_TOPIC_OUT', 'topico-saida')
CHECKPOINT_DIR = os.getenv('SPARK_CHECKPOINT_DIR', '/tmp/spark-checkpoints')

OS_PACKAGES = "org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.0"

def main():
	logger.info("Iniciando SparkSession para DiscordWordCount...")

	try:
		spark = (
				SparkSession.builder
				.appName("DiscordWordCountStreaming")
				.config("spark.sql.shuffle.partitions", "4")
				.config("spark.jars.packages", OS_PACKAGES)
				.getOrCreate()
				)
		spark.sparkContext.setLogLevel("WARN")

		logger.info("Conectando ao Kafka (Source)...", extra={"topic": TOPICO_ENTRADA, "bootstrap": KAFKA_BOOTSTRAP})

		# 1. Leitura (Source)
		df_input = spark.readStream.format("kafka") \
				.option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP) \
				.option("subscribe", TOPICO_ENTRADA) \
				.option("startingOffsets", "latest") \
				.load()

		# 2. Transformacao (Process)
		df_counts = df_input.select(col("value").cast("string").alias("texto")) \
				.select(explode(split(col("texto"), " ")).alias("palavra")) \
				.filter(col("palavra") != "") \
				.groupBy("palavra").count()

		logger.info("Configurando Sink do Kafka...", extra={"topic": TOPICO_SAIDA, "checkpoint": CHECKPOINT_DIR})

		# 3. Escrita (Sink)
		query = df_counts.select(to_json(struct("*")).alias("value")) \
				.writeStream \
				.format("kafka") \
				.option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP) \
				.option("topic", TOPICO_SAIDA) \
				.option("checkpointLocation", CHECKPOINT_DIR) \
				.outputMode("update") \
				.start()

		logger.info("Query de Streaming iniciada com sucesso.", extra={"query_id": str(query.id)})

		# Mantem rodando continuamente
		query.awaitTermination()

	except Exception as e:
		logger.error("Falha na execução do Spark Streaming", exc_info=True)
		sys.exit(1)

if __name__ == "__main__":
	main()
