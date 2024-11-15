import re

from academics.services.publication_searching import PublicationSearchForm, publication_search_query
from .. import blueprint
from academics.ui.views.decorators import assert_folder_user
from flask import flash, redirect, render_template, render_template_string, url_for
from sqlalchemy import select
from academics.model.folder import Folder, FolderDoi
from academics.model.publication import Publication
from lbrc_flask.database import db
from datetime import datetime, timezone
from lbrc_flask.security import current_user_id
from lbrc_flask.response import refresh_response
from wtforms import TextAreaField
from lbrc_flask.forms import FlashingForm
from wtforms.validators import DataRequired


class UploadFolderDois(FlashingForm):
    dois = TextAreaField('DOIs', validators=[DataRequired()])


@blueprint.route("/folder/<int:folder_id>/doi/delete/<path:doi>", methods=['POST'])
def folderdoi_delete(folder_id, doi):
    remove_doi_from_folder(folder_id, doi)

    return render_publication_folders(doi)


@blueprint.route("/folder/<int:id>/upload_dois", methods=['GET', 'POST'])
@assert_folder_user()
def folder_upload_dois(id):
    form = UploadFolderDois()

    if form.validate_on_submit():
        for doi in filter(None, re.split(',|\s', form.dois.data)):
            doi = doi.strip('.:')
            add_doi_to_folder(id, doi)

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

    return redirect(url_for('ui.folders'))


def render_publication_folders(doi):
    pq = select(Publication).where(Publication.doi == doi)

    template = '''
        {% from "ui/_folder_dois.html" import render_publication_folders with context %}

        {{ render_publication_folders(publication, folders) }}
    '''

    return render_template_string(
        template,
        publication=db.session.execute(pq).unique().scalar(),
        folders=db.session.execute(select(Folder)).scalars().all(),
    )


def add_doi_to_folder(folder_id, doi):
    fd = db.session.execute(
        select(FolderDoi)
        .where(FolderDoi.folder_id == folder_id)
        .where(FolderDoi.doi == doi)
    ).scalar_one_or_none()

    if not fd:
        db.session.add(FolderDoi(
            folder_id=folder_id,
            doi=doi,
        ))
        db.session.commit()


def remove_doi_from_folder(folder_id, doi):
    fd: FolderDoi = db.session.execute(
        select(FolderDoi)
        .where(FolderDoi.folder_id == folder_id)
        .where(FolderDoi.doi == doi)
    ).scalar_one_or_none()

    if fd:
        fd.deleted = True
        db.session.add(fd)
        db.session.commit()


def create_publication_folder(publications):
    folder = Folder(
        name=f'Publication Search {datetime.now(timezone.utc):%Y%m%d_%H%M%S}',
        owner_id=current_user_id(),
    )
    db.session.add(folder)
    db.session.flush()

    db.session.add_all([
        FolderDoi(folder_id=folder.id, doi=p.doi) for p in publications
    ])

    db.session.commit()

    return folder
