FROM python:3.10

ARG BUILD_VERSION

LABEL name="telethondjangoproject" \
      version=$BUILD_VERSION

RUN mkdir -p /data/django/app
RUN mkdir /data/django/app/logs
RUN mkdir /data/django/app/sessions

WORKDIR /data/django/app

COPY requirements.txt /data/django/app
RUN python3 -m venv venv
RUN . venv/bin/activate && python3 -m pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
COPY . /data/django/app
