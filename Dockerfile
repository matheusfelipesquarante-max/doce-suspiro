FROM python:3.11

WORKDIR /app

COPY . .

# Dependência do sistema (SQLite)
RUN apt-get update && apt-get install -y sqlite3

# Instalar dependências do projeto
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

CMD ["python", "doce_suspiro/app.py"]
