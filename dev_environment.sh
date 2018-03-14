#!/usr/bin/env bash
#run mysql
echo 'You need to start MySQL manually if not already.'

#run redis
echo 'Starting Redis...'
brew services run redis

#run mongodb
echo 'Starting MongoDB...'
brew services run mongodb

#run celery
echo 'Starting Celery...'
celery worker -A celery_worker.celery
