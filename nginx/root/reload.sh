#!/bin/bash
envsubst '$SERVER_NAME' \
< /etc/nginx/conf.d/app.template \
> /etc/nginx/conf.d/app.conf
