#!/bin/bash

# Docker Hub username and password
DOCKER_USERNAME="***REMOVED***"
DOCKER_PASSWORD="***REMOVED***"

VERSION=$(cat version.txt)
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
IMAGE_NAME=$(basename "$(pwd)")
TAG="$VERSION-$CURRENT_BRANCH"


# Build the Docker image
docker build --platform linux/arm64 -t bitemap/$IMAGE_NAME-arm64:$TAG .
docker build --platform linux/amd64 -t bitemap/$IMAGE_NAME-x86_64:$TAG .

# Log in to Docker Hub
echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin

# Push the Docker image to Docker Hub
docker push bitemap/$IMAGE_NAME-arm64:$TAG
docker push bitemap/$IMAGE_NAME-x86_64:$TAG