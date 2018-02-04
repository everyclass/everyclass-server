#!/usr/bin/env bash
echo 'Connecting to production server...'
ssh travis@admirable.one -o PubkeyAuthentication=no

echo 'cd to dir'
cd /home/pyweb/EveryClass-server

echo 'git pull'
git pull