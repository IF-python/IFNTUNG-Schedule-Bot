FROM python:3.6-slim

ENV PYTHONUNBUFFERED 1

ADD ./ /app/
WORKDIR /app

RUN python -m pip install -r requirements.txt
