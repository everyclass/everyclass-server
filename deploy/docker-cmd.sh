#!/usr/bin/env bash

# for debug use
# /gor/goreplay --input-raw :80  --output-stdout

if [ "$MODE"=="PRODUCTION" ]
then
    /gor/goreplay \
        --input-raw :80 \
        --output-http http://everyclass-server.staging \
        --output-http-elasticsearch https://${GOREPLAY_USER}:${GOREPLAY_PWD}@${GOREPLAY_ES}:443/gor-everyclass-server \
        --http-disallow-url /_healthCheck \
        > /gor/goreplay.log &
fi

uwsgi --ini "/var/everyclass-server/deploy/uwsgi.ini"