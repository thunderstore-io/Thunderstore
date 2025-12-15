#!/bin/sh
set -e

mkdir -p /etc/nginx/user-conf

WATCH_FILE="/etc/nginx/user-conf/new-thunderstore-localhost.conf"
POLL_INTERVAL_SECONDS="${NGINX_CONF_POLL_INTERVAL_SECONDS:-1}"

checksum_watch_file() {
	if [ -f "$WATCH_FILE" ]; then
		cksum "$WATCH_FILE" | awk '{print $1":"$2}'
	else
		echo "missing"
	fi
}

# Nginx `include` directives fail hard if a glob matches zero files.
# Create a no-op config so the base stack can start even when no UI containers
# have populated the shared config volume.
if ! ls /etc/nginx/user-conf/*.conf >/dev/null 2>&1; then
	printf '%s\n' '# intentionally empty' > "$WATCH_FILE"
fi

# Auto-reload when thunderstore-ui updates new-thunderstore-localhost.conf in the shared volume.
last_checksum="$(checksum_watch_file)"
(
	# The parent script runs with `set -e`, but this monitor runs in the background.
	# If it exits due to an unhandled error, nginx would keep running with no
	# visible indication that auto-reload stopped working. Disable `-e` here and
	# log unexpected exits/errors instead.
	set +e
	trap 'rc=$?; echo "nginx conf monitor: exiting (rc=$rc)" >&2' EXIT

	while true; do
		sleep "$POLL_INTERVAL_SECONDS"
		if [ $? -ne 0 ]; then
			echo "nginx conf monitor: sleep failed" >&2
			continue
		fi

		current_checksum="$(checksum_watch_file)"
		if [ $? -ne 0 ]; then
			echo "nginx conf monitor: failed to checksum $WATCH_FILE" >&2
			continue
		fi

		if [ "$current_checksum" != "$last_checksum" ]; then
			echo "Detected change in $WATCH_FILE; reloading nginx..."
			nginx -t >/dev/null 2>&1
			if [ $? -eq 0 ]; then
				nginx -s reload >/dev/null 2>&1
				if [ $? -ne 0 ]; then
					echo "Warning: nginx reload failed" >&2
				fi
			else
				echo "Warning: nginx config test failed; not reloading" >&2
				nginx -t 2>&1 || true
			fi
			last_checksum="$current_checksum"
		fi
	done
) &

nginx -g "daemon off;"
