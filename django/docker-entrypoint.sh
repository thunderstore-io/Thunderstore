#!/bin/bash
python manage.py collectstatic --noinput

if [ "$DEBUG" = true ] || [ "$DEBUG" = 'True' ] || [ "$DEBUG" = 1 ]; then
    echo 'Launching in debug mode'
    python manage.py runserver 0.0.0.0:8000
else
    echo 'Launching in production mode'
    python manage.py migrate
    gunicorn core.wsgi:application --log-level debug -w 3 -k gevent -b 0.0.0.0:8000
fi
