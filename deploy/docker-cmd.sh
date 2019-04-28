#!/usr/bin/env bash

# for debug use
# /gor/goreplay --input-raw :80  --output-stdout

if [[ "$MODE" == "PRODUCTION" ]]
then
    echo "Production mode. Start goreplay."
    /gor/goreplay \
        --input-raw :80 \
        --output-http http://everyclass-server.staging \
        --output-file /mnt/goreplay/$(hostname)-%Y-%m-%d.log.gz \
        --http-allow-method GET \
        --http-disallow-url /_healthCheck \
        > /gor/goreplay.log &
fi

exec uwsgi --ini "/var/app/deploy/uwsgi.ini"