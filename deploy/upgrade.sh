#!/usr/bin/env bash
# Upgrade script for Admirable applications
#
# - Get latest source code
# - Build Docker image (use `--no-build` option to skip building)
# - Start new docker image, wait till it's up
# - Register the new container to Consul
# - Unregister old containers from Consul

# exit if any command fails
set -e

# Configurations goes here
APP_DOCKER_REPO="fr0der1c/everyclass-server"
APP_CONTAINER_BASENAME="everyclass"

# generate a unused port
function EPHEMERAL_PORT(){
    PORT_L=10086;
    PORT_U=2220; # the upper bound is 12306
    # the environment variable $RANDOM range from 0 to 32767
    while true; do
        PORT_M=$[$PORT_L + ($RANDOM % $PORT_U)];
        (echo "" >/dev/tcp/127.0.0.1/${PORT_M}) >/dev/null 2>&1
        if [ $? -ne 0 ]; then
            echo ${PORT_M};
            return 0;
        fi
    done
}


APP_PORT=$(EPHEMERAL_PORT)
APP_START_TIMEOUT=30
APP_URL=http://localhost:$(echo ${APP_PORT})


### Build and run image

# get latest source code and build Docker image
cd `dirname $0` # cd to deploy/
cd ../ # cd to project root (where Dockerfile exists)
if [ "$1" != "--rollback" ]
then
    git reset --hard
    git pull
else
    git reset --hard HEAD^1
fi
if [ "$1" != "--no-build" ]
then
    docker build -t ${APP_DOCKER_REPO} .
fi

# run Docker image
docker run -it --rm -d \
    --net=host \
    --name "${APP_CONTAINER_BASENAME}-$(git describe --tags)-$(date "+%m%d-%H%M")" \
    -v "$(pwd)/everyclass/server/config:/var/everyclass-server/everyclass/server/config" \
    -v "$(pwd)/calendar_files:/var/everyclass-server/calendar_files" \
    -p $(echo ${APP_PORT}):${APP_PORT} \
    -e UWSGI_HTTP_SOCKET=":${APP_PORT}" \
    ${APP_DOCKER_REPO}


### Roll-upgrade
LATEST_CONTAINER=$(docker ps -q --filter name=${APP_CONTAINER_BASENAME} -l)
ALL_CONTAINERS=$(docker ps -q --filter name=${APP_CONTAINER_BASENAME})

# wait 30 seconds, replace nginx upstream with new container, and stop old container.
counter=0
while [ ! "$(curl -k ${APP_URL} 2> /dev/null)" -a ${counter} -lt ${APP_START_TIMEOUT}  ]; do
    sleep 1
    ((counter++))
    echo "waiting for application to be up ($counter/$APP_START_TIMEOUT)"
done
if [ ! "$(curl -k ${APP_URL} 2> /dev/null)" ]; then
    echo "Couldn't start application. Exiting."
    exit 1
fi
echo "Application started."

# stop old containers (stop nothing if there are no old containers)
for each in ${ALL_CONTAINERS[@]}
do
    if [ "$each" != "$LATEST_CONTAINER" ]; then
        docker stop ${each}
    fi
done