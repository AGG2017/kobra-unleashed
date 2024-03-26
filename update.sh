#!/bin/bash
echo "Updating..."
docker compose down
docker rmi kobra-unleashed
git pull origin master
docker build . -t kobra-unleashed --no-cache
docker compose up
echo "DONE!"
