FROM python:3.7.1-slim-stretch
LABEL maintainer="frederic.t.chan@gmail.com"
ENV REFRESHED_AT 20181129
ENV MODE PRODUCTION
ENV FLASK_ENV production
ENV PIPENV_VENV_IN_PROJECT 1
# ENV LANG="en_US.UTF-8" LC_ALL="en_US.UTF-8"

WORKDIR /var/app

# build uWSGI and Python plugin for current python version
# reference on how to build uwsgi python plugin: https://bradenmacdonald.com/blog/2015/uwsgi-emperor-multiple-python

# Why we need these packages?
# - procps contains useful proccess control commands like: free, kill, pkill, ps, top
# - wget is quite basic tool
# - git for using git in our app
# - gcc, libpcre3-dev for compiling uWSGI
# - libffi-dev for installing Python package cffi
# - libssl-dev for installing Python package cryptography
# - vim for online debugging
RUN apt-get update \
    && apt-get install -y --no-install-recommends procps wget gcc libpcre3-dev git libffi-dev libssl-dev vim \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && pip install uwsgi

# install gor
RUN cd / \
    && mkdir gor \
    && cd gor \
    && wget https://github.com/buger/goreplay/releases/download/v0.16.1/gor_0.16.1_x64.tar.gz \
    && tar xzf gor_0.16.1_x64.tar.gz \
    && rm gor_0.16.1_x64.tar.gz

COPY . /var/app

# install Python dependencies, make entrypoint executable
RUN pip3 install --upgrade pip \
    && pip3 install pipenv \
    && pipenv sync \
    && pip3 install uwsgitop \
    && rm -r /root/.cache \
    && chmod +x ./deploy/docker-cmd.sh

ENV UWSGI_HTTP_SOCKET ":80"

CMD ["deploy/docker-cmd.sh"]