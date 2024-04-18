FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . ./

RUN pip install --no-cache-dir -r requirements.txt

CMD exec gunicorn --bind :8080 --workers 1 --threads 8 --timeout 0 app:app