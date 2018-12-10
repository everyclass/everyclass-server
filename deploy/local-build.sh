#!/usr/bin/env bash
docker build . -t everyclass-server:$(git describe --tag)