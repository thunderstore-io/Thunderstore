#!/bin/bash

source /root/.profile
cd /app/
python manage.py update_caches
