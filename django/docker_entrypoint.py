import json
import os
import subprocess
import sys
from distutils.util import strtobool
from typing import List, Union


class EnvironmentVariable:
    def __init__(self, cast, name, default):
        self.cast = cast
        self.name = name
        self.default = default

    @property
    def value(self):
        val = os.environ.get(self.name, self.default)
        if self.cast is not None and val is not None and isinstance(val, str):
            val = self.cast(val)
        return val

    @value.setter
    def value(self, val):
        if val is None:
            del os.environ[self.name]
        else:
            os.environ[self.name] = str(val)

    def __str__(self):
        if self.value is None:
            return ""
        return str(self.value)

    def __bool__(self):
        return bool(self.value)


VARIABLES = {}


def run_command(command: Union[List[Union[EnvironmentVariable, str]], str]) -> int:
    environment = {
        **os.environ,
        **({k: str(v) for k, v in VARIABLES.items() if v is not None}),
    }
    if isinstance(command, str):
        command = command.split(" ")
    else:
        command = [str(x) for x in command]
    print(" ".join(command))
    result = subprocess.call(command, env=environment)
    if result != 0:
        sys.exit(result)
    return result


def register_variable(cast, name, default):
    var = EnvironmentVariable(cast, name, default)
    VARIABLES[name] = var
    return var


def to_bool(val) -> bool:
    if not val:
        return False
    return bool(strtobool(val))


SERVER_PORT = register_variable(int, "PORT", 8000)
SERVER_HOST = register_variable(str, "HOST", "0.0.0.0")

RUN_MODE = register_variable(str, "RUN_MODE", "gunicorn")
RUN_MIGRATIONS = register_variable(to_bool, "RUN_MIGRATIONS", True)
AUTORELOAD = register_variable(str, "AUTORELOAD", False)

GUNICORN_WORKER_CLASS = register_variable(str, "GUNICORN_WORKER_CLASS", "gevent")
GUNICORN_WORKER_COUNT = register_variable(int, "GUNICORN_WORKER_COUNT", 2)
GUNICORN_LOG_LEVEL = register_variable(str, "GUNICORN_LOG_LEVEL", "info")
GUNICORN_MAX_REQUESTS = register_variable(int, "GUNICORN_MAX_REQUESTS", 10000)
GUNICORN_MAX_REQUESTS_JITTER = register_variable(
    int, "GUNICORN_MAX_REQUESTS_JITTER", 1000
)
GUNICORN_PIDFILE = register_variable(str, "GUNICORN_PIDFILE", "/var/run/gunicorn.pid")

CELERY_PIDFILE = register_variable(str, "CELERY_PIDFILE", "/var/run/celery.pid")
CELERY_LOG_LEVEL = register_variable(str, "CELERY_LOG_LEVEL", "INFO")
CELERY_CONCURRENCY = register_variable(None, "CELERY_CONCURRENCY", None)
CELERY_POOL = register_variable(None, "CELERY_POOL", None)


WATCHMEDO_COMMAND = [
    "watchmedo",
    "auto-restart",
    '--patterns="*.py"',
    "--ignore-directories",
    "--recursive",
    "-d",
    "./",
    "--",
]


def run_django() -> None:
    print("Launching Django development server")
    command = ["python", "manage.py", "runserver", f"{SERVER_HOST}:{SERVER_PORT}"]
    if not AUTORELOAD:
        command += ["--noreload"]
    run_command(command)


def run_gunicorn() -> None:
    print("Launching gunicorn production server")
    command = [
        "gunicorn",
        "thunderstore.core.wsgi:application",
        "--log-level",
        GUNICORN_LOG_LEVEL,
        "-w",
        GUNICORN_WORKER_COUNT,
        "-k",
        GUNICORN_WORKER_CLASS,
        "-b",
        f"{SERVER_HOST}:{SERVER_PORT}",
        "--pid",
        GUNICORN_PIDFILE,
    ]
    if AUTORELOAD:
        command += ["--reload"]
    run_command(command)


def run_celery_worker() -> None:
    print("Launching celery workers")
    worker_command = [
        "celery",
        "--app",
        "thunderstore.core",
        "worker",
        "--loglevel",
        CELERY_LOG_LEVEL,
        "--pidfile",
        CELERY_PIDFILE,
    ]
    if CELERY_POOL:
        worker_command += ["--pool", CELERY_POOL]
    if CELERY_CONCURRENCY:
        worker_command += ["--concurrency", CELERY_CONCURRENCY]
    command = []
    if AUTORELOAD:
        command += WATCHMEDO_COMMAND
    command += worker_command
    run_command(command)


def run_celery_beat() -> None:
    print("Launching celery beat")
    worker_command = [
        "celery",
        "--app",
        "thunderstore.core",
        "beat",
        "--loglevel",
        CELERY_LOG_LEVEL,
        "--pidfile",
        CELERY_PIDFILE,
        "--scheduler",
        "django_celery_beat.schedulers:DatabaseScheduler",
    ]
    command = []
    if AUTORELOAD:
        command += WATCHMEDO_COMMAND
    command += worker_command
    run_command(command)


def run_migrations():
    print("Ensuring database schema is up to date")
    run_command("python manage.py migrate")


def run_server(mode: str) -> None:
    if RUN_MIGRATIONS:
        run_migrations()

    if mode == "django":
        run_django()
    elif mode == "gunicorn":
        run_gunicorn()
    elif mode == "celeryworker":
        run_celery_worker()
    elif mode == "celerybeat":
        run_celery_beat()


def dump_env() -> None:
    with open(os.path.expanduser("~") + "/.bashrc", "a") as f:
        f.writelines(
            [
                f'declare -x {key}="{str(var)}"\n'
                for key, var in VARIABLES.items()
                if var.value is not None
            ]
        )
    with open("/var/run/thunderstore-launch.json", "w") as f:
        f.write(json.dumps({k: str(v) for k, v in VARIABLES.items()}))


mode = (" ".join(sys.argv[1:])).strip()
if mode in {"django", "gunicorn", "celeryworker", "celerybeat"}:
    RUN_MODE.value = mode
    dump_env()
    run_server(mode)
elif sys.argv[1:]:
    RUN_MODE.value = None
    dump_env()
    run_command(sys.argv[1:])
else:
    dump_env()
    run_server(str(RUN_MODE))
