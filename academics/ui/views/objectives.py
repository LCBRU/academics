from flask import render_template, request, url_for
from lbrc_flask.forms import FlashingForm, SearchForm, ConfirmForm
from academics.model.objective import Objective
from academics.model.security import User

from academics.model.theme import Theme
from .. import blueprint
from wtforms import HiddenField, RadioField, StringField
from lbrc_flask.database import db
from lbrc_flask.security import current_user_id, system_user_id
from wtforms import SelectField
from wtforms.validators import Length, DataRequired
from lbrc_flask.response import refresh_response


class ObjectiveSearchForm(SearchForm):
    theme_id = SelectField('Theme', coerce=int)

    def __init__(self, **kwargs):
        super().__init__(search_placeholder='Search Name', **kwargs)

        choices = [(t.id, t.name) for t in Theme.query.all()]

        if choices:
            self.theme_id.choices = choices
            self.theme_id.default = choices[0][0]

    def get_theme_id(self):
        if self.theme_id.data:
            return self.theme_id.data
        else:
            return self.theme_id.default


class ObjectiveEditForm(FlashingForm):
    id = HiddenField('id')
    name = StringField('Name', validators=[DataRequired(), Length(max=500)])
    theme_id = RadioField('Theme', coerce=int)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.theme_id.choices = [(t.id, t.name) for t in Theme.query.all()]


@blueprint.route("/objectives/")
def objectives():
    search_form = ObjectiveSearchForm(formdata=request.args)
    
    q = _get_objective_query(search_form)

    q = q.order_by(Objective.name)

    objectives = q.paginate(
        page=search_form.page.data,
        per_page=5,
        error_out=False,
    )

    return render_template(
        "ui/objectives.html",
        search_form=search_form,
        objectives=objectives,
        users=User.query.filter(User.id.notin_([current_user_id(), system_user_id()])).all(),
        edit_objective_form=ObjectiveEditForm(),
        confirm_form=ConfirmForm(),
    )


def _get_objective_query(search_form):
    q = Objective.query
    q = q.filter(Objective.theme_id == search_form.get_theme_id())

    if search_form.search.data:
        q = q.filter(Objective.name.like(f'%{search_form.search.data}%'))

    return q


@blueprint.route("/objective/<int:id>/edit", methods=['GET', 'POST'])
@blueprint.route("/objective/add", methods=['GET', 'POST'])
def objective_edit(id=None):
    if id:
        objective = db.get_or_404(Objective, id)
        title=f'Edit Objective'
    else:
        objective = Objective()
        title=f'Add Objective'

    form = ObjectiveEditForm(obj=objective)

    if form.validate_on_submit():
        objective.name = form.name.data
        objective.theme_id = form.theme_id.data

        db.session.add(objective)
        db.session.commit()

        return refresh_response()

    return render_template(
        "lbrc/form_modal.html",
        title=title,
        form=form,
        url=url_for('ui.objective_edit', id=id),
    )


@blueprint.route("/objective/<int:id>/delete", methods=['POST'])
def objective_delete(id):
    objective = db.get_or_404(Objective, id)

    db.session.delete(objective)
    db.session.commit()

    return refresh_response()
