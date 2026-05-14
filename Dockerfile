# Usa uma imagem oficial e enxuta do Python
FROM python:3.12-slim

# Impede a criação de arquivos .pyc e força o log direto no terminal (sem buffer)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instala o 'uv' copiando o binário oficial (forma mais rápida e leve)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Define o diretório de trabalho
WORKDIR /app

# Copia primeiro apenas o arquivo de dependências (otimização de cache do Docker)
COPY requirements.txt .

# Instala as dependências usando o uv diretamente no sistema do contêiner
RUN uv pip install --system --no-cache -r requirements.txt

# Copia o restante do código
COPY . .

# Expõe a porta que o FastAPI vai rodar
EXPOSE 8000

# Comando para rodar a aplicação em produção
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]