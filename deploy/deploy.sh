#!/usr/bin/env bash
ssh travis@admirable.one <<EOF
  cd /home/pyweb/EveryClass-server
  git pull
EOF