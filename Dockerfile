FROM python:3.7.1-slim-stretch
LABEL maintainer="frederic.t.chan@gmail.com"
ENV REFRESHED_AT 20181129
ENV MODE PRODUCTION
ENV FLASK_ENV production
ENV PIPENV_VENV_IN_PROJECT 1
# ENV LANG="en_US.UTF-8" LC_ALL="en_US.UTF-8"

WORKDIR /var/everyclass-server

# build uWSGI and Python plugin for current python version
# reference on how to build uwsgi python plugin: https://bradenmacdonald.com/blog/2015/uwsgi-emperor-multiple-python

# Why we need these packages?
# - git for using git in our app
# - make, gcc, libpcre3-dev for compiling uWSGI
# - libffi-dev for installing Python package cffi
# - libssl-dev for installing Python package cryptography
RUN apt-get update \
    && apt-get install -y wget git make gcc libpcre3-dev libffi-dev libssl-dev \
    && cd /usr/local/src \
    && wget http://projects.unbit.it/downloads/uwsgi-2.0.17.1.tar.gz \
    && tar zxf uwsgi-2.0.17.1.tar.gz \
    && cd uwsgi-2.0.17.1/ \
    && sed -i "s:plugin_dir = .:plugin_dir = /usr/local/lib/uwsgi/:g" buildconf/base.ini \
    && make PROFILE=nolang \
    && PYTHON=python3.7 ./uwsgi --build-plugin "plugins/python python37" \
    && mkdir /usr/local/lib/uwsgi/ \
    && cp python*_plugin.so /usr/local/lib/uwsgi/ \
    && cp uwsgi /usr/local/bin/uwsgi \
    && rm -rf /usr/local/src/uwsgi-2.0.17.1

# install gor
RUN cd / \
    && mkdir gor \
    && cd gor \
    && wget https://github.com/buger/goreplay/releases/download/v0.16.1/gor_0.16.1_x64.tar.gz \
    && tar xzf gor_0.16.1_x64.tar.gz \
    && rm gor_0.16.1_x64.tar.gz

COPY . /var/everyclass-server

# install Python dependencies
RUN pip3 install --upgrade pip \
    && pip3 install pipenv \
    && pipenv sync \
    && pip3 install uwsgitop \
    && rm -r /root/.cache

ENV UWSGI_HTTP_SOCKET ":80"

CMD ["sh", "deploy/docker-cmd.sh"]