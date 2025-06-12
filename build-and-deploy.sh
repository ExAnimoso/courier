#!/bin/sh

docker build -t raincord/courier .
docker compose up -d bot
