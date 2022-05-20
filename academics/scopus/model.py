from dataclasses import dataclass
import logging
from elsapy.elsprofile import ElsAuthor, ElsAffil
from academics.model import ScopusAuthor, ScopusPublication
from lbrc_flask.validators import parse_date
from elsapy.elsdoc import AbsDoc


@dataclass
class AuthorSearch():

    scopus_id: str
    eid: str
    first_name: str
    last_name: str
    affiliation_id: str
    affiliation_name: str
    affiliation_city: str
    affiliation_country: str
    existing : bool = False
    
    def __init__(self, data):
        self.scopus_id = data.get(u'dc:identifier', ':').split(':')[1]
        self.eid = data.get(u'eid', '')
        self.first_name = data.get(u'preferred-name', {}).get(u'given-name', '')
        self.last_name = data.get(u'preferred-name', {}).get(u'surname', '')
        self.affiliation_id = data.get(u'affiliation-current', {}).get(u'affiliation-id', '')
        self.affiliation_name = data.get(u'affiliation-current', {}).get(u'affiliation-name', '')
        self.affiliation_city = data.get(u'affiliation-current', {}).get(u'affiliation-city', '')
        self.affiliation_country = data.get(u'affiliation-current', {}).get(u'affiliation-country', '')

    @property
    def full_name(self):
        return ', '.join(
            filter(len, [
                self.first_name,
                self.last_name,
            ])
        )

    @property
    def affiliation_full_name(self):
        return ', '.join(
            filter(len, [
                self.affiliation_name or '',
                self.affiliation_city or '',
                self.affiliation_country or '',
            ])
        )


class Author(ElsAuthor):
    def __init__(self, scopus_id):
        self.scopus_id = scopus_id
        super().__init__(author_id=self.scopus_id)

    @property
    def href(self):
        for h in  self.data.get(u'coredata', {}).get(u'link', ''):
            if h['@rel'] == 'scopus-author':
                return h['@href']

    @property
    def orcid(self):
        return self.data.get(u'coredata', {}).get(u'orcid', '')

    @property
    def eid(self):
        return self.data.get(u'coredata', {}).get(u'eid', '')

    @property
    def citation_count(self):
        return self.data.get(u'coredata', {}).get(u'citation-count', '')

    @property
    def document_count(self):
        return self.data.get(u'coredata', {}).get(u'document-count', '')

    @property
    def affiliation_id(self):
        return self.data.get(u'affiliation-current', {}).get(u'@id', '')

    @property
    def h_index(self):
        return self.data.get(u'h-index', None)

    def read(self, client):
        try:
            result = super().read(client)
            super().read_metrics(client)
        except Exception:
            pass

        if self.affiliation_id:
            self.affiliation = Affiliation(affiliation_id=self.affiliation_id)
            self.affiliation.read(client)
        else:
            self.affiliation = None

        return result

    def update_scopus_author(self, scopus_author):
        scopus_author.scopus_id = self.scopus_id
        scopus_author.eid = self.eid
        scopus_author.orcid = self.orcid
        scopus_author.first_name = self.first_name
        scopus_author.last_name = self.last_name

        if self.affiliation:
            scopus_author.affiliation_id = self.affiliation_id
            scopus_author.affiliation_name = self.affiliation.name
            scopus_author.affiliation_address = self.affiliation.address
            scopus_author.affiliation_city = self.affiliation.city
            scopus_author.affiliation_country = self.affiliation.country

        scopus_author.citation_count = self.citation_count
        scopus_author.document_count = self.document_count
        scopus_author.h_index = self.h_index
        scopus_author.href = self.href

    def get_scopus_author(self):
        result = ScopusAuthor()
        self.update_scopus_author(result)
        return result

class Affiliation(ElsAffil):
    def __init__(self, affiliation_id):
        self.affiliation_id = affiliation_id
        super().__init__(affil_id=affiliation_id)

    @property
    def name(self):
        return self.data.get(u'affiliation-name', '')

    @property
    def address(self):
        return self.data.get(u'address', '')

    @property
    def city(self):
        return self.data.get(u'city', '')

    @property
    def country(self):
        return self.data.get(u'country', '')


class Abstract(AbsDoc):
    def __init__(self, scopus_id):
        self.scopus_id = scopus_id
        super().__init__(scp_id=self.scopus_id)

    @property
    def abstract(self):
        if self.data:
            return self.data.get('item', {}).get('bibrecord', {}).get('head', {}).get('abstracts', '')

    def read(self, client):
        try:
            super().read(client)
            return True
        except Exception as e:
            logging.error(e)
            return False
