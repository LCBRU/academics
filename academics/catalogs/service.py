import logging
from pathlib import Path
from flask import current_app
from academics.model.academic import Academic
from lbrc_flask.celery import celery
from celery.signals import after_setup_logger
from lbrc_flask.async_jobs import AsyncJobs
from academics.catalogs.jobs import AcademicEnsureSourcesArePotential, AcademicFindNewPotentialSources, PublicationRemoveUnused, SourceGetPublications, SourceRefresh


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


def update_single_academic(academic: Academic):
    AsyncJobs.schedule(AcademicFindNewPotentialSources(academic))

    _process_updates.delay()


def update_all():
    for academic in Academic.query.all():
        AsyncJobs.schedule(AcademicFindNewPotentialSources(academic))
        AsyncJobs.schedule(AcademicEnsureSourcesArePotential(academic))

        for s in academic.sources:
            AsyncJobs.schedule(SourceRefresh(s))
            AsyncJobs.schedule(SourceGetPublications(s))

    AsyncJobs.schedule(PublicationRemoveUnused)

    _process_updates.delay()


def schedule_source_update(source):
    AsyncJobs.schedule(SourceRefresh(source))
    AsyncJobs.schedule(SourceGetPublications(source))

    _process_updates.delay()

@celery.task()
def _process_updates():
    logging.debug('started')

    AsyncJobs.run_due()

    logging.debug('Ended')
