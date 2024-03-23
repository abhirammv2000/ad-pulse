#!/bin/bash

# Read the version from the version.txt file and the current branch from Git and the current directory name
VERSION=$(cat version.txt)
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
CURRENT_DIR=$(basename "$(pwd)")
HOST_PORT=3000
CONTAINER_PORT=3000
ARCHITECTURE=$(uname -m)

echo "Architecture: $ARCHITECTURE"

echo "Current version is: $VERSION"
echo "Current Git branch is: $CURRENT_BRANCH"
echo "Current directory/reponame is: $CURRENT_DIR"

# Build Docker image and tag it with the version
docker build --build-arg VERSION="$VERSION-$CURRENT_BRANCH" -t $CURRENT_DIR-$ARCHITECTURE:"$VERSION" .

# Run the Docker container and port forward
docker run -p $HOST_PORT:$CONTAINER_PORT $CURRENT_DIR-$ARCHITECTURE:$VERSION