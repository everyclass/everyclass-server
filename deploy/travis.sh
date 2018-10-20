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
echo ${DOCKER_PASSWORD} | docker login --username ${DOCKER_USERNAME} ccr.ccs.tencentyun.com --password-stdin
IMAGE_ADDRESS=ccr.ccs.tencentyun.com/everyclass/everyclass-server:${VERSION}
docker build -t ${IMAGE_ADDRESS} .
docker push ${IMAGE_ADDRESS}

sentry-cli releases deploys ${VERSION} new -e staging

else

     echo "No deploy script for branch '$TRAVIS_BRANCH'. Skip deploying."

fi