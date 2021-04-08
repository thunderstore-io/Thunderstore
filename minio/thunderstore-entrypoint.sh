#!/bin/sh
sh /usr/bin/docker-entrypoint.sh "$@" &
MINIO_PID=$!
while ! nc -z minio 9000; do echo 'Wait minio to startup...' && sleep 0.1; done;
mc config host add thunderstore http://127.0.0.1:9000 $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD;
mc mb thunderstore/thunderstore;
mc policy set download thunderstore/thunderstore;
kill $MINIO_PID
wait $MINIO_PID
source /usr/bin/docker-entrypoint.sh "$@"
