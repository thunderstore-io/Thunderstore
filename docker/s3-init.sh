#!/bin/sh
# Creates the local S3 buckets and allows anonymous downloads from them, like
# the public buckets in production. Safe to run on every start.
set -e

tries=0
until aws s3api list-buckets >/dev/null 2>&1; do
    tries=$((tries + 1))
    if [ "$tries" -ge 60 ]; then
        echo "S3 server at $AWS_ENDPOINT_URL did not become ready" >&2
        exit 1
    fi
    sleep 1
done

for bucket in thunderstore test; do
    aws s3api head-bucket --bucket "$bucket" 2>/dev/null \
        || aws s3api create-bucket --bucket "$bucket"
    aws s3api put-bucket-policy --bucket "$bucket" --policy "{
        \"Version\": \"2012-10-17\",
        \"Statement\": [{
            \"Effect\": \"Allow\",
            \"Principal\": {\"AWS\": [\"*\"]},
            \"Action\": [\"s3:GetObject\"],
            \"Resource\": [\"arn:aws:s3:::$bucket/*\"]
        }]
    }"
done

echo "Buckets ready: thunderstore, test"
