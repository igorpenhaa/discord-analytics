FROM python:3.9-slim

# evita a gravacao de arquivos .pyc e unbuffering do stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Altera a propriedade dos arquivos para o novo usuario antes de alternar para ele
RUN chown -R appuser:appgroup /app
USER appuser

