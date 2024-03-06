from flask import abort, jsonify, redirect, render_template, request, url_for
from sqlalchemy import delete, select
from wtforms import SelectField
from academics.catalogs.service import create_potential_sources, update_single_academic
from academics.model.academic import Academic, AcademicPotentialSource, CatalogPublicationsSources, Source
from .. import blueprint
from lbrc_flask.database import db
from lbrc_flask.json import validate_json
from lbrc_flask.forms import ConfirmForm, FlashingForm


class AcademicEditForm(FlashingForm):
    academic_id = SelectField('Other Academic', coerce=int)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        academics = db.session.execute(
            select(Academic).order_by(Academic.last_name).order_by(Academic.first_name)
        ).unique().scalars()

        self.academic_id.choices = [(0, '')] + [(a.id, a.full_name) for a in academics]


@blueprint.route("/sources/<int:id>/details", methods=['GET', 'POST'])
def source_details(id):
    form = AcademicEditForm()

    s = db.get_or_404(Source, id)

    if not s:
        abort(404)

    if form.validate_on_submit():
        if form.has_value('academic_id'):
            create_potential_sources([s], db.get_or_404(Academic, form.academic_id.data), not_match=False)

        return redirect(request.args.get('prev', ''))

    return render_template(
        "ui/source_details.html",
        source=s,
        form=form,
    )


@blueprint.route("/sources/potential_for_academic/<int:id>")
def academics_potential_sources(id):
    a = db.session.get(Academic, id)

    if not a:
        abort(404)

    return render_template(
        "ui/potential_sources.html",
        academic=a,
    )


@blueprint.route("/sources/potential_for_academic_status", methods=['POST'])
@validate_json({
    'type': 'object',
    'properties': {
        'id': {'type': 'integer'},
        'academic_id': {'type': 'integer'},
        'status': {'type': 'string'},
    },
    "required": ["id", "academic_id", "status"]
})
def academics_amend_potential_sources():
    ps : AcademicPotentialSource = db.get_or_404(AcademicPotentialSource, request.json.get('id'))
    a : Academic = db.get_or_404(Academic, request.json.get('academic_id'))
    status = request.json.get('status').lower()

    UNASSIGNED = 'unassigned'
    NO_MATCH = 'no match'
    MATCH = 'match'

    ALL_STATUSES = {UNASSIGNED, NO_MATCH, MATCH}

    if status not in ALL_STATUSES:
        abort(406, f"Status not recognised should be {ALL_STATUSES}, but is {status}")

    if ps.source.academic and ps.source.academic != a:
        abort(406, f"Academic does not match source academic of {ps.source.academic.full_name}, but is {a.full_name}")

    match request.json.get('status').lower():
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

    return jsonify({'status': request.json.get('status')}), 200


@blueprint.route("/sources/delete", methods=['POST'])
def delete_author():
    form = ConfirmForm()

    if form.validate_on_submit():
        s = db.get_or_404(Source, form.id.data)

        db.session.delete(s)
        db.session.commit()

    return redirect(url_for('ui.index'))
