from dataclasses import dataclass
from elsapy.elsprofile import ElsAuthor, ElsAffil
from academics.model import ScopusAuthor

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
        return self.data.get(u'h-index', '')

    def read(self, client):
        result = super().read(client) and super().read_metrics(client)

        self.affiliation = Affiliation(affiliation_id=self.affiliation_id)
        self.affiliation.read(client)

        return result

    def get_scopus_author(self):
        return ScopusAuthor(
            scopus_id=self.scopus_id,
            eid=self.eid,
            first_name=self.first_name,
            last_name=self.last_name,
            affiliation_id=self.affiliation_id,
            affiliation_name=self.affiliation.name,
            affiliation_address=self.affiliation.address,
            affiliation_city=self.affiliation.city,
            affiliation_country=self.affiliation.country,
            citation_count=self.citation_count,
            document_count=self.document_count,
            h_index=self.h_index,
        )


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
