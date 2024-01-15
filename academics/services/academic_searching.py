from lbrc_flask.forms import SearchForm
from sqlalchemy import alias, select
from wtforms import SelectField
from academics.model.academic import Academic
from academics.model.theme import Theme


class AcademicSearchForm(SearchForm):
    theme_id = SelectField('Theme', coerce=int)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.theme_id.choices = [(0, ''), (-1, '[Unset]')] + [(t.id, t.name) for t in Theme.query.all()]


def academic_search_query(search_form):
    q = select(Academic).where(Academic.initialised == True)

    if search_form.search.data:
        q = q.where((Academic.first_name + ' ' + Academic.last_name).like("%{}%".format(search_form.search.data)))

    if search_form.has_value('theme_id'):
        if search_form.theme_id.data == -1:
            q = q.where(~Academic.themes.any())
        else:
            q = q.where(Academic.themes.any(Theme.id == search_form.theme_id.data))

    q = q.order_by(Academic.last_name).order_by(Academic.first_name)

    return q


def theme_search_query(search_form):
    q = select(Theme)

    if search_form.search.data:
        q = q.where(Theme.name.like("%{}%".format(search_form.search.data)))

    if search_form.has_value('theme_id'):
        q = q.where(Theme.id == search_form.theme_id.data)

    q = q.order_by(Theme.name)

    return q
