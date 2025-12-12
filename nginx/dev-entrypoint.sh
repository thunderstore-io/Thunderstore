#!/bin/sh
set -e

mkdir -p /etc/nginx/user-conf

# Nginx `include` directives fail hard if a glob matches zero files.
# Create a no-op config so the base stack can start even when no UI containers
# have populated the shared config volume.
if ! ls /etc/nginx/user-conf/*.conf >/dev/null 2>&1; then
	printf '%s\n' '# intentionally empty' > /etc/nginx/user-conf/00-empty.conf
fi
nginx -g "daemon off;"
