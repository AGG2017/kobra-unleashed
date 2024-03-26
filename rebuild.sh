#!/bin/bash
echo "Rebuilding..."
docker compose down
docker rmi kobra-unleashed
docker build . -t kobra-unleashed --no-cache
docker compose up
echo "DONE!"
