from academics.model import FundingAcr, Journal, Keyword, Sponsor, Subtype
from lbrc_flask.database import db


def _get_journal(journal_name):
    journal_name = (journal_name or '').lower().strip()

    if not journal_name:
        return None

    result = Journal.query.filter(Journal.name == journal_name).one_or_none()

    if not result:
        result = Journal(name=journal_name)
        db.session.add(result)

    return result


def _get_subtype(code, description):
    if not code:
        return None

    result = Subtype.query.filter(Subtype.code == code).one_or_none()

    if not result:
        result = Subtype(code=code, description=description)
        db.session.add(result)

    return result


def _get_sponsor(name):
    if not name:
        return None

    result = Sponsor.query.filter(Sponsor.name == name).one_or_none()

    if not result:
        result = Sponsor(name=name)
        db.session.add(result)

    return result


def _get_funding_acr(name):
    if not name:
        return None

    result = FundingAcr.query.filter(FundingAcr.name == name).one_or_none()

    if not result:
        result = FundingAcr(name=name)
        db.session.add(result)

    return result


def _add_keywords_to_publications(publication, keyword_list):
    publication.keywords.clear()

    for k in keyword_list.split('|'):
        keyword_word = k.strip().lower()

        if not keyword_word:
            continue

        keyword = Keyword.query.filter(Keyword.keyword == keyword_word).one_or_none()

        if not keyword:
            keyword = Keyword(keyword=keyword_word)
            db.session.add(keyword)
        
        publication.keywords.add(keyword)


def _add_sponsors_to_publications(publication, sponsor_names):
    publication.keywords.clear()

    for name in sponsor_names:
        if not name:
            continue

        sponsor = Sponsor.query.filter(Sponsor.name == name).one_or_none()

        if not sponsor:
            sponsor = Sponsor(name=name)
            db.session.add(sponsor)
        
        publication.sponsors.add(sponsor)
