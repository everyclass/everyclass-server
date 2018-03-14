#!/usr/bin/env bash
#run redis

#run mongodb

#run celery
celery worker -A celery_worker.celery
