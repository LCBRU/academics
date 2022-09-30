#!/usr/bin/env bash

# To run add the following line to the CRONTAB file
# * * * * * export ACADEMIC_DIR=/local/www/academics VENV=/local/www/venv/bin/activate; /local/run_worker.sh &>> /local/www/log/worker.log

cd $ACADEMIC_DIR
source $VENV

if ! pgrep -f celery &> /dev/null 2>&1; then
    echo ---------------
    echo Starting Celery
    echo ---------------

    python -m celery -A celery_worker.celery worker
else
    echo ----------------------
    echo Celery already running
    echo ----------------------
fi
