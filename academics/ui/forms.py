from lbrc_flask.forms import SearchForm
from flask_login import current_user
from acadex.model import Academic
from wtforms import SelectField


def _get_academics_choices():
    academics = Academic.query.order_by(Academic.name).all()

    return [(0, 'All')] + [(a.id, a.name) for a in academics]


class PublicationSearchForm(SearchForm):
    academic_id = SelectField('Academic', coerce=int, choices=[])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.academic_id.choices = _get_academics_choices()

