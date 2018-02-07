#!/bin/bash
set -xe

eval "$(ssh-agent -s)"
chmod 600 /tmp/deploy_rsa
ssh-add /tmp/deploy_rsa



if [ $TRAVIS_BRANCH = "master" ] ; then

    ssh travis@admirable.one <<EOF
cd /home/pyweb/EveryClass-server
git pull
touch reload
EOF


else

     echo "No deploy script for branch '$TRAVIS_BRANCH'. Skip deploying."

fi