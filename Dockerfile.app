FROM python:3.9-slim

# evita a gravacao de arquivos .pyc e unbuffering do stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Criacao de um usuario de sistema nao-root
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

# Copia apenas o requirements primeiro para maximizar o uso do cache do Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do codigo da aplicacao
COPY . .

# Altera a propriedade dos arquivos para o novo usuario antes de alternar para ele
RUN chown -R appuser:appgroup /app
USER appuser

