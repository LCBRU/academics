from datetime import datetime
import logging
from flask import render_template, request
from lbrc_flask.forms import SearchForm
from academics.model import Academic, Keyword, ScopusAuthor, ScopusPublication, Theme
from .. import blueprint
from sqlalchemy import or_
from wtforms import SelectField, MonthField, SelectMultipleField
from lbrc_flask.export import excel_download, pdf_download
from lbrc_flask.validators import parse_date_or_none
from dateutil.relativedelta import relativedelta


def _get_author_choices():
    return [('', '')] + [(a.id, f'{a.full_name} ({a.affiliation_name})') for a in ScopusAuthor.query.order_by(ScopusAuthor.last_name, ScopusAuthor.first_name).all()]


def _get_keyword_choices():
    return [('', '')] + [(k.id, k.keyword.title()) for k in Keyword.query.order_by(Keyword.keyword).all()]


class PublicationSearchForm(SearchForm):
    theme_id = SelectField('Theme', coerce=int)
    publication_date_start = MonthField('Publication Start Date')
    publication_date_end = MonthField('Publication End Date')
    keywords = SelectMultipleField('Keywords')
    author_id = SelectField('Author')


    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.author_id.choices = _get_author_choices()
        self.theme_id.choices = [(0, '')] + [(t.id, t.name) for t in Theme.query.all()]
        self.keywords.choices = _get_keyword_choices()


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

    if search_form.keywords.data:

        for k in search_form.keywords.data:
            q = q.filter(ScopusPublication.keywords.any(Keyword.id == k))

    publication_start_date = parse_date_or_none(search_form.publication_date_start.data)
    if publication_start_date:
        q = q.filter(ScopusPublication.publication_cover_date >= publication_start_date)

    publication_end_date = parse_date_or_none(search_form.publication_date_end.data)
    if publication_end_date:
        q = q.filter(ScopusPublication.publication_cover_date < (publication_end_date + relativedelta(months=1)))

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
        author = ScopusAuthor.query.get_or_404(search_form.author_id.data)
        parameters.append(('Author', author.full_name))

    if search_form.theme_id.data:
        theme = Theme.query.get_or_404(search_form.theme_id.data)
        parameters.append(('Theme', theme.name))

    publication_start_date = parse_date_or_none(search_form.publication_date_start.data)
    if publication_start_date:
        parameters.append(('Start Publication Date', f'{publication_start_date:%b %Y}'))

    publication_end_date = parse_date_or_none(search_form.publication_date_end.data)
    if publication_end_date:
        parameters.append(('End Publication Date', f'{publication_end_date:%b %Y}'))

    publications = q.order_by(ScopusPublication.publication_cover_date.desc()).all()

    return pdf_download('ui/publications_pdf.html', title='Academics Publications', publications=publications, parameters=parameters)
