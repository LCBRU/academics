from flask import request
from lbrc_flask.forms import SearchForm
from sqlalchemy import select
from wtforms import MonthField, SelectField, HiddenField, SelectMultipleField

from academics.model import (Academic, NihrAcknowledgement, Theme)
from academics.publication_searching import publication_summary
from lbrc_flask.database import db

from .. import blueprint

def _get_nihr_acknowledgement_choices():
    return [(f.id, f.name.title()) for f in NihrAcknowledgement.query.order_by(NihrAcknowledgement.name).all()]


class PublicationSearchForm(SearchForm):
    total = SelectField('Total', choices=[('BRC', 'BRC'), ('Theme', 'Theme'), ('Academic', 'Academic')])
    measure = SelectField('Measure', choices=[('Percentage', 'Percentage'), ('Publications', 'Publications')])
    theme_id = SelectField('Theme')
    nihr_acknowledgement_id = SelectMultipleField('Acknowledgement')
    academic_id = HiddenField()
    publication_date_start = MonthField('Publication Start Date')
    publication_date_end = MonthField('Publication End Date')
    supress_validation_historic = HiddenField('supress_validation_historic', default=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.theme_id.choices = [('', '')] + [(t.id, t.name) for t in Theme.query.all()]
        self.nihr_acknowledgement_id.choices = [('-1', 'Unvalidated')] + _get_nihr_acknowledgement_choices()


@blueprint.route("/publications", methods=['GET', 'POST'])
def api_publications():
    search_form = PublicationSearchForm(formdata=request.args)

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
