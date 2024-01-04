from flask import request
from sqlalchemy import select
from academics.model.academic import Academic

from academics.services.publication_searching import PublicationSummarySearchForm, publication_summary
from lbrc_flask.database import db

from .. import blueprint


@blueprint.route("/publications", methods=['GET', 'POST'])
def api_publications():
    search_form = PublicationSummarySearchForm(formdata=request.args)

    return publication_summary(search_form)


@blueprint.route("/academics", methods=['GET', 'POST'])
def api_academics():

    q = select(Academic).where(Academic.initialised == True)
    
    return [{
        'first_name': a.first_name,
        'last_name': a.last_name,
        'theme': a.theme.name,
        'orcid': a.orcid,
        'scopus_ids': list(a.all_scopus_ids()),
    } for a in db.session.scalars(q).all()]
