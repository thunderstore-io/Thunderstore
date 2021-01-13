import os
import sys

pidfile = os.environ.get("GUNICORN_PIDFILE", "/var/run/gunicorn.pid")

try:
    pid = int(open(pidfile, "r").read())
    os.kill(pid, 0)
    sys.exit(0)
except Exception:
    sys.exit(1)
