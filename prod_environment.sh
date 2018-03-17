#!/usr/bin/env bash
#run mysql
echo 'You need to start MySQL manually if not already.'

#run redis
echo 'Starting Redis...'
service redis start

#run mongodb
echo 'Starting MongoDB...'
service mongod start

#run celery
#echo 'Starting Celery...'
#supervisorctl start everyclass_celery
