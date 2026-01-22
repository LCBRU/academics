import re

from academics.services.folder import add_doi_to_folder, create_publication_folder, remove_doi_from_folder
from academics.services.publication_searching import PublicationSearchForm, publication_search_query
from .. import blueprint
from academics.ui.views.decorators import assert_folder_user
from flask import flash, redirect, render_template, render_template_string, url_for
from sqlalchemy import select
from academics.model.folder import Folder
from academics.model.publication import Publication
from lbrc_flask.database import db
from lbrc_flask.response import refresh_response, refresh_details
from wtforms import TextAreaField
from lbrc_flask.forms import FlashingForm
from wtforms.validators import DataRequired


class UploadFolderDois(FlashingForm):
    dois = TextAreaField('DOIs', validators=[DataRequired()])


@blueprint.route("/folder/<int:folder_id>/doi/delete/<path:doi>", methods=['POST'])
def folderdoi_delete(folder_id, doi):
    remove_doi_from_folder(folder_id, doi)
    db.session.commit()
    return refresh_details()


@blueprint.route("/folder/<int:id>/upload_dois", methods=['GET', 'POST'])
@assert_folder_user()
def folder_upload_dois(id):
    form = UploadFolderDois()

    if form.validate_on_submit():
        for doi in filter(None, re.split(',|\s', form.dois.data)):
            doi = doi.strip('.:')
            add_doi_to_folder(id, doi)

        db.session.commit()

        return refresh_response()

    return render_template(
        "lbrc/form_modal.html",
        title="Upload Folder DOIs",
        form=form,
        url=url_for('ui.folder_upload_dois', id=id),
    )


@blueprint.route("/publications/create_folder", methods=['POST'])
def publication_create_folder():
    search_form = PublicationSearchForm()

    q = publication_search_query(search_form)

    folder = create_publication_folder(db.session.execute(q).unique().scalars())

    flash(f'Publications added to new folder "{folder.name}"')

    db.session.commit()

    return redirect(url_for('ui.folders'))
