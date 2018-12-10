#!/usr/bin/env bash
CURRENT_VERSION=$(git describe --tag) docker-compose -f local-compose.yml up