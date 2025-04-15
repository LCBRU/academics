from collections import defaultdict
from datetime import datetime
from pathlib import Path
import shutil
import tempfile
from flask import render_template, request, send_file
from lbrc_flask.database import db
from lbrc_flask.export import excel_download, pdf_download
from lbrc_flask.lookups import NullObject
from weasyprint import HTML
from academics.model.academic import CatalogPublicationsSources, Source
from academics.model.folder import FolderDoi
from academics.model.publication import CatalogPublication, Publication
from academics.services.publication_searching import PublicationSearchForm, publication_search_query
from sqlalchemy.orm import selectinload
from werkzeug.utils import secure_filename
from .. import blueprint


@blueprint.route("/export/publications/xslt")
def publication_full_export_xlsx():
    # Use of dictionary instead of set to maintain order of headers
    headers = {
        'catalog': None,
        'catalog_identifier': None,
        'doi': None,
        'journal': None,
        'type': None,
        'volume': None,
        'issue': None,
        'pages': None,
        'publication_cover_date': None,
        'authors': None,
        'title': None,
        'abstract': None,
        'open access': None,
        'citations': None,
        'sponsor': None,
        'author_count': None,
        'brc_authors': None,
        'nihr acknowledgement': None,
    }

    search_form = PublicationSearchForm(formdata=request.args)

    q = publication_search_query(search_form)
    q = q.options(
        selectinload(Publication.catalog_publications)
        .selectinload(CatalogPublication.catalog_publication_sources)
        .selectinload(CatalogPublicationsSources.source)
    )
    q = q.options(
        selectinload(Publication.catalog_publications)
        .selectinload(CatalogPublication.sponsors)
    )
    q = q.options(
        selectinload(Publication.nihr_acknowledgement)
    )

    publication_details = ({
        'catalog': p.best_catalog_publication.catalog,
        'catalog_identifier': p.best_catalog_publication.catalog_identifier,
        'doi': p.doi,
        'journal': NullObject(p.best_catalog_publication.journal).name,
        'type': NullObject(p.best_catalog_publication.subtype).description,
        'volume': p.best_catalog_publication.volume,
        'issue': p.best_catalog_publication.issue,
        'pages': p.best_catalog_publication.pages,
        'publication_cover_date': p.best_catalog_publication.publication_cover_date,
        'title': p.best_catalog_publication.title,
        'abstract': p.best_catalog_publication.abstract,
        'open access': p.best_catalog_publication.is_open_access,
        'citations': p.best_catalog_publication.cited_by_count,
        'sponsor': '; '.join([s.name for s in p.best_catalog_publication.sponsors]),
        'author_count': len(p.best_catalog_publication.catalog_publication_sources),
        'brc_authors': '; '.join([f'{cps.source.display_name} ({cps.ordinal + 1})' for cps in p.best_catalog_publication.catalog_publication_sources if cps.source.academic is not None]),
        'nihr acknowledgement': '' if p.nihr_acknowledgement is None else p.nihr_acknowledgement.name,
    } for p in db.session.execute(q).scalars())

    return excel_download('Academics_Publications', headers.keys(), publication_details)


@blueprint.route("/export/publications/annual_report")
def publication_full_annual_report_xlsx():
    # Use of dictionary instead of set to maintain order of headers
    headers = {
        'Publication Reference': None,
        'DOI': None,
    }

    search_form = PublicationSearchForm(formdata=request.args)

    q = publication_search_query(search_form)

    q = q.with_only_columns(
        Publication.id,
        Publication.doi,
        Publication.vancouver,
    )

    publication_details = ({
        'Publication Reference': p.vancouver,
        'DOI': p.doi,
    } for p in db.session.execute(q).unique().mappings())

    return excel_download('Academics_Publications', headers.keys(), publication_details)


@blueprint.route("/export/publications/pdf")
def publication_export_pdf():
    search_form = PublicationSearchForm(formdata=request.args)
    
    q = publication_search_query(search_form)
    q = q.options(
        selectinload(Publication.catalog_publications)
        .selectinload(CatalogPublication.catalog_publication_sources)
        .selectinload(CatalogPublicationsSources.source)
        .selectinload(Source.academic)
    )
    q = q.options(
        selectinload(Publication.folder_dois)
        .selectinload(FolderDoi.folder)
    )

    publications = db.session.execute(q.order_by(CatalogPublication.publication_period_start)).unique().scalars()

    return pdf_download(
        'ui/exports/publication_export.html',
        publications=publications,
        parameters=search_form.values_description(),
    )


@blueprint.route("/export/publications/author_report/pdf")
def publication_author_report_pdf():
    search_form = PublicationSearchForm(formdata=request.args)
    
    q = publication_search_query(search_form)
    q = q.options(
        selectinload(Publication.catalog_publications)
        .selectinload(CatalogPublication.catalog_publication_sources)
        .selectinload(CatalogPublicationsSources.source)
        .selectinload(Source.academic)
    )

    publications = db.session.execute(q.order_by(CatalogPublication.publication_period_start)).unique().scalars()

    academics = defaultdict(set)

    for p in publications:
        for a in p.academics:
            academics[a].add(p)

    with tempfile.TemporaryDirectory() as tmpdirname:
        print('created temporary directory', tmpdirname)

        for a, pubs in academics.items():
            html = render_template(
                'ui/exports/publications_by_academic.html',
                publications=pubs,
                academic=a,
                parameters=search_form.values_description(),
            )
            weasy_html = HTML(string=html, base_url=tmpdirname)
            weasy_html.write_pdf(Path(tmpdirname) / secure_filename(a.full_name))

        with tempfile.NamedTemporaryFile(delete=False) as zipfilename:
            zipname = shutil.make_archive(zipfilename.name, 'zip', tmpdirname)
            return send_file(
                zipname,
                as_attachment=True,
                download_name=f'publication_author_report_{datetime.now():%Y%m%d_%H%M%S}.zip',
                )


