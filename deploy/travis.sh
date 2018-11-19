#!/bin/bash
# Travis auto deploy script

set -xe

if [[ -z ${TRAVIS_TAG+x} ]]; then
    echo "TRAVIS_TAG is unset. Skip deploying.";
else
    echo "TRAVIS_TAG is set to '$TRAVIS_TAG'. Start deploying.";
    # checkout release first, otherwise `git describe` will be wrong
    git checkout $TRAVIS_TAG
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


    if [[ "$VERSION" == *_testing ]];then
        sentry-cli releases deploys ${VERSION} new -e testing
    else
        sentry-cli releases deploys ${VERSION} new -e staging
    fi
fi
