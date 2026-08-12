import os
import time
import json
import requests
from dotenv import load_dotenv

load_dotenv()

KIBANA_URL = os.getenv('KIBANA_URL', 'http://localhost:5601')
ELASTICSEARCH_URL = os.getenv('ELASTICSEARCH_URL', 'http://localhost:9200')
INDEX_NAME = os.getenv('ELASTICSEARCH_INDEX', 'palavras-discord')
HEADERS = {"kbn-xsrf": "true", "Content-Type": "application/json"}

def wait_for_data():
    print(f"Aguardando dados no indice '{INDEX_NAME}'...")
    for _ in range(60): # Tenta por ate 5 minutos
        try:
            r = requests.get(f"{ELASTICSEARCH_URL}/{INDEX_NAME}/_count", timeout=2)
            if r.status_code == 200 and r.json().get("count", 0) > 0:
                print("Dados detectados no Elasticsearch!")
                return True
        except requests.ConnectionError:
            pass
        time.sleep(5)
    return False

def setup_dashboard():
    # Index Pattern
    payload_ip = {"attributes": {"title": f"{INDEX_NAME}*"}}
    requests.post(
        f"{KIBANA_URL}/api/saved_objects/index-pattern/palavras-pattern?overwrite=true",
        headers=HEADERS, json=payload_ip
    )

    print("Aguardando sincronização de campos do Kibana...")
    time.sleep(10) 

    # Visualizacao
    vis_state = {
        "title": "Nuvem de Palavras", "type": "tagcloud",
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
            "kibanaSavedObjectMeta": {"searchSourceJSON": json.dumps({"index": "palavras-pattern", "query": {"query": "", "language": "kuery"}, "filter": []})}
        }
    }

    r = requests.post(
        f"{KIBANA_URL}/api/saved_objects/visualization/nuvem-auto?overwrite=true",
        headers=HEADERS, json=payload_vis
    )
    if r.status_code == 200:
        print("Visualização 'Nuvem de Palavras' criada com sucesso!")
    else:
        print(f"Erro ao criar visualizacao: {r.text}")

if __name__ == "__main__":
    if wait_for_data():
        setup_dashboard()
    else:
        print("Tempo limite excedido aguardando dados.")
