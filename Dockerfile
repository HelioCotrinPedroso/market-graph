# Terminal Macro do Ecossistema — imagem única que constrói o graph.json e serve o frontend.
FROM python:3.12-slim

WORKDIR /app

# Dependências do pipeline (para os fetchers de API funcionarem dentro do container também).
# O build/serve offline não precisa disto, mas instalar deixa a imagem completa.
COPY pipeline/requirements.txt pipeline/requirements.txt
RUN pip install --no-cache-dir -r pipeline/requirements.txt

# Código
COPY . .

# Não abrir navegador dentro do container
ENV MG_NO_OPEN=1

EXPOSE 8000

# serve.py reconstrói web/data/graph.json (offline, stdlib) e serve em 0.0.0.0:8000
CMD ["python", "serve.py", "--no-open", "--port", "8000"]
