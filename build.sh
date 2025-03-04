#!/bin/bash
set -e

# Configuration
IMAGE_NAME="seedshield"
VERSION=$(grep -o 'VERSION = "[0-9]*\.[0-9]*\.[0-9]*"' seedshield/config.py | grep -o '[0-9]*\.[0-9]*\.[0-9]*')

# Build the image
echo "Building Docker image ${IMAGE_NAME}:${VERSION}..."
docker build -t ${IMAGE_NAME}:${VERSION} .
docker tag ${IMAGE_NAME}:${VERSION} ${IMAGE_NAME}:latest

# Run basic tests
echo "Running basic tests..."
docker run --rm ${IMAGE_NAME}:${VERSION} --help

echo "Done! Image built successfully as ${IMAGE_NAME}:${VERSION} and ${IMAGE_NAME}:latest"