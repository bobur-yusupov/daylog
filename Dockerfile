FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        postgresql-client \
        libpq-dev \
        git \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt .

RUN python3 -m venv /.venv/ \
    && /.venv/bin/pip install --upgrade pip \
    && /.venv/bin/pip install --no-cache-dir -r /app/requirements.txt

ENV PATH="/.venv/bin:$PATH"

RUN adduser --disabled-password --gecos '' appuser \
    && chown -R appuser:appuser /app \
    && chown -R appuser:appuser /.venv

USER appuser

RUN python manage.py collectstatic --noinput

EXPOSE 8000

COPY ./app /app/
