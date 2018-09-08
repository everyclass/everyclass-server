#!/usr/bin/env bash
# Upgrade script for EveryClass
#
# - Get latest source code
# - Build Docker image (use `--no-build` option to skip building)
# - Start new docker image, wait till it's up
# - Register the new container to Consul
# - Unregister old containers from Consul

# exit if any command fails
set -e

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


EVERYCLASS_PORT=$(EPHEMERAL_PORT)
EVERYCLASS_START_TIMEOUT=30
EVERYCLASS_URL=http://localhost:`echo ${EVERYCLASS_PORT}`


### Build and run image

# get latest source code and build Docker image
cd /var/EveryClass-server
git reset --hard
git pull
if [ "$1" != "--no-build" ]
then
    docker build -t fr0der1c/everyclass-server .
fi

# run Docker image
docker run -it --rm -d \
    --net=host \
    --name "everyclass-`git describe --tags`-`date "+%m%d-%H%M"`" \
    -v "`pwd`/everyclass/server/config:/var/everyclass-server/everyclass/server/config" \
    -v "`pwd`/calendar_files:/var/everyclass-server/calendar_files" \
    -p `echo ${EVERYCLASS_PORT}`:`echo ${EVERYCLASS_PORT}` \
    -e UWSGI_HTTP_SOCKET=":`echo ${EVERYCLASS_PORT}`" \
    fr0der1c/everyclass-server


### Roll-upgrade
LATEST_CONTAINER=`docker ps -q --filter name=everyclass -l`
ALL_CONTAINERS=`docker ps -q --filter name=everyclass`

# wait 30 seconds, replace nginx upstream with new container, and stop old container.
counter=0
while [ ! "$(curl -k ${EVERYCLASS_URL} 2> /dev/null)" -a ${counter} -lt EVERYCLASS_START_TIMEOUT  ]; do
    sleep 1
    ((counter++))
    echo "waiting for EveryClass to be up ($counter/$EVERYCLASS_START_TIMEOUT)"
done
if [ ! "$(curl -k ${EVERYCLASS_URL} 2> /dev/null)" ]; then
    echo "Couldn't start EveryClass. Exiting."
    exit 1
fi
echo "EveryClass started."

# stop old containers (stop nothing if there are no old containers)
for each in ${ALL_CONTAINERS[@]}
do
    if [ "$each" != "$LATEST_CONTAINER" ]; then
        docker stop ${each}
    fi
done