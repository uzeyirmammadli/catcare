FROM python:3.10

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 5225

CMD [ "gunicorn", "--bind", "0.0.0.0:5225", "app:app" ]

