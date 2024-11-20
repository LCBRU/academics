from academics.jobs.emails import email_theme_folder_publication_list
from academics.services.academic_searching import academic_search_query
from academics.services.folder import FolderPublicationSearchForm, FolderThemeSearchForm, add_doi_to_folder, current_user_folders_search_query, folder_publication_search_query, folder_theme_search_query, is_folder_name_duplicate, remove_doi_from_folder
from academics.services.folder_academics import folder_academics_search_query_with_folder_summary
from academics.services.publication_searching import publication_picker_search_query
from academics.ui.views.users import render_user_search_results, user_search_query
from .. import blueprint
from flask import abort, flash, render_template, request, url_for
from flask_login import current_user
from lbrc_flask.forms import FlashingForm, SearchForm
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from academics.model.academic import Academic, AcademicPicker, CatalogPublicationsSources, Source
from academics.model.folder import Folder, FolderDoi, FolderDoiUserRelevance
from academics.model.publication import CatalogPublication, Publication
from academics.model.security import User
from academics.model.theme import Theme
from academics.ui.views.decorators import assert_folder_user, assert_folder_user_or_author
from wtforms import BooleanField, DateField, HiddenField, SelectField, StringField, TextAreaField, validators
from lbrc_flask.database import db
from lbrc_flask.security import current_user_id
from lbrc_flask.response import refresh_response
from lbrc_flask.validators import is_invalid_doi
from wtforms.validators import Length, DataRequired, Optional
from lbrc_flask.requests import get_value_from_all_arguments
from datetime import date


def folder_name_unique_validator(form, field):
    if is_folder_name_duplicate(name=form.name.data, folder_id=form.id.data):
        raise validators.ValidationError('Folder name has already been used')


class FolderEditForm(FlashingForm):
    id = HiddenField('id')
    name = StringField('Name', validators=[Length(max=1000), DataRequired(), folder_name_unique_validator])
    description = TextAreaField('Description', validators=[Length(max=1000)])
    autofill_year = SelectField('Autofill Year', coerce=int, default=None, validators=[Optional()])
    author_access = BooleanField('Allow authors access')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.autofill_year.choices = [(0, '')] + [(y, f'April {y} to March {y+1}') for y in range(2024, date.today().year + 2)]

    def populate_item(self, item):
        item.name = self.name.data
        item.description = self.description.data

        if self.autofill_year.data:
            item.autofill_year = self.autofill_year.data
        else:
            item.autofill_year = None
        
        item.author_access = self.author_access.data
    

@blueprint.route("/folders/")
def folders():
    search_form = SearchForm(search_placeholder='Search Name', formdata=request.args)

    return render_template(
        "ui/folder/index.html",
        search_form=search_form,
        folders=db.paginate(
            select=current_user_folders_search_query(search_form)
        ),
    )


@blueprint.route("/folder/<int:id>/edit", methods=['GET', 'POST'])
@assert_folder_user()
def folder_edit(id):
    folder = db.get_or_404(Folder, id)
    form = FolderEditForm(obj=folder)

    if form.validate_on_submit():
        form.populate_item(folder)

        db.session.add(folder)
        db.session.commit()

        return refresh_response()

    return render_template(
        "lbrc/form_modal.html",
        title='Edit Folder',
        form=form,
        url=url_for('ui.folder_edit', id=id),
    )


@blueprint.route("/folder/add", methods=['GET', 'POST'])
@assert_folder_user()
def folder_add():
    form = FolderEditForm()

    if form.validate_on_submit():
        folder = Folder()
        folder.owner = current_user

        form.populate_item(folder)

        db.session.add(folder)
        db.session.commit()

        return refresh_response()

    return render_template(
        "lbrc/form_modal.html",
        title='Add Folder',
        form=form,
        url=url_for('ui.folder_add'),
    )


@blueprint.route("/folder/<int:id>/delete", methods=['POST'])
@assert_folder_user()
def folder_delete(id):
    folder = db.get_or_404(Folder, id)

    db.session.delete(folder)
    db.session.commit()

    return refresh_response()


@blueprint.route("/folder/<int:folder_id>/shared_user/search")
@assert_folder_user()
def folder_shared_user_search(folder_id):
    f: Folder = db.get_or_404(Folder, folder_id)

    return render_template(
        "lbrc/search.html",
        title=f"Add Shared User to Folder '{f.name}'",
        results_url=url_for('ui.folder_shared_user_search_results', folder_id=f.id),
    )


@blueprint.route("/folder/<int:folder_id>/shared_user/search_results/<int:page>")
@blueprint.route("/folder/<int:folder_id>/shared_user/search_results")
@assert_folder_user()
def folder_shared_user_search_results(folder_id, page=1):
    f: Folder = db.get_or_404(Folder, folder_id)

    q = user_search_query(get_value_from_all_arguments('search_string') or '',)
    q = q.where(User.id.not_in([u.id for u in f.shared_users]))

    results = db.paginate(select=q)

    return render_user_search_results(
        results=results,
        title="Add shared user to folder '{f.name}'",
        add_url=url_for('ui.folder_add_shared_user', folder_id=f.id),
        results_url='ui.folder_shared_user_search_results',
        results_url_args={'folder_id': f.id},
    )


