from os import abort
from flask import jsonify, redirect, render_template, request
from lbrc_flask.forms import FlashingForm, SearchForm, ConfirmForm
from academics.model import Objective, ScopusPublication, User, Theme
from .. import blueprint
from wtforms import HiddenField, StringField
from lbrc_flask.database import db
from lbrc_flask.json import validate_json
from lbrc_flask.security import current_user_id, system_user_id
from wtforms import SelectField
from wtforms.validators import Length, DataRequired


class ObjectiveSearchForm(SearchForm):
    theme_id = SelectField('Theme', coerce=int)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

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
    theme_id = HiddenField('Theme', validators=[DataRequired()])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


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


@blueprint.route("/objective/save", methods=['POST'])
def objective_save():
    form = ObjectiveEditForm()

    if form.validate_on_submit():
        id = form.id.data

        if id:
            obj = Objective.query.get_or_404(id)
        else:
            obj = Objective()

        obj.name = form.name.data
        obj.theme_id = form.theme_id.data

        db.session.add(obj)
        db.session.commit()

    return redirect(request.referrer)


@blueprint.route("/objective/delete", methods=['POST'])
def objective_delete():
    form = ConfirmForm()

    if form.validate_on_submit():
        objective = Objective.query.get_or_404(form.id.data)

        db.session.delete(objective)
        db.session.commit()

    return redirect(request.referrer)


@blueprint.route("/objective/remove_publication", methods=['POST'])
@validate_json({
    'type': 'object',
    'properties': {
        'objective_id': {'type': 'integer'},
        'scopus_publication_id': {'type': 'integer'},
    },
    "required": ["objective_id", "scopus_publication_id"]
})
def objective_remove_publication():
    p = ScopusPublication.query.get_or_404(request.json.get('scopus_publication_id'))
    f = Objective.query.get_or_404(request.json.get('objective_id'))

    f.publications.remove(p)

    db.session.add(f)
    db.session.commit()

    return jsonify({}), 200


@blueprint.route("/objective/add_publication", methods=['POST'])
@validate_json({
    'type': 'object',
    'properties': {
        'objective_id': {'type': 'integer'},
        'scopus_publication_id': {'type': 'integer'},
    },
    "required": ["objective_id", "scopus_publication_id"]
})
def objective_add_publication():
    p = ScopusPublication.query.get_or_404(request.json.get('scopus_publication_id'))
    f = Objective.query.get_or_404(request.json.get('objective_id'))

    f.publications.add(p)

    db.session.add(f)
    db.session.commit()

    return jsonify({}), 200
