docker compose down
docker rmi kobra-unleashed
# edit main.py
docker build . -t kobra-unleashed --no-cache
docker compose up
