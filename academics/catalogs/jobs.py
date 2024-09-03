from lbrc_flask.async_jobs import AsyncJob
from lbrc_flask.database import db
from sqlalchemy import select
from academics.catalogs.open_alex import get_open_alex_affiliation_data
from academics.catalogs.scopus import get_scopus_affiliation_data
from academics.model.academic import Affiliation
from academics.model.catalog import CATALOG_OPEN_ALEX, CATALOG_SCOPUS


class AffiliationRefresh(AsyncJob):
    __mapper_args__ = {
        "polymorphic_identity": "AffiliationRefresh",
    }

    def _run_actual(self):
        affiliation = db.session.execute(select(Affiliation).where(Affiliation.id == self.entity_id)).scalar()
        
        if affiliation.catalog == CATALOG_SCOPUS:
            aff_data = get_scopus_affiliation_data(affiliation.catalog_identifier)
        if affiliation.catalog == CATALOG_OPEN_ALEX:
            aff_data = get_open_alex_affiliation_data(affiliation.catalog_identifier)

        aff_data.update_affiliation(affiliation)

        db.session.add(affiliation)
        db.session.commit()
