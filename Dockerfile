FROM alpine:3.7
MAINTAINER Frederic Chan "frederic.t.chan@gmail.com"
ENV REFRESHED_AT 20180801
ENV MODE PRODUCTION
ENV PYTHONPATH /var/everyclass-server

WORKDIR /var/everyclass-server

RUN apk add --no-cache \
    python3 \
    uwsgi \
    uwsgi-python3 \
    git \
    && python3 -m ensurepip \
    && rm -r /usr/lib/python*/ensurepip

#RUN pip3 install pipenv \
#    && pipenv install \
#    && rm -r /root/.cache

# expose HTTP port
EXPOSE 80

# Why "enable-threads":
# https://uwsgi-docs.readthedocs.io/en/latest/ThingsToKnow.html
# By default the Python plugin does not initialize the GIL. This means your app-generated threads will not run. If you
#  need threads, remember to enable them with enable-threads. Running uWSGI in multithreading mode (with the threads
# options) will automatically enable threading support. This “strange” default behaviour is for performance reasons,
# no shame in that.
CMD ["uwsgi", "--ini", "/var/everyclass-server/uwsgi.ini", "--enable-threads"]