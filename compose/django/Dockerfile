FROM python:3.10-slim

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

RUN apt-get update && apt-get install --no-install-recommends -y \
  # dependencies for building Python packages
  build-essential \
  # psycopg2 dependencies
  libpq-dev \
  git

COPY ./compose/django/requirements.txt requirements.txt
RUN pip install -r requirements.txt

WORKDIR /code

EXPOSE 8000
