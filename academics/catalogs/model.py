from datetime import datetime, timedelta, timezone
import logging
from lbrc_flask.database import db
from sqlalchemy import Boolean, DateTime, Integer, String, UnicodeText, UniqueConstraint, select
from sqlalchemy.orm import Mapped, mapped_column
from lbrc_flask.logging import log_exception


class AsyncJob(db.Model):
    __table_args__ = (
        UniqueConstraint("job_type", "entity_id", "entity_id_string", name='ux__async_job__job_type__entity'),
    )
    __mapper_args__ = {
        "polymorphic_identity": "generic",
        "polymorphic_on": "job_type",
    }

    TIMEDELTA_HOURS = 'hours'
    TIMEDELTA_DAYS = 'days'

    id: Mapped[Integer] = mapped_column(Integer, primary_key=True, nullable=False)
    job_type: Mapped[String] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[Integer] = mapped_column(Integer, nullable=True)
    entity_id_string: Mapped[String] = mapped_column(String(255), nullable=True)
    scheduled: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    error: Mapped[UnicodeText] = mapped_column(UnicodeText, nullable=True)
    retry: Mapped[Boolean] = mapped_column(Boolean, nullable=False, default=False)
    retry_timedelta_period: Mapped[String] = mapped_column(String(10), nullable=True)
    retry_timedelta_size: Mapped[Integer] = mapped_column(Integer, nullable=True)

    def run(self):
        try:
            self._run_actual()

            self.scheduled = None
            self.error = ''

            db.session.add(self)
            db.session.commit()

        except Exception as e:
            logging.error(f'Error processing {self._name()}')
            log_exception(e)
            logging.warn('Rolling back transaction')
            db.session.rollback()

            self.error = str(e)

            if self.retry and self.retry_timedelta_period and self.retry_timedelta_size:
                self.scheduled = datetime.now(timezone.utc) + self.__retry_timedelta()

            db.session.add(self)
            db.session.commit()


    def __retry_timedelta(self):
        params = {}

        if self.retry_timedelta_period == AsyncJob.TIMEDELTA_HOURS:
            params = {'hours': self.retry_timedelta_size}
        elif self.retry_timedelta_period == AsyncJob.TIMEDELTA_DAYS:
            params = {'days': self.retry_timedelta_size}
        
        return timedelta(**params)
    
    def _run_actual(self):
        raise Exception("Generic AsyncJob is not defined")

    def _name(self):
        return f'{self.job_type}: {self.entity_id} - {self.entity_id_string}'


class AsyncJobs:
    @staticmethod
    def due():
        return db.session.execute(select(AsyncJob).where(AsyncJob.scheduled < datetime.now(timezone.utc))).scalars()

    @staticmethod
    def run_due():
        for j in AsyncJobs.due():
            j.run()

    @staticmethod
    def schedule(job: AsyncJob):
        existing: AsyncJob = db.session.execute(
            select(AsyncJobs)
            .where(AsyncJob.job_type == job.job_type)
            .where(AsyncJob.entity_id == job.entity_id)
            .where(AsyncJob.entity_id_string == job.entity_id_string)
        ).scalar_or_none()
    
        if existing:
            existing.scheduled = job.scheduled
            existing.error = job.error
            existing.retry = job.retry
            existing.retry_timedelta_period = job.retry_timedelta_period
            existing.retry_timedelta_size = job.retry_timedelta_size

            db.session.add(existing)
        else:
            db.session.add(job)
