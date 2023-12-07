import pyalex
import logging

from datetime import date
from sqlalchemy import select
from academics.catalogs.utils import AuthorData, PublicationData
from academics.config import Config
from pyalex import Authors, Works, Institutions
from itertools import chain
from flask import current_app
from lbrc_flask.database import db
from academics.model import CATALOG_OPEN_ALEX, DOI_URL, ORCID_URL, Academic, Source
from lbrc_flask.validators import parse_date


def get_open_alex():
    config = Config()
    pyalex.config.email = config.OPEN_ALEX_EMAIL

    q = Authors().search_filter(display_name="samani").get()
    a = next(iter(q))

    pubs = get_openalex_publications(a['id'])

    print(pubs)


def get_openalex_publications(identifier):
    logging.info('get_openalex_publications: started')

    pyalex.config.email = current_app.config['OPEN_ALEX_EMAIL']

    if not current_app.config['OPEN_ALEX_ENABLED']:
        print(current_app.config['OPEN_ALEX_ENABLED'])
        logging.info('OpenAlex Not Enabled')
        return []
    
    return [
        _get_publication_data(w)
        for w in Works()
            .filter(**{"author.id": identifier})
            .filter(publication_year=f'{date.today().year - 1}')
            .get()
    ]


def _get_publication_data(pubdata):
    pd = _diction_purge_none(pubdata)
    bib = pd.get('biblio', {})
    grants = pd.get('grants', [])

    return PublicationData(
        catalog=CATALOG_OPEN_ALEX,
        catalog_identifier=_get_id_from_href(pd['id']),
        href=pd['id'],
        doi=_get_doi_from_href(pd.get('doi', None)),
        title=pd.get('title', None),
        journal_name=pd.get('primary_location', {}).get('source', {}).get('display_name', ''),
        publication_cover_date=parse_date(pd.get('publication_date', None)),
        abstract_text=abstract_from_inverted_index(pd.get('abstract_inverted_index', None)),
        funding_list={g.get('funder_display_name', None) for g in grants},
        funding_text='',
        volume=bib.get('volume', ''),
        issue=bib.get('issue', ''),
        pages='-'.join(filter(None, [bib.get('first_page'), bib.get('last_page')])),
        subtype_code='',
        subtype_description=pd.get('type', None),
        cited_by_count=pd.get('cited_by_count', None),
        author_list='',
        authors=[_translate_publication_author(a) for a in pd.get('authorships', [])],
        keywords={k.get('keyword', None) for k in pd.get('keywords', {})},
        is_open_access=pd.get('open_access', {}).get('is_oa', False),
    )


def _diction_purge_none(_dict):
    """Delete None values recursively from all of the dictionaries"""
    for key, value in list(_dict.items()):
        if isinstance(value, dict):
            _diction_purge_none(value)
        elif value is None:
            del _dict[key]
        elif isinstance(value, list):
            for v_i in value:
                if isinstance(v_i, dict):
                    _diction_purge_none(v_i)

    return _dict


def _translate_publication_author(author_dict):
    affiliation = next(iter(author_dict.get('institutions', [])), {})
    author = author_dict.get('author', {})

    if _get_id_from_href(author.get('id', None)) == 'A5027073118':
        print('v'*40)
        print(author_dict)
        print('^'*40)


    return AuthorData(
        catalog=CATALOG_OPEN_ALEX,
        catalog_identifier=_get_id_from_href(author.get('id', None)),
        orcid=_get_orcid_from_href(author.get('orcid', None)),
        first_name='',
        last_name='',
        initials='',
        author_name=author_dict.get('display_name', None),
        href=author_dict.get('id', None),
        affiliation_identifier=_get_id_from_href(affiliation.get('id', None)),
        affiliation_name=affiliation.get('display_name', None),
        affiliation_address='',
        affiliation_country=affiliation.get('country_code', None),
    )


