from datetime import datetime
from flask import render_template, request
from lbrc_flask.forms import SearchForm
from academics.model import Academic, ScopusAuthor, ScopusPublication, Theme
from academics.scopus.model import Author
from .. import blueprint
from sqlalchemy import or_
from wtforms import SelectField
from lbrc_flask.export import excel_download, pdf_download


def _get_author_choices():
    return [('', '')] + [(a.id, f'{a.full_name} ({a.affiliation_name})') for a in ScopusAuthor.query.order_by(ScopusAuthor.last_name, ScopusAuthor.first_name).all()]


class PublicationSearchForm(SearchForm):
    theme_id = SelectField('Theme', coerce=int)
    publication_period = SelectField('Publication Period', choices=[])
    author_id = SelectField('Author', choices=[])


    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.author_id.choices = _get_author_choices()

        this_year = datetime.now().year

        if datetime.now().month < 4:
            this_year -= 1
 
        self.publication_period.choices = [('', '')] + [(y, f'{y} - {y + 1}') for y in range(this_year, this_year - 20, -1)]
        self.theme_id.choices = [(0, '')] + [(t.id, t.name) for t in Theme.query.all()]


@blueprint.route("/publications/")
def publications():
    search_form = PublicationSearchForm(formdata=request.args)
    
    q = _get_publication_query(search_form)

    q = q.order_by(ScopusPublication.publication_cover_date.desc())

    publications = q.paginate(
        page=search_form.page.data,
        per_page=5,
        error_out=False,
    )

    return render_template(
        "ui/publications.html",
        search_form=search_form,
        publications=publications,
    )

def _get_publication_query(search_form):
    q = ScopusPublication.query

    if search_form.author_id.data:
        q = q.filter(ScopusPublication.scopus_authors.any(ScopusAuthor.id == search_form.author_id.data))

    if search_form.theme_id.data:
        aq = ScopusAuthor.query.with_entities(ScopusAuthor.id.distinct())
        aq = aq.join(ScopusAuthor.academic)
        aq = aq.filter(Academic.theme_id == search_form.theme_id.data)
        aq = aq.subquery()

        q = q.filter(ScopusPublication.scopus_authors.any(ScopusAuthor.id.in_(aq)))

    if search_form.publication_period.data:
        y = int(search_form.publication_period.data)
        start_date = datetime(y, 4, 1)
        end_date = datetime(y + 1, 3, 31)
        q = q.filter(ScopusPublication.publication_cover_date.between(start_date, end_date))

    if search_form.search.data:
        q = q.filter(or_(
            ScopusPublication.title.like(f'%{search_form.search.data}%'),
            ScopusPublication.publication.like(f'%{search_form.search.data}%'),
        ))
        
    return q


@blueprint.route("/publications/export/xslt")
def publication_export_xlsx():
    # Use of dictionary instead of set to maintain order of headers
    headers = {
        'scopus_id': None,
        'doi': None,
        'pubmed_id': None,
        'publication': None,
        'publication_cover_date': None,
        'authors': None,
        'title': None,
        'abstract': None,
    }

    search_form = PublicationSearchForm(formdata=request.args)
    
    q = _get_publication_query(search_form)

    q = q.order_by(ScopusPublication.publication_cover_date.desc())

    publication_details = ({
        'scopus_id': p.scopus_id,
        'doi': p.doi,
        'pubmed_id': p.pubmed_id,
        'publication': p.publication,
        'publication_cover_date': p.publication_cover_date,
        'authors': p.author_list,
        'title': p.title,
        'abstract': p.abstract,
    } for p in q.all())

    return excel_download('Academics_Publications', headers.keys(), publication_details)


@blueprint.route("/publications/export/pdf")
def publication_export_pdf():
    search_form = PublicationSearchForm(formdata=request.args)
    
    q = _get_publication_query(search_form)

    parameters = []

    if search_form.author_id.data:
        author = Author.query.get_or_404(search_form.author_id.data)
        parameters.append(('Author', author.full_name))

    if search_form.theme_id.data:
        theme = Theme.query.get_or_404(search_form.theme_id.data)
        parameters.append(('Theme', theme.name))

    if search_form.period.data:
        y = int(search_form.period.data)
        parameters.append(('Period', f'{y} - {y+1}'))

    publications = q.order_by(ScopusPublication.publication_cover_date.desc()).all()

    return pdf_download('ui/publications_pdf.html', title='Academics Publications', publications=publications, parameters=parameters)
