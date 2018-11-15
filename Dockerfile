FROM alpine:3.8
LABEL maintainer="frederic.t.chan@gmail.com"
ENV REFRESHED_AT 20180801
ENV MODE PRODUCTION
ENV FLASK_ENV production
ENV PIPENV_VENV_IN_PROJECT 1
ENV LANG="en_US.UTF-8" LC_ALL="en_US.UTF-8" LC_CTYPE="en_US.UTF-8"

WORKDIR /var/everyclass-server

# 安装 uWSGI 本体和 Python 插件（语言相关的插件不在发行版的包管理器中）
# uwsgi-python3 依赖uwsgi、python3、musl
RUN apk add --no-cache git python3 uwsgi uwsgi-python3 \
    gcc musl-dev libffi-dev openssl-dev python3-dev

COPY . /var/everyclass-server

# install Python dependencies
RUN pip3 install --upgrade pip \
    && pip3 install pipenv \
    && pipenv sync \
    && rm -r /root/.cache

# install gor
RUN cd / \
    && mkdir gor \
    && cd gor \
    && wget https://github.com/buger/goreplay/releases/download/v0.16.1/gor_0.16.1_x64.tar.gz \
    && tar xzf gor_0.16.1_x64.tar.gz \
    && rm gor_0.16.1_x64.tar.gz

ENV UWSGI_HTTP_SOCKET ":80"

CMD ["sh", "deploy/docker-cmd.sh"]