def open_alex_similar_authors(academic: Academic):
    if not current_app.config['OPEN_ALEX_ENABLED']:
        print(current_app.config['OPEN_ALEX_ENABLED'])
        logging.info('OpenAlex Not Enabled')
        return []

    logging.info(f'Getting OpenAlex data for {academic.full_name}')

    existing = set(db.session.execute(
        select(Source.catalog_identifier).
        where(Source.catalog == CATALOG_OPEN_ALEX)
    ).scalars())

    authors = {}

    for o in academic.all_orcids():
        authors.update({
            _get_id_from_href(a.get('id', '')): a
            for a in _get_for_orcid(o)
        })
    for s in academic.all_scopus_ids():
        authors.update({
            _get_id_from_href(a.get('id', '')): a
            for a in _get_for_scopus_id(s)
        })
    authors.update({
        _get_id_from_href(a.get('id', '')): a
        for a in _get_for_name(academic.full_name)
    })

    new_authors = [a for a in authors.values() if _get_id_from_href(a.get('id', '')) not in existing]

    return _get_author_datas(new_authors)


def abstract_from_inverted_index(inverted_index):
    words = {}

    for w, indices in (inverted_index or {}).items():
        for i in indices:
            words[i] = w

    return ' '.join([w[1] for w in sorted(words.items(), key=lambda w: w[0])])


def get_open_alex_author_data(identifier):
    if not current_app.config['OPEN_ALEX_ENABLED']:
        print(current_app.config['OPEN_ALEX_ENABLED'])
        logging.info('OpenAlex Not Enabled')
        return None

    author = Authors()[identifier]

    results = _get_author_datas([author])

    return next(iter(results), None)


def _get_author_datas(authors):
    result = []

    for a in authors:
        institution_id = _get_id_from_href((a.get('last_known_institution') or {}).get('id', ''))

        if institution_id:
            i = Institutions()[institution_id]
        else:
            i = {}

        result.append(
            AuthorData(
                catalog=CATALOG_OPEN_ALEX,
                catalog_identifier=_get_id_from_href(a.get('id', '')),
                orcid=_get_id_from_href(a.get('orcid', None)),
                first_name='',
                last_name='',
                initials='',
                author_name=a.get('display_name', ''),
                href=a.get('id', ''),
                affiliation_identifier=institution_id,
                affiliation_name=i.get('display_name', ''),
                affiliation_address=i.get('geo', {}).get('city', ''),
                affiliation_country=i.get('geo', {}).get('country', ''),
                citation_count=a.get('cited_by_count', None),
                document_count=a.get('works_count', None),
                h_index=a.get('summary_stats', {}).get('h_index', None),
            )
        )

    return result



def _get_id_from_href(href):
    if not href:
        return None
    
    if not '/' in href:
        return href
    
    _, result = href.rsplit('/', 1)
    return result


def _get_orcid_from_href(href):
    if not href:
        return None

    parts = href.partition(ORCID_URL)

    rparts = list(reversed(parts))
    fparts = filter(len, rparts)

    return next(iter(fparts)).strip('/')


def _get_doi_from_href(href):
    if not href:
        return None

    parts = href.partition(DOI_URL)

    rparts = list(reversed(parts))
    fparts = filter(len, rparts)

    return next(iter(fparts)).strip('/')


def _get_for_orcid(orcid):
    logging.info(f'Getting OpenAlex authors for ORCID: {orcid}')

    q = Authors().filter(orcid=orcid)
    return chain(*q.paginate(per_page=200))


def _get_for_scopus_id(scopus_id):
    logging.info(f'Getting OpenAlex authors for SCOPUS ID: {scopus_id}')

    q = Authors().filter(scopus=scopus_id)
    return chain(*q.paginate(per_page=200))


def _get_for_name(name):
    logging.info(f'Getting OpenAlex authors for name: {name}')

    q = Authors().search_filter(display_name=name)
    return chain(*q.paginate(per_page=200))
