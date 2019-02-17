#!/usr/bin/env bash
CURRENT_VERSION=$(git describe --tag) docker-compose -f deploy/local-compose.yml up