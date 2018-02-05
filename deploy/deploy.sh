#!/usr/bin/env bash
set -xe

eval "$(ssh-agent -s)"
chmod 600 /tmp/deploy_rsa
ssh-add /tmp/deploy_rsa

ssh travis@admirable.one <<EOF
  cd /home/pyweb/EveryClass-server
  git pull
EOF