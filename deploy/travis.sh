#!/bin/bash
# Travis auto deploy script

set -xe

if [ $TRAVIS_BRANCH = "release" ] ; then

# checkout release first, otherwise `git describe` will be wrong
git checkout release
VERSION=$(git describe --tags)

# sentry release
curl -sL https://sentry.io/get-cli/ | bash
export SENTRY_ORG=admirable
export SENTRY_URL=https://sentry.admirable.pro/
sentry-cli releases new -p everyclass-server --finalize "$VERSION"
sentry-cli releases set-commits "$VERSION" --auto

# build Docker image and upload to hub
docker login --username ${DOCKER_USERNAME} ccr.ccs.tencentyun.com --password ${DOCKER_PASSWORD}
IMAGE_ADDRESS=ccr.ccs.tencentyun.com/everyclass/everyclass-server:${VERSION}
docker build -t ${IMAGE_ADDRESS}
docker push ${IMAGE_ADDRESS}

else

     echo "No deploy script for branch '$TRAVIS_BRANCH'. Skip deploying."

fi