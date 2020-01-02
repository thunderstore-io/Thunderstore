#!/bin/bash

workers=${GUNICORN_WORKER_COUNT:-2}
loglevel=${GUNICORN_LOG_LEVEL:-info}

if [ "$DEBUG" = true ] || [ "$DEBUG" = 'True' ] || [ "$DEBUG" = 1 ]; then
    echo 'Launching in debug mode'
    python manage.py runserver 0.0.0.0:8000
else
    echo 'Launching in production mode'
    python manage.py migrate
    echo "gunicorn core.wsgi:application --log-level $loglevel -w $workers -k gevent -b 0.0.0.0:8000"
    gunicorn core.wsgi:application --log-level $loglevel -w $workers -k gevent -b 0.0.0.0:8000
fi
