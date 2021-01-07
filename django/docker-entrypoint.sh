#!/bin/bash

workers=${GUNICORN_WORKER_COUNT:-2}
loglevel=${GUNICORN_LOG_LEVEL:-info}
maxrequests=${GUNICORN_MAX_REQUESTS:-10000}
maxrequestsjitter=${GUNICORN_MAX_REQUESTS_JITTER:-1000}

export >> ~/.profile

if [ "$DEBUG" = true ] || [ "$DEBUG" = 'True' ] || [ "$DEBUG" = 1 ]; then
    echo 'Launching in debug mode'
    python manage.py runserver 0.0.0.0:8000
else
    echo 'Launching in production mode'
    python manage.py migrate
    echo "gunicorn thunderstore.core.wsgi:application --log-level $loglevel -w $workers -k gevent -b 0.0.0.0:8000 --max-requests $maxrequests --max-requests-jitter $maxrequestsjitter"
    gunicorn thunderstore.core.wsgi:application --log-level $loglevel -w $workers -k gevent -b 0.0.0.0:8000
fi
