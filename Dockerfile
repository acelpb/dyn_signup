FROM python:3.10-alpine
ENV PYTHONUNBUFFERED 1

RUN mkdir /app
WORKDIR /app

COPY ./ .
RUN pip install -r requirements.txt

CMD gunicorn dynasignup.wsgi:application --bind 0.0.0.0:9000
