import logging
from pathlib import Path
from flask import current_app
from academics.model.academic import Academic
from lbrc_flask.celery import celery
from celery.signals import after_setup_logger
from lbrc_flask.async_jobs import AsyncJobs


@after_setup_logger.connect
def setup_loggers(logger, *args, **kwargs):
    formatter = logging.Formatter('%(asctime)s (%(levelname)s) %(module)s::%(funcName)s(%(lineno)d): %(message)s')

    # add filehandler
    fh = logging.FileHandler(str(Path(current_app.config["CELERY_LOG_DIRECTORY"]) / 'service.log'))
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.propagate = False


def updating():
    result = Academic.query.filter(Academic.updating == True).count() > 0
    logging.info(result)
    return result


def refresh():
    _process_updates.delay()


@celery.task()
def _process_updates():
    logging.debug('started')

    AsyncJobs.run_due()

    logging.debug('Ended')
