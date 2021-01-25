FROM python:3.8-buster

ENV PYTHONUNBUFFERED 1

RUN apt-get update \
&& apt-get install -y \
  curl build-essential sudo git \
&& rm -rf /var/lib/apt/lists/*

RUN pip install -U pip poetry~=1.1.4 --no-cache-dir && \
    poetry config virtualenvs.in-project true
