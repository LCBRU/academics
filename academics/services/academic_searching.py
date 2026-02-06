from lbrc_flask.forms import SearchForm
from sqlalchemy import or_, select
from wtforms import SelectField
from academics.model.academic import Academic
from academics.model.theme import Theme
from academics.services.folder import folder_academic_query
from lbrc_flask.database import db

class AcademicSearchForm(SearchForm):
    theme_id = SelectField('Theme')

    def __init__(self, **kwargs):
        super().__init__(search_placeholder='Search Academic Name', **kwargs)

        themes = db.session.execute(select(Theme).order_by(Theme.name)).scalars().all()

        self.theme_id.choices = [('', ''), (-1, '[Unset]')] + [(t.id, t.name) for t in themes]


def academic_search_query(search_data):
    q = select(Academic).where(Academic.initialised == True)

    if x := search_data.get('search'):
        for word in x.split():
            q = q.where(or_(
                Academic.first_name.like(f"%{word}%"),
                Academic.last_name.like(f"%{word}%"),
            ))

    if x := search_data.get('theme_id'):
        x = int(x)
        if x == -1:
            q = q.where(~Academic.themes.any())
        else:
            q = q.where(Academic.themes.any(Theme.id == x))

    if x := search_data.get('folder_id'):
        x = int(x)

        faq = folder_academic_query().subquery()

        q = q.where(Academic.id.in_(
            select(faq.c.academic_id)
            .where(faq.c.folder_id == x)
        ))

    if x := search_data.get('is_user'):
        x = bool(x)

        if x:
            q = q.where(Academic.user_id != None)
        else:
            q = q.where(Academic.user_id == None)

    q = q.order_by(Academic.last_name).order_by(Academic.first_name).order_by(Academic.id)

    return q


def theme_search_query(search_data):
    q = select(Theme)

    if x := search_data.get('search'):
        for word in x.split():
            q = q.where(Theme.name.like(f"%{word}%"))

    if x := search_data.get('theme_id'):
        q = q.where(Theme.id == x)

    q = q.order_by(Theme.name)

    return q
