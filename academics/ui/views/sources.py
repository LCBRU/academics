from flask import abort, jsonify, redirect, render_template, request, url_for
from sqlalchemy import select
from wtforms import SelectField
from academics.catalogs.service import create_potential_sources, update_single_academic
from academics.model.academic import Academic, AcademicPotentialSource, Source
from .. import blueprint
from lbrc_flask.database import db
from lbrc_flask.json import validate_json
from lbrc_flask.forms import ConfirmForm, FlashingForm
from flask_security import roles_accepted
from lbrc_flask.response import refresh_response, trigger_response


class AcademicEditForm(FlashingForm):
    academic_id = SelectField('Other Academic', coerce=int)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        academics = db.session.execute(
            select(Academic).order_by(Academic.last_name).order_by(Academic.first_name)
        ).unique().scalars()

        self.academic_id.choices = [(0, '')] + [(a.id, a.full_name) for a in academics]


@blueprint.route("/source/<int:id>/summary_details", methods=['GET', 'POST'])
def source_summary_details(id):
    form = AcademicEditForm()

    s = db.get_or_404(Source, id)

    if not s:
        abort(404)

    if form.validate_on_submit():
        if form.has_value('academic_id'):
            create_potential_sources([s], db.get_or_404(Academic, form.academic_id.data), not_match=False)

        return refresh_response()

    return render_template(
        "ui/source_summary_details.html",
        source=s,
        form=form,
    )


@blueprint.route("/sources/potential_for_academic/<int:id>")
def academics_potential_sources(id):
    a = db.get_or_404(Academic, id)

    return render_template(
        "ui/potential_sources.html",
        academic=a,
    )


@blueprint.route("/sources/<int:id>/academic/<int:academic_id>/<string:status>", methods=['POST'])
@roles_accepted('editor')
def academics_amend_potential_sources(id, academic_id, status):
    ps : AcademicPotentialSource = db.get_or_404(AcademicPotentialSource, id)
    a : Academic = db.get_or_404(Academic, academic_id)

    UNASSIGNED = 'unassigned'
    NO_MATCH = 'no match'
    MATCH = 'match'

    ALL_STATUSES = {UNASSIGNED, NO_MATCH, MATCH}

    if status not in ALL_STATUSES:
        abort(406, f"Status not recognised should be {ALL_STATUSES}, but is {status}")

    if ps.source.academic and ps.source.academic != a:
        abort(406, f"Academic does not match source academic of {ps.source.academic.full_name}, but is {a.full_name}")

    match status:
        case 'unassigned':
            ps.source.academic = None
            ps.not_match = False
        case 'no match':
            ps.source.academic = None
            ps.not_match = True
        case 'match':
            ps.source.academic = a
            ps.not_match = False
            update_single_academic(a)
    
    db.session.add(ps)
    db.session.commit()

    return trigger_response('refreshModal')


@blueprint.route("/sources/delete", methods=['POST'])
@roles_accepted('editor')
def delete_author():
    form = ConfirmForm()

    if form.validate_on_submit():
        s = db.get_or_404(Source, form.id.data)

        db.session.delete(s)
        db.session.commit()

    return redirect(url_for('ui.index'))
