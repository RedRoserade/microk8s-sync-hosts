#!/usr/bin/env bash

set -e

image=localhost:32000/microk8s-sync-hosts

docker build -t ${image} .
docker push ${image}
