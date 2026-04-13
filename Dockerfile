FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir flask

EXPOSE 8000

CMD ["python", "doce_suspiro/app.py"]