#!/usr/bin/env bash
NETWORK_NAME="everyclass_net"

REDIS_CONTAINER_NAME="adm_redis"
EC_CONTAINER_NAME="adm_everyclass"

# ./docker.sh local start
function local_start(){
    # network
    if [ -z $(docker network ls -f name=everyclass_net -q) ]
    then
        echo "Network $NETWORK_NAME not found. I'll create one."
        docker network create ${NETWORK_NAME}
    fi
    NETWORK_ID=$(docker network inspect --format="{{.Id}}" ${NETWORK_NAME})

    function add_to_network(){
        # $1 container name
        if [ -z $(docker inspect --format='{{range .NetworkSettings.Networks}}{{println .NetworkID}}{{end}}' $1 | grep ${NETWORK_ID}) ]
        then
            echo "Container $1 not in network. Add to network."
            docker network connect ${NETWORK_NAME} $1 1> /dev/null
        else
            echo "Container $1 already in network."
        fi
    }

    function start_redis(){
        echo "Start Redis..."
        docker run -d \
          --name ${REDIS_CONTAINER_NAME} \
          redis 1> /dev/null
    }

    function start_everyclass(){
        echo "Start EveryClass..."
        docker run -d \
          -e MODE=DEVELOPMENT \
          -p 8003:80 \
          --name ${EC_CONTAINER_NAME} \
          -v "$(pwd)/everyclass/config:/var/everyclass-server/config" \
          fr0der1c/everyclass-server:0.2 1> /dev/null
    }

    function delete_if_exist(){
        # $1 container name
        if [ ! -z $(docker ps -a -f name=$1 -q) ]
        then
            echo "Container $1 exist. Delete it."
            docker rm --force $1 1> /dev/null
        fi
    }

    function start_container(){
        # $1 container name
        if [ -z $(docker ps -f name=$1 -q) ]
        then
            # container stopped or not exist
            delete_if_exist $1

            if [[ $1 =~ "redis" ]]
            then
                start_redis
            elif [[ $1 =~ "everyclass" ]]
            then
                start_everyclass
            fi
        else
            echo "Container $1 is running. Skip."
        fi
    }

    # MySQL

    # Redis
    start_container ${REDIS_CONTAINER_NAME}
    add_to_network ${REDIS_CONTAINER_NAME}

    # Celery

    # EveryClass
    start_container ${EC_CONTAINER_NAME}
    add_to_network ${EC_CONTAINER_NAME}
}

# ./docker.sh local stop
function local_stop(){
    echo "Stopping container ${REDIS_CONTAINER_NAME}..."
    docker stop ${REDIS_CONTAINER_NAME}

    echo "Stopping container ${EC_CONTAINER_NAME}..."
    docker stop ${EC_CONTAINER_NAME}
}

# ./docker.sh local/online start/stop
if [ "$1" == "local" ]
then
    if [ "$2" == "start" ]
    then
        local_start
    elif [ "$2" == "stop" ]
    then
        local_stop
    fi
elif [ "$1" == "online" ]
then
    echo "online: not implemented."
fi