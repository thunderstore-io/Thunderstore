#!/bin/bash

cd /workspace/django
poetry run python /workspace/django/docker_entrypoint.py "$@"
