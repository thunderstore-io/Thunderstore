import json
import os
import sys

LAUNCHFILE_LOCATION = "/var/run/thunderstore-launch.json"


def check_pidfile(pidfile):
    try:
        pid = int(open(pidfile, "r").read())
        os.kill(pid, 0)
        return 0
    except Exception:
        return 1


def check_status() -> int:
    if not os.path.exists(LAUNCHFILE_LOCATION):
        return 1
    try:
        with open(LAUNCHFILE_LOCATION, "r") as launch_file:
            launch_json = launch_file.read()
        environment = json.loads(launch_json)
    except Exception:
        return 1

    runmode = environment.get("RUN_MODE", None)
    if runmode == "gunicorn":
        pidfile = environment.get("GUNICORN_PIDFILE", None)
        if pidfile is None:
            return 1
        return check_pidfile(pidfile)
    elif runmode == "celeryworker" or runmode == "celerybeat":
        pidfile = environment.get("CELERY_PIDFILE", None)
        if pidfile is None:
            return 1
        return check_pidfile(pidfile)
    elif runmode == "django":
        return 0
    else:
        return 1


sys.exit(check_status())
