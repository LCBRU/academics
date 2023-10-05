from dataclasses import dataclass
import logging
from elsapy.elssearch import ElsSearch
from elsapy.elsprofile import ElsAuthor, ElsAffil
from academics.model import ScopusAuthor, Affiliation as AcaAffil
from elsapy.elsdoc import AbsDoc


@dataclass
class AuthorSearch():

    source_identifier: str
    first_name: str
    last_name: str
    affiliation_id: str
    affiliation_name: str
    existing : bool = False
    
    def __init__(self, data):
        self.source_identifier = data.get(u'dc:identifier', ':').split(':')[1]
        self.first_name = data.get(u'preferred-name', {}).get(u'given-name', '')
        self.last_name = data.get(u'preferred-name', {}).get(u'surname', '')
        self.affiliation_id = data.get(u'affiliation-current', {}).get(u'affiliation-id', '')
        self.affiliation_name = data.get(u'affiliation-current', {}).get(u'affiliation-name', '')

    @property
    def full_name(self):
        return ', '.join(
            filter(len, [
                self.first_name,
                self.last_name,
            ])
        )


class Author(ElsAuthor):
    def __init__(self, source_identifier):
        self.source_identifier = source_identifier
        super().__init__(author_id=self.source_identifier)

    @property
    def href(self):
        for h in  self.data.get(u'coredata', {}).get(u'link', ''):
            if h['@rel'] == 'scopus-author':
                return h['@href']

    @property
    def orcid(self):
        return self.data.get(u'coredata', {}).get(u'orcid', '')

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
            logging.info('Error reading Scopus data')
            return None
        
        if self.data is None:
            logging.info('No error reading Scopus data, but data is still None')
            return None

        if self.affiliation_id:
            self.affiliation = Affiliation(affiliation_id=self.affiliation_id)
            self.affiliation.read(client)
        else:
            self.affiliation = None

        return result

    def update_scopus_author(self, scopus_author):
        scopus_author.source_identifier = self.source_identifier
        scopus_author.orcid = self.orcid
        scopus_author.first_name = self.first_name
        scopus_author.last_name = self.last_name
        scopus_author.display_name = ' '.join(filter(self.first_name, self.last_name))

        scopus_author.citation_count = self.citation_count
        scopus_author.document_count = self.document_count
        scopus_author.h_index = self.h_index
        scopus_author.href = self.href

    def get_scopus_author(self):
        result = ScopusAuthor()
        self.update_scopus_author(result)
        return result


def get_affiliation(affiliation_id, client):
    result = Affiliation(affiliation_id=affiliation_id)
    if result.read(client):
        return result
    else:
        return None


class Affiliation(ElsAffil):
    def __init__(self, affiliation_id):
        self.affiliation_id = affiliation_id
        super().__init__(affil_id=affiliation_id)

    @property
    def name(self):
        return self.data.get(u'affiliation-name', '')

    @property
    def address(self):
        return ', '.join(filter(None, [self.data.get(u'address', ''), self.data.get(u'city', '')]))

    @property
    def country(self):
        return self.data.get(u'country', '')
    
    def get_academic_affiliation(self):
        return AcaAffil(
            catalog='scopus',
            catalog_identifier=self.affiliation_id,
            name=self.name,
            address=self.address,
            country=self.country,
        )


class Abstract(AbsDoc):
    def __init__(self, scopus_id):
        self.scopus_id = scopus_id
        super().__init__(scp_id=self.scopus_id)

    @property
    def funding_list(self):
        if not self.data:
            return set()

        result = set()

        funding_section = self.data.get('item', {}).get('xocs:meta', {}).get('xocs:funding-list', {}).get('xocs:funding', None)

        if type(funding_section) is list:

            for f in funding_section:
                if f.get('xocs:funding-agency-matched-string', None):
                    result.add(f.get('xocs:funding-agency-matched-string', None))
                if f.get('xocs:funding-agency', None):
                    result.add(f.get('xocs:funding-agency', None))

        elif type(funding_section) is dict:
            result.add(funding_section.get('xocs:funding-agency', None))

        return result

    @property
    def funding_text(self):
        if not self.data:
            return ''

        funding_text = self.data.get('item', {}).get('xocs:meta', {}).get('xocs:funding-list', {}).get('xocs:funding-text', '')

        if type(funding_text) is list:
            return '\n'.join([t.get('$', '') for t in funding_text])
        else:
            return funding_text

    def read(self, client):
        try:
            super().read(client)
            return True
        except Exception as e:
            logging.error(e)
            return False


class DocumentSearch(ElsSearch):
    def __init__(self, author):
        super().__init__(query=f'au-id({author.source_identifier})', index='scopus')
        self._uri += '&view=complete'