@blueprint.route("/folder/<int:id>/remove_shared_user/<int:user_id>", methods=['POST'])
@assert_folder_user()
def folder_remove_shared_user(id, user_id):
    u = db.get_or_404(User, user_id)
    f = db.get_or_404(Folder, id)

    f.shared_users.remove(u)

    db.session.add(f)
    db.session.commit()

    return refresh_response()


@blueprint.route("/folder/<int:folder_id>/add_shared_user", methods=['POST'])
@assert_folder_user()
def folder_add_shared_user(folder_id):
    f = db.get_or_404(Folder, folder_id)

    id: int = get_value_from_all_arguments('id')
    u = db.get_or_404(User, id)

    f.shared_users.add(u)

    db.session.add(f)
    db.session.commit()

    return refresh_response()


@blueprint.route("/folder/<int:folder_id>/doi/delete_publication/<path:doi>", methods=['POST'])
@assert_folder_user()
def folder_delete_publication(folder_id, doi):
    remove_doi_from_folder(folder_id, doi)
    db.session.commit()

    return refresh_response()


@blueprint.route("/folder/<int:folder_id>/publications")
@blueprint.route("/folder/<int:folder_id>/acadmic/<int:academic_id>/publications")
@blueprint.route("/folder/<int:folder_id>/theme/<int:theme_id>/publications")
@assert_folder_user_or_author()
def folder_publications(folder_id, academic_id=None, theme_id=None):
    search_form = FolderPublicationSearchForm()

    folder = db.get_or_404(Folder, folder_id)
    academic = db.session.execute(select(Academic).where(Academic.id == academic_id)).scalar_one_or_none()
    theme = db.session.execute(select(Theme).where(Theme.id == theme_id)).scalar_one_or_none()

    q = folder_publication_search_query(folder=folder, search_form=search_form)
    q = q.options(
        selectinload(Publication.catalog_publications)
        .selectinload(CatalogPublication.catalog_publication_sources)
        .selectinload(CatalogPublicationsSources.source)
        .selectinload(Source.academic)
    )

    publications = db.paginate(select=q, per_page=10)

    return render_template(
        "ui/folder/publications.html",
        search_form=search_form,
        publications=publications,
        folder=folder,
        academic=academic,
        theme=theme,
    )


@blueprint.route("/folder/<int:folder_id>/academics")
@assert_folder_user()
def folder_academics(folder_id):
    search_form: SearchForm = SearchForm("Search Folder Academics")

    folder = db.get_or_404(Folder, folder_id)

    q = folder_academics_search_query_with_folder_summary(
        folder_id=folder.id,
        search_string=search_form.search.data,
    )
    q = q.options(selectinload(Academic.user))

    academics = db.paginate(
        select=q,
        per_page=20,
    )

    return render_template(
        "ui/folder/academics.html",
        search_form=search_form,
        academics=academics,
        folder=folder,
    )


@blueprint.route("/folder/<int:folder_id>/themes")
@assert_folder_user()
def folder_themes(folder_id):
    search_form=FolderThemeSearchForm()
    folder = db.get_or_404(Folder, folder_id)

    q = folder_theme_search_query(folder=folder, search_form=search_form)

    themes = db.paginate(
        select=q,
        per_page=20,
    )

    return render_template(
        "ui/folder/themes.html",
        search_form=search_form,
        themes=themes,
        folder=folder,
    )


@blueprint.route("/folder/<int:folder_id>/relevant/<int:relevant>/doi/<path:doi>", methods=['POST'])
@assert_folder_user()
def folder_doi_set_user_relevance(folder_id, relevant, doi):
    fd = db.one_or_404(
        select(FolderDoi)
        .where(FolderDoi.folder_id == folder_id)
        .where(FolderDoi.doi == doi)
        )

    fdur = db.session.execute(
        select(FolderDoiUserRelevance)
        .where(FolderDoiUserRelevance.folder_doi_id == fd.id)
        .where(FolderDoiUserRelevance.user_id == current_user_id())
        ).scalar_one_or_none()

    if fdur is None:
        fdur = FolderDoiUserRelevance(
            folder_doi_id=fd.id,
            user_id=current_user_id()
        )

    fdur.relevant = (relevant != 0)
    
    db.session.add(fdur)
    db.session.commit()

    return refresh_response()


