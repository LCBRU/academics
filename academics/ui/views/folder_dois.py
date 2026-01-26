
from .. import blueprint
from academics.services.folder import create_publication_folder, remove_doi_from_folder
from academics.services.publication_searching import PublicationSearchForm, publication_search_query
from flask import flash, redirect, url_for
from lbrc_flask.database import db
from lbrc_flask.response import refresh_details
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


@blueprint.route("/publications/create_folder", methods=['POST'])
def publication_create_folder():
    search_form = PublicationSearchForm()

    q = publication_search_query(search_form)
    publications = db.session.execute(q).unique().scalars().all()

    folder = create_publication_folder(publications)

    flash(f'Publications added to new folder "{folder.name}"')

    db.session.commit()

    return redirect(url_for('ui.folders'))
