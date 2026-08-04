# --- 1.1. Correcoes de Ambiente (CRITICO) ---
# Downgrade do Numpy para compatibilidade com versoes atuais da lib 'elasticsearch'
# e evitar conflitos com JAX/Tensorflow pre-instalados no Colab.
!pip install -q "numpy<2.0"

# --- 1.2. Instalacao de Dependencias do SO ---
# Java 8 eh pre-requisito para Spark e Kafka (Scala)
!apt-get update
!apt-get install openjdk-8-jdk-headless -qq > /dev/null

# --- 1.3. Instalacao de Bibliotecas Python ---
!pip install -q pyspark kafka-python findspark discord.py elasticsearch==7.10.1

print("Dependencias instaladas com sucesso.")

import os

# --- Versoes dos Softwares ---
SPARK_VERSION = "3.3.0"
HADOOP_VERSION = "3"
KAFKA_VERSION = "3.3.1"
SCALA_VERSION_KAFKA = "2.13"
ELK_VERSION = "7.10.2"

# --- Caminhos (Paths) ---
os.environ["JAVA_HOME"] = "/usr/lib/jvm/java-8-openjdk-amd64"
os.environ["SPARK_HOME"] = f"/content/spark-{SPARK_VERSION}-bin-hadoop{HADOOP_VERSION}"
KAFKA_HOME = f"/content/kafka_{SCALA_VERSION_KAFKA}-{KAFKA_VERSION}"
ES_HOME = f"/content/elasticsearch-{ELK_VERSION}"
KIBANA_HOME = f"/content/kibana-{ELK_VERSION}-linux-x86_64"

# --- Configuracoes de Rede ---
KAFKA_BOOTSTRAP = "localhost:9092"
TOPICO_ENTRADA = "topico-entrada"
TOPICO_SAIDA = "topico-saida"

print("Variaveis de ambiente definidas.")

import os
import time

# --- Funcoes Auxiliares de Instalacao Robusta ---
def install_component_robust(name, version, install_path, download_url, archive_name, extract_cmd=None):
    if os.path.exists(install_path):
        print(f" {name} instalado em '{install_path}'.")
        return

    print(f" Baixando {name} {version}...")
    if os.path.exists(archive_name): os.remove(archive_name)

    # Tenta download silencioso primeiro
    if os.system(f"wget -q {download_url}") != 0 or not os.path.exists(archive_name):
        print(f" Tentativa 1 falhou. Retentando {name} com verbose...")
        if os.system(f"wget --progress=bar:force {download_url}") != 0 or not os.path.exists(archive_name):
             print(f" FALHA CRITICA: Nao foi possivel baixar {name}.")
             return

    print(f" Extraindo {name}...")
    os.system(extract_cmd if extract_cmd else f"tar -xf {archive_name}")

    if os.path.exists(install_path): print(f"{name} instalado com sucesso.")
    else: print(f" FALHA CRITICA: Pasta {install_path} nao criada.")

# --- Instalacao dos Componentes ---
install_component_robust("Apache Spark", SPARK_VERSION, os.environ["SPARK_HOME"],
    f"https://archive.apache.org/dist/spark/spark-{SPARK_VERSION}/spark-{SPARK_VERSION}-bin-hadoop{HADOOP_VERSION}.tgz",
    f"spark-{SPARK_VERSION}-bin-hadoop{HADOOP_VERSION}.tgz")

install_component_robust("Apache Kafka", KAFKA_VERSION, KAFKA_HOME,
    f"https://archive.apache.org/dist/kafka/{KAFKA_VERSION}/kafka_{SCALA_VERSION_KAFKA}-{KAFKA_VERSION}.tgz",
    f"kafka_{SCALA_VERSION_KAFKA}-{KAFKA_VERSION}.tgz")

install_component_robust("ElasticSearch", ELK_VERSION, ES_HOME,
    f"https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-{ELK_VERSION}-linux-x86_64.tar.gz",
    f"elasticsearch-{ELK_VERSION}-linux-x86_64.tar.gz",
    extract_cmd=f"tar -xzf elasticsearch-{ELK_VERSION}-linux-x86_64.tar.gz && chown -R daemon:daemon {ES_HOME}")

install_component_robust("Kibana", ELK_VERSION, KIBANA_HOME,
    f"https://artifacts.elastic.co/downloads/kibana/kibana-{ELK_VERSION}-linux-x86_64.tar.gz",
    f"kibana-{ELK_VERSION}-linux-x86_64.tar.gz")

import time

print(" Iniciando servicos de infraestrutura...")

