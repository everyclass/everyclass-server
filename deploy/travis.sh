#!/bin/bash
# Travis auto deploy script

set -xe

eval "$(ssh-agent -s)"
chmod 600 /tmp/deploy_key
chmod 600 /tmp/stage_key
ssh-add /tmp/deploy_key
ssh-add /tmp/stage_key



if [ $TRAVIS_BRANCH = "master" ] ; then

git checkout master
VERSION=$(git describe --tags)
curl -sL https://sentry.io/get-cli/ | bash
sentry-cli releases new -p everyclass-server -p everyclass-server-staging --finalize "$VERSION"
sentry-cli releases set-commits "$VERSION" --auto

ssh -o StrictHostKeyChecking=no travis@every.admirable.one <<EOF
cd /var/EveryClass-server
git reset --hard
git pull
bash deploy/upgrade.sh
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