from dataclasses import dataclass

@dataclass
class ScopusAuthor():

    scopus_id: str
    eid: str
    first_name: str
    last_name: str
    affiliation_id: str
    affiliation_name: str
    affiliation_city: str
    affiliation_country: str
    
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
                self.affiliation_name,
                self.affiliation_city,
                self.affiliation_country,
            ])
        )