# 1. Zookeeper & Kafka
!nohup $KAFKA_HOME/bin/zookeeper-server-start.sh $KAFKA_HOME/config/zookeeper.properties > zookeeper.log 2>&1 &
time.sleep(5)
!nohup $KAFKA_HOME/bin/kafka-server-start.sh $KAFKA_HOME/config/server.properties > kafka.log 2>&1 &
time.sleep(10)

# 2. ElasticSearch & Kibana
os.environ['ES_JAVA_OPTS'] = "-Xms512m -Xmx512m"
!nohup sudo -u daemon $ES_HOME/bin/elasticsearch -E "discovery.type=single-node" -E "http.port=9200" > es.log 2>&1 &
!nohup $KIBANA_HOME/bin/kibana --allow-root -p 5601 > kibana.log 2>&1 &

print(" Servicos iniciados em background.")

!$KAFKA_HOME/bin/kafka-topics.sh --create --if-not-exists --topic $TOPICO_ENTRADA --bootstrap-server $KAFKA_BOOTSTRAP --replication-factor 1 --partitions 1
!$KAFKA_HOME/bin/kafka-topics.sh --create --if-not-exists --topic $TOPICO_SAIDA --bootstrap-server $KAFKA_BOOTSTRAP --replication-factor 1 --partitions 1

print("\n--- Topicos Ativos ---")
!$KAFKA_HOME/bin/kafka-topics.sh --list --bootstrap-server $KAFKA_BOOTSTRAP

from google.colab import userdata
import os

try:
    os.environ['DISCORD_TOKEN'] = userdata.get('DISCORD_TOKEN')
    print(" Token do Discord recuperado com sucesso.")
except:
    print(" ERRO: Adicione 'DISCORD_TOKEN' nos Secrets do Colab.")

%%writefile discord_producer.py
import discord
import asyncio
from kafka import KafkaProducer
import os

KAFKA_TOPIC = 'topico-entrada'
KAFKA_BOOTSTRAP = 'localhost:9092'
TOKEN = os.environ.get('DISCORD_TOKEN')

if not TOKEN: raise ValueError("Token nao encontrado")

producer = KafkaProducer(bootstrap_servers=[KAFKA_BOOTSTRAP], value_serializer=lambda v: str(v).encode('utf-8'))
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f' Bot {client.user} conectado! Enviando para: {KAFKA_TOPIC}')

@client.event
async def on_message(message):
    if message.author == client.user: return
    try:
        producer.send(KAFKA_TOPIC, value=message.content)
        # print(f" Enviado: {message.content}") # debug verbal
    except Exception as e:
        print(f" Erro de envio: {e}")

asyncio.run(client.start(TOKEN))

# Executa o bot em background
!nohup python discord_producer.py > bot_discord.log 2>&1 &
print(" Bot do Discord iniciado em background.")

import findspark
findspark.init()
from pyspark.sql import SparkSession
from pyspark.sql.functions import explode, split, col, to_json, struct

SCALA_VERSION_SPARK = "2.12"
OS_PACKAGES = f"org.apache.spark:spark-sql-kafka-0-10_{SCALA_VERSION_SPARK}:{SPARK_VERSION}"

print(f" Iniciando Spark com pacote Kafka: {OS_PACKAGES}")

spark = (
    SparkSession.builder
    .master("local[*]")
    .appName("PSPD-Lab-SparkStreaming")
    .config("spark.jars.packages", OS_PACKAGES)
    .config("spark.sql.shuffle.partitions", "4")
    .getOrCreate()
)
spark.sparkContext.setLogLevel("WARN")
print(" SparkSession inicializada.")

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

# 3. Escrita (Sink)
query = df_counts.select(to_json(struct("*")).alias("value")) \
    .writeStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP) \
    .option("topic", TOPICO_SAIDA) \
    .option("checkpointLocation", "/content/checkpoint_spark") \
    .outputMode("update") \
    .start()

print(f"Query de Streaming iniciada [ID: {query.id}]")

!npm install -g localtunnel > /dev/null 2>&1
!nohup lt --port 5601 > url_kibana.txt 2>&1 &
time.sleep(5)

%%writefile bridge_kafka_elastic.py
import json
from kafka import KafkaConsumer
from elasticsearch import Elasticsearch

es = Elasticsearch(['http://localhost:9200'])
consumer = KafkaConsumer(
    'topico-saida',
    bootstrap_servers='localhost:9092',
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    auto_offset_reset='earliest'
)
index_name = "palavras-discord"
if not es.indices.exists(index=index_name): es.indices.create(index=index_name, ignore=400)
print(f" Ponte iniciada. Indexando em '{index_name}'...")

for msg in consumer:
    doc = msg.value
    if 'palavra' in doc:
        # Usa a palavra como ID para fazer 'upsert' (atualizar contagem)
        es.index(index=index_name, id=doc['palavra'], body=doc)

!nohup python bridge_kafka_elastic.py > bridge.log 2>&1 &
print(" Ponte Kafka-Elastic iniciada em background.")

import requests
import time
import json

# Configuracoes
KIBANA_URL = "http://localhost:5601"
ES_URL = "http://localhost:9200"
HEADERS = {"kbn-xsrf": "true", "Content-Type": "application/json"}

def wait_for_data(index_name):
    print(f"⏳ Aguardando dados do Spark chegarem no indice '{index_name}'...")
    retries = 0
    while retries < 60: # Espera ate ~5 minutos
        try:
            r = requests.get(f"{ES_URL}/{index_name}/_count", timeout=2)
            if r.status_code == 200:
                count = r.json().get("count", 0)
                if count > 0:
                    print(f" Dados detectados no ElasticSearch! ({count} documentos)")
                    return True
        except:
            pass
        time.sleep(5)
        retries += 1
        if retries % 5 == 0: print(f"   ...ainda aguardando dados (tentativa {retries}/60)")
    print(" Tempo esgotado aguardando dados.")
    return False

def create_kibana_objects_robust():
    # 1. Criar Index Pattern
    payload_ip = {"attributes": {"title": "palavras-discord*"}}
    r_ip = requests.post(f"{KIBANA_URL}/api/saved_objects/index-pattern/palavras-pattern?overwrite=true", headers=HEADERS, json=payload_ip)
    if r_ip.status_code == 200:
        print(" Index Pattern 'palavras-discord*' criado/atualizado.")
    else:
        print(f" Aviso ao criar Index Pattern: {r_ip.text}")

    # 2. Espera para Sincronizacao de Campos
    # O Kibana precisa de um momento para escanear o ElasticSearch e descobrir os campos 'count' e 'palavra'
    print(" Aguardando 15s para o Kibana sincronizar os campos...")
    time.sleep(15)

    # 3. Criar Visualizacao (Tag Cloud)
    vis_state = {
        "title": "Nuvem (Auto)", "type": "tagcloud",
        "params": {"host": "elasticsearch", "type": "tagcloud", "orientation": "single", "minFontSize": 18, "maxFontSize": 72, "showLabel": True, "scale": "linear"},
        "aggs": [
            {"id": "1", "enabled": True, "type": "max", "schema": "metric", "params": {"field": "count"}},
            {"id": "2", "enabled": True, "type": "terms", "schema": "segment", "params": {"field": "palavra.keyword", "size": 50, "orderBy": "1"}}
        ]
    }
    payload_vis = {
        "attributes": {
            "title": "Nuvem de Palavras Discord",
            "visState": json.dumps(vis_state),
            "uiStateJSON": "{}",
            "description": "Criado automaticamente via API",
            "kibanaSavedObjectMeta": {"searchSourceJSON": json.dumps({"index": "palavras-pattern", "query": {"query": "", "language": "kuery"}, "filter": []})}
        }
    }

    r_vis = requests.post(f"{KIBANA_URL}/api/saved_objects/visualization/nuvem-auto?overwrite=true", headers=HEADERS, json=payload_vis)

    if r_vis.status_code == 200:
        print(" Visualizacao 'Nuvem de Palavras Discord' criada com sucesso!")
    else:
        print(f" Erro ao criar visualizacao: {r_vis.text}")
        print(" Tente rodar esta celula novamente apos alguns instantes.")

# --- Fluxo de Execução Principal ---
# 1. Aguarda o Kibana estar online
print("⏳ Testando conexao com Kibana...")
kibana_up = False
for _ in range(30):
    try:
        if requests.get(f"{KIBANA_URL}/api/status", timeout=1).status_code == 200:
            kibana_up = True
            break
    except:
        time.sleep(2)

if kibana_up:
    # 2. So prossegue se houver dados reais para garantir que os campos existem
    if wait_for_data("palavras-discord"):
        create_kibana_objects_robust()
        print("\n TUDO PRONTO! Acesse o Kibana pelo link abaixo e abra a visualizacao.")
else:
    print(" O Kibana nao parece estar online. Verifique os logs da celula de infraestrutura.")

print(" ACESSE O KIBANA NESTA URL:")
!cat url_kibana.txt
print(" Se o LocalTunnel pedir uma senha, use o IP abaixo:")
!curl -s ipv4.icanhazip.com

# Verifica os últimos logs dos principais serviços
print("--- LOG DO BOT DISCORD ---")
!tail -n 5 bot_discord.log
print("\n--- LOG DA PONTE ELASTIC ---")
!tail -n 5 bridge.log
print("\n--- STATUS DO ELASTICSEARCH ---")
!curl -s -X GET "localhost:9200/_cluster/health?pretty"
