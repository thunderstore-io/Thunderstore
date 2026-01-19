#!/bin/sh
sh /usr/bin/docker-entrypoint.sh "$@" &
MINIO_PID=$!
while ! nc -z minio 9000; do echo 'Wait minio to startup...' && sleep 0.1; done;
sleep 2
mc alias set thunderstore http://127.0.0.1:9000 $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD;
mc mb thunderstore/thunderstore;
mc mb thunderstore/test;
mc anonymous set download thunderstore/thunderstore;
mc anonymous set download thunderstore/test;
kill $MINIO_PID
wait $MINIO_PID
source /usr/bin/docker-entrypoint.sh "$@"
