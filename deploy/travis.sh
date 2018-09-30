#!/bin/bash
# Travis auto deploy script

set -xe

eval "$(ssh-agent -s)"
chmod 600 /tmp/deploy_key
chmod 600 /tmp/stage_key
ssh-add /tmp/deploy_key
ssh-add /tmp/stage_key



if [ $TRAVIS_BRANCH = "master" ] ; then

# checkout master first, otherwise `git describe will be wrong`
git checkout master
VERSION=$(git describe --tags)
curl -sL https://sentry.io/get-cli/ | bash
export SENTRY_ORG=admirable
export SENTRY_URL=https://sentry.admirable.pro/
sentry-cli releases new -p everyclass-server --finalize "$VERSION"
sentry-cli releases set-commits "$VERSION" --auto
DEPLOY_START_TIME=$(date +%s)

ssh -o StrictHostKeyChecking=no travis@every.admirable.one <<EOF
cd /var/EveryClass-server
echo "Reset git repository..."
git reset --hard
echo "Pulling latest code..."
git pull
bash deploy/upgrade.sh
EOF

DEPLOY_END_TIME=$(date +%s)
sentry-cli releases deploys ${VERSION} new -e production -t $((DEPLOY_END_TIME-DEPLOY_START_TIME))


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