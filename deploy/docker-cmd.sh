#!/usr/bin/env bash

# for debug use
# /gor/goreplay --input-raw :80  --output-stdout

if [[ "$MODE"=="PRODUCTION" ]]
then
    /gor/goreplay \
        --input-raw :80 \
        --output-http http://everyclass-server.staging \
        --output-file /mnt/goreplay/$(hostname)-%Y-%m-%d.log.gz \
        --http-allow-method GET \
        --http-disallow-url /_healthCheck \
        > /gor/goreplay.log &
fi

uwsgi --ini "/var/everyclass-server/deploy/uwsgi.ini"