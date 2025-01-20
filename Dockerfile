FROM python:3.10

WORKDIR /app

ENV DEBIAN_FRONTEND='noninteractive'

RUN apt-get update && apt install -y curl

RUN pip install poetry

ENV PATH="${PATH}:/root/.local/bin"

COPY ./pyproject.toml /app/pyproject.toml

COPY ./poetry.lock /app/poetry.lock

COPY ./README.md /app/README.md

RUN poetry install

COPY . /app

EXPOSE 8000

#Exposing port for celery flower
EXPOSE 5555
