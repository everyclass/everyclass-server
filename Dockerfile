FROM alpine:3.8
LABEL maintainer="frederic.t.chan@gmail.com"
ENV REFRESHED_AT 20180801
ENV MODE PRODUCTION
ENV PIPENV_VENV_IN_PROJECT 1
ENV LANG="en_US.UTF-8" LC_ALL="en_US.UTF-8" LC_CTYPE="en_US.UTF-8"

WORKDIR /var/everyclass-server

# 安装 uWSGI 本体和 Python 插件（语言相关的插件不在发行版的包管理器中）
# uwsgi-python3 依赖uwsgi、python3、musl
RUN apk add --no-cache git python3 uwsgi uwsgi-python3 \
    gcc musl-dev libffi-dev openssl-dev python3-dev

# 经测试，如果把本目录在运行时挂载，会导致找不到 build 时生成的虚拟环境，于是只能在这里先把代码加到镜像里
COPY . /var/everyclass-server

RUN pip3 install --upgrade pip \
    && pip3 install pipenv \
    && pipenv sync \
    && rm -r /root/.cache

ENV UWSGI_HTTP_SOCKET ":9000"

CMD ["uwsgi", "--ini", "/var/everyclass-server/deploy/uwsgi.ini"]