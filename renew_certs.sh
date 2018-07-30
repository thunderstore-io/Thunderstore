#!/bin/bash
docker run -it --rm --name certbot \
  -v nexus_certs:/etc/letsencrypt \
  -v nexus_logs:/var/log/letsencrypt \
  -v nexus_letsencrypt:/var/www/.well-known \
  quay.io/letsencrypt/letsencrypt -t certonly \
  --agree-tos --renew-by-default \
  --webroot -w /var/www \
  -d nexus.leaguesandbox.gg
