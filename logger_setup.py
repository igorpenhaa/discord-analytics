import logging
import json
import sys
from datetime import datetime, timezone

class JSONFormatter(logging.Formatter):
	# formatador customizado para converter registros de log do Python em JSON.

	def format(self, record):
		log_record = {
				"timestamp": datetime.now(timezone.utc).isoformat(),
				"level": record.levelname,
				"logger": record.name,
				"message": record.getMessage(),
				"module": record.module,
				"function": record.funcName,
				"line": record.lineno
				}

		# Anexa o traceback da excecao caso exista (ex: logger.error("...", exc_info=True))
		if record.exc_info:
			log_record["exception"] = self.formatException(record.exc_info)

		return json.dumps(log_record)

def get_json_logger(name: str) -> logging.Logger:
	# Configura e retorna um logger padronizado para stdout.
	logger = logging.getLogger(name)

	# Evita adicionar multiplos handlers se a função for chamada mais de uma vez
	if not logger.handlers:
		logger.setLevel(logging.INFO)
		# O Kubernetes captura logs do stdout por padrao
		handler = logging.StreamHandler(sys.stdout)
		handler.setFormatter(JSONFormatter())
		logger.addHandler(handler)

	return logger