@blueprint.route("/folder/<int:folder_id>/publication/add_search")
@assert_folder_user()
def folder_add_publication_add_search(folder_id):
    f: Folder = db.get_or_404(Folder, folder_id)

    return render_template(
        "lbrc/search.html",
        title=f"Add Publication to Folder '{f.name}'",
        search_placeholder='Search Publication DOI ...',
        results_url=url_for('ui.folder_add_publication_add_search_results', folder_id=f.id),
    )


class FolderNewPublicationForm(FlashingForm):
    folder_id = HiddenField('folder_id')
    doi = HiddenField('doi')
    title = TextAreaField('Title', validators=[Length(max=1000)])
    publication_cover_date = DateField('Publication Cover Date', validators=[Optional()])


@blueprint.route("/folder/<int:folder_id>/publication/add_search_results/<int:page>")
@blueprint.route("/folder/<int:folder_id>/publication/add_search_results")
@assert_folder_user()
def folder_add_publication_add_search_results(folder_id):
    f: Folder = db.get_or_404(Folder, folder_id)

    search_string: str = get_value_from_all_arguments('search_string') or ''

    q = publication_picker_search_query(
        search_string=search_string,
        exclude_dois=[fd.doi for fd in f.dois],
    )

    results = db.paginate(select=q)

    if results.total == 0:
        if is_invalid_doi(search_string):
            return "<h6>Invalid DOI</h6>"
        else:
            return render_template(
                "lbrc/search_form_result.html",
                url=url_for('ui.catalog_publication_edit'),
                form=FolderNewPublicationForm(data={
                    'folder_id': folder_id,
                    'doi': search_string,
                }),
            )

    return render_template(
        "lbrc/search_add_results.html",
        add_title="Add publication to folder '{f.name}'",
        add_url=url_for('ui.folder_add_publication', folder_id=f.id),
        results_url='ui.folder_add_publication_add_search_results',
        results_url_args={'folder_id': f.id},
        results=results,
    )


@blueprint.route("/folder/<int:folder_id>/publication/add", methods=['POST'])
def folder_add_publication(folder_id):
    f: Folder = db.get_or_404(Folder, folder_id)

    id: int = get_value_from_all_arguments('id')
    p: Publication = db.get_or_404(Publication, id)

    add_doi_to_folder(f.id, p.doi)
    db.session.commmit()

    return refresh_response()



@blueprint.route("/folder/<int:folder_id>/theme/<int:theme_id>/email_search")
@assert_folder_user()
def folder_theme_email_search(folder_id, theme_id):
    f: Folder = db.get_or_404(Folder, folder_id)
    t: Theme = db.get_or_404(Theme, theme_id)

    return render_template(
        "ui/folder/email_academics.html",
        folder=f,
        theme=t,
        title=f"Email '{f.name}' Folder Publications for '{t.name}' to Academics",
        search_placeholder='Search Folder Academics ...',
        results_url=url_for('ui.folder_theme_email_search_results', folder_id=f.id, theme_id=t.id),
    )


@blueprint.route("/folder/<int:folder_id>/theme/<int:theme_id>/email_search_results/<int:page>")
@blueprint.route("/folder/<int:folder_id>/theme/<int:theme_id>/email_search_results")
@assert_folder_user()
def folder_theme_email_search_results(folder_id, theme_id, page=1):
    f: Folder = db.get_or_404(Folder, folder_id)
    t: Theme = db.get_or_404(Theme, theme_id)

    q = academic_search_query({
        'folder_id': f.id,
        'theme_id': t.id,
        'search': get_value_from_all_arguments('search_string') or '',
    })

    q = q.where(Academic.user_id != None)

    q = q.with_only_columns(AcademicPicker)

    results = db.paginate(select=q, page=page)

    return render_template(
        "ui/folder/email_academics_results.html",
        folder=f,
        theme=t,
        results=results,
    )


@blueprint.route("/folder/<int:folder_id>/theme/<int:theme_id>/email_lead", methods=['POST'])
def folder_email_theme_lead(folder_id, theme_id):
    f: Folder = db.get_or_404(Folder, folder_id)
    t: Theme = db.get_or_404(Theme, theme_id)

    academic_id: int = get_value_from_all_arguments('id')

    a: Academic = db.get_or_404(Academic, academic_id)

    email_theme_folder_publication_list.delay(
        # folder_id=f.id,
        # theme_id=t.id,
        # user_id=a.user_id,
        folder_id=99999,
        theme_id=t.id,
        user_id=a.user_id,
    )

    flash(f"Email sent to {a.user.email} for publications in the theme '{t.name}' for folder '{f.name}'")

    return refresh_response()


@blueprint.route("/folder/<int:folder_id>/theme/<int:theme_id>/email_authors", methods=['POST'])
def folder_email_authors(folder_id, theme_id):
    f: Folder = db.get_or_404(Folder, folder_id)
    t: Theme = db.get_or_404(Theme, theme_id)

    id: int = get_value_from_all_arguments('id')

    # TODO
    return refresh_response()
