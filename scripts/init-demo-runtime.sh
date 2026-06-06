#!/usr/bin/env bash

set -e

echo "Starting SEZRA runtime..."

docker compose up -d
docker compose up -d spike-detector-service

echo "SEZRA runtime is ready."