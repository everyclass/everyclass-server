#!/bin/bash
set -xe

eval "$(ssh-agent -s)"
chmod 600 /tmp/deploy_key
chmod 600 /tmp/stage_key
ssh-add /tmp/deploy_key
ssh-add /tmp/stage_key



if [ $TRAVIS_BRANCH = "master" ] ; then

ssh -o StrictHostKeyChecking=no travis@every.admirable.one <<EOF
cd /var/EveryClass-server
pip install pipenv
pipenv clean
pipenv install
git reset --hard
git pull
touch reload
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