#!/bin/bash
# Travis auto deploy script

set -xe

eval "$(ssh-agent -s)"
chmod 600 /tmp/deploy_key
chmod 600 /tmp/stage_key
ssh-add /tmp/deploy_key
ssh-add /tmp/stage_key



if [ $TRAVIS_BRANCH = "master" ] ; then

ssh -o StrictHostKeyChecking=no travis@every.admirable.one <<EOF
cd /var/EveryClass-server && \
    git reset --hard && \
    git pull && \
    docker build -t fr0der1c/everyclass-server . && \
    docker run -it --rm -d \
        --net=host \
        --name "everyclass-`git describe`" \
        -v "`pwd`/everyclass/config:/var/everyclass-server/config" \
        -v "`pwd`/calendar_files:/var/everyclass-server/calendar_files" \
        -e UWSGI_HTTP_SOCKET=":9000" \
        fr0der1c/everyclass-server && \
    wait 30s, replace nginx upstream with new container, and stop old container.
EOF

elif [ $TRAVIS_BRANCH = "develop" ] ; then

ssh -o StrictHostKeyChecking=no travis@stage.admirable.one <<EOF
cd /var/EveryClass-server
pip install pipenv
pipenv clean
pipenv install
git reset --hard
git pull
touch reload
EOF

else

     echo "No deploy script for branch '$TRAVIS_BRANCH'. Skip deploying."

fi