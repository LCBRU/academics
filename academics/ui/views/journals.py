from flask import render_template, render_template_string, request, redirect
from lbrc_flask.forms import FlashingForm, SearchForm, boolean_coerce
from lbrc_flask.database import db
from sqlalchemy import func, select
from wtforms.fields.simple import BooleanField
from wtforms import SelectField
from academics.catalogs.service import updating
from academics.model.publication import Journal
from flask_security import roles_accepted

from .. import blueprint


class JournalSearchForm(SearchForm):
    preprint = SelectField(
        'Preprint',
        choices=[('', ''), ('True', 'Yes'), ('False', 'No')],
        coerce=boolean_coerce,
        default=None,
    )


@blueprint.route("/journals/")
def journals():
    search_form = JournalSearchForm(formdata=request.args)

    q = journal_search_query(search_form)

    journals = db.paginate(
        select=q,
        page=search_form.page.data,
        per_page=20,
        error_out=False,
    )

    return render_template(
        "ui/journals.html",
        journals=journals,
        search_form=search_form,
        updating=updating(),
    )


def journal_search_query(search_form):
    q = select(Journal)

    if search_form.search.data:
        q = q.where(Journal.name.like("%{}%".format(search_form.search.data)))

    if search_form.has_value('preprint'):
        is_is = 1 if search_form.preprint.data else 0
        q = q.where(func.coalesce(Journal.preprint, 0) == is_is)

    q = q.order_by(Journal.name)

    return q


@blueprint.route("/journal/update_preprint/<int:id>/<int:is_preprint>", methods=['POST'])
@roles_accepted('validator')
def journal_update_preprint(id, is_preprint):
    journal = db.get_or_404(Journal, id)
    journal.preprint = is_preprint
    db.session.add(journal)
    db.session.commit()

    template = '''
        {% from "ui/_journal_details.html" import render_journal %}

        {{ render_journal(journal, current_user) }}
    '''

    return render_template_string(template, journal=journal)
