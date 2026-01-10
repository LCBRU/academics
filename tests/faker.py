from datetime import datetime
from random import choice, choices, randint
import string
from functools import cache
from academics.model.academic import Academic, Affiliation, Source
from faker.providers import BaseProvider
from lbrc_flask.pytest.faker import FakeCreator, UserCreator as BaseUserCreator
from academics.model.folder import Folder, FolderDoi
from academics.model.institutions import Institution
from academics.model.publication import Journal, Keyword, NihrAcknowledgement, Publication, Sponsor, Subtype
from academics.model.security import User
from academics.model.theme import Theme
from academics.model.catalog import primary_catalogs


class ThemeCreator(FakeCreator):
    cls = Theme
    DEFAULT_VALUES = Theme.DEFAULT_VALUES
    
    def get(self, **kwargs):
        return self.cls(
            name = kwargs.get('name') or self.faker.unique.word(),
        )


class FolderCreator(FakeCreator):
    cls = Folder

    def get(self, **kwargs):
        return self.cls(
            name = kwargs.get('name') or self.faker.unique.word(),
        )


class FolderDoiCreator(FakeCreator):
    cls = FolderDoi
    
    def get(self, **kwargs):
        folder = self.faker.folder().get_from_source_or_id_or_new(
            source=kwargs,
            object_key='folder',
            id_key='folder_id',
        )
        
        if 'doi' in kwargs:
            doi = kwargs['doi']
        else:
            publication = self.faker.publication().get_from_source_or_id_or_new(
                source=kwargs,
                object_key='publication',
                id_key='publication_id',
            )
            doi = publication.doi

        return self.cls(
            folder_id = folder.id,
            doi = doi,
        )


class AffiliationCreator(FakeCreator):
    cls = Affiliation
    
    def get(self, **kwargs):
        return self.cls(
            catalog = kwargs.get('catalog') or choice(primary_catalogs),
            catalog_identifier = kwargs.get('catalog_identifier') or self.faker.unique.pystr(min_chars=5, max_chars=20),
            name = kwargs.get('name') or self.faker.company(),
            address = kwargs.get('address') or self.faker.address(),
            country = kwargs.get('country') or self.faker.country(),
            refresh_details = kwargs.get('refresh_details', False),
            home_organisation = kwargs.get('home_organisation', False),
            international = kwargs.get('international', False),
            industry = kwargs.get('industry', False),
        )


class UserCreator(BaseUserCreator):
    cls = User
    
    def get(self, **kwargs):
        result = super().get(**kwargs)

        result.theme = self.faker.theme().get_value_or_get(kwargs, 'theme')

        if (folder := kwargs.get('folder')) is not None:
            result.folders.append(folder)

        return result


class AcademicFakeCreator(FakeCreator):
    cls = Academic
    
    def get(self, create_user=False, **kwargs):
        has_left_brc = kwargs.get('has_left_brc') or False
        left_brc_date = kwargs.get('left_brc_date')

        if has_left_brc and left_brc_date is None:
            left_brc_date = datetime.strptime(self.faker.date(), '%Y-%m-%d').date()
        
        user_id = kwargs.get('user_id')

        if create_user:
            user = self.faker.user().get(**kwargs)

        if (user := kwargs.get('user')) is not None:
            user_id = user.id

        result = self.cls(
            first_name = kwargs.get('first_name') or self.faker.first_name(),
            last_name = kwargs.get('last_name') or self.faker.last_name(),
            initials = kwargs.get('initials') or ''.join(self.faker.random_letters(length=self.faker.random_int(min=0, max=3))),
            orcid = kwargs.get('orcid') or ''.join(choices(string.ascii_uppercase + string.digits, k=randint(10, 15))),
            google_scholar_id = kwargs.get('google_scholar_id') or ''.join(choices(string.ascii_uppercase + string.digits, k=randint(10, 15))),
            updating = self.get_value_or_default(kwargs, 'updating', False),
            initialised = self.get_value_or_default(kwargs, 'initialised', True),
            error = self.get_value_or_default(kwargs, 'error', False),
            has_left_brc = has_left_brc,
            left_brc_date = left_brc_date,
            user = user,
            user_id = user_id
        )

        if (theme := kwargs.get('theme')) is not None:
            result.themes.append(theme)

        return result


class SourceFakeCreator(FakeCreator):
    cls = Source
    
    def get(self, **kwargs):
        academic_id = kwargs.get('academic_id')

        if (academic := kwargs.get('academic')) is not None:
            academic_id = academic.id
        
        if (affiliations := kwargs.get('affiliations')) is None:
            affiliations = [self.faker.affiliation().get() for _ in range(randint(1, 3))]

        first_name = kwargs.get('first_name') or self.faker.first_name()
        initials = kwargs.get('initials') or ''.join(self.faker.random_letters(length=self.faker.random_int(min=0, max=3)))
        last_name = kwargs.get('last_name') or self.faker.last_name()
        display_name = kwargs.get('display_name') or ' '.join(filter(None, [first_name, initials, last_name]))


        result = self.cls(
            catalog = kwargs.get('catalog') or choice(primary_catalogs),
            catalog_identifier = kwargs.get('catalog_identifier') or self.faker.unique.pystr(min_chars=5, max_chars=20),
            academic_id = academic_id,
            academic = academic,
            affiliations = affiliations,
            first_name = first_name,
            last_name = last_name,
            initials = initials,
            display_name = display_name,
            href = kwargs.get('href') or self.faker.url(),
            orcid = kwargs.get('orcid') or self.faker.unique.orcid(),
            citation_count = kwargs.get('citation_count') or self.faker.random_int(min=0, max=10000),
            document_count = kwargs.get('document_count') or self.faker.random_int(min=0, max=500),
            h_index = kwargs.get('h_index') or self.faker.random_int(min=0, max=100),
            last_fetched_datetime = kwargs.get('last_fetched_datetime') or self.faker.date_time(),
            error = self.get_value_or_default(kwargs, 'error', False),
        )

        return result


class PublicationFakeCreator(FakeCreator):
    cls = Publication
    
    def get(self, **kwargs):
        validation_historic = self.get_value_or_default(kwargs, 'validation_historic', self.faker.random.choice([True, False]))
        not_brc = self.get_value_or_default(kwargs, 'not_brc', self.faker.random.choice([True, False]))
        doi = self.get_value_or_default(kwargs, 'doi', self.faker.doi())
        vancouver = self.get_value_or_default(kwargs, 'vancouver', f"{self.faker.last_name()}, {self.faker.first_name()[0]}. Sample Publication Title. Journal Name. {self.faker.year()};{self.faker.random_int(min=1, max=100)}({self.faker.random_int(min=1, max=12)}):{self.faker.random_int(min=1, max=500)}-{self.faker.random_int(min=501, max=1000)}.")
        refresh_full_details = self.get_value_or_default(kwargs, 'refresh_full_details', self.faker.random.choice([True, False]))
        auto_nihr_acknowledgement = self.faker.nihr_acknowledgement().get_from_source_or_id_or_new(
            source=kwargs,
            object_key='auto_nihr_acknowledgement',
            id_key='auto_nihr_acknowledgement_id',
        )
        nihr_acknowledgement = self.faker.nihr_acknowledgement().get_from_source_or_id_or_new(
            source=kwargs,
            object_key='nihr_acknowledgement',
            id_key='nihr_acknowledgement_id',
        )
        strict_nihr_acknowledgement_match = self.get_value_or_default(kwargs, 'strict_nihr_acknowledgement', self.faker.pyint())
        preprint = self.get_value_or_default(kwargs, 'preprint', self.faker.random.choice([True, False]))
        institutions = set(self.faker.institution().get_list_from_source_or_ids_or_new(
            source=kwargs,
            objects_key='institutions',
            ids_key='institution_ids',
            count=self.faker.random_int(min=1, max=3),
        ))
        # folders = self.faker.folder().get_list_from_source_or_ids_or_new(
        #     source=kwargs,
        #     objects_key='folders',
        #     ids_key='folder_ids',
        #     count=self.faker.random_int(min=1, max=3),
        # )

        return self.cls(
            doi = doi,
            vancouver = vancouver,
            validation_historic = validation_historic,
            not_brc = not_brc,
            refresh_full_details = refresh_full_details,
            auto_nihr_acknowledgement = auto_nihr_acknowledgement,
            nihr_acknowledgement = nihr_acknowledgement,
            strict_nihr_acknowledgement_match = strict_nihr_acknowledgement_match,
            preprint = preprint,
            institutions = institutions,
            # folders = folders,
        )
    

class CatalogPublicationFakeCreator(FakeCreator):
    cls = Publication
    
    def get(self, **kwargs):
        publication = self.faker.publication().get_from_source_or_id_or_new(
            source=kwargs,
            object_key='publication',
            id_key='publication_id',
        )

        if 'doi' in kwargs:
            doi = kwargs['doi']
        elif publication is not None:
            doi = publication.doi
        else:
            doi = self.faker.doi()

        publication_cover_date = self.get_value_or_default(kwargs, 'publication_cover_date', self.faker.date_between(start_date='-2y', end_date='today'))
        publication_period_start = self.get_value_or_default(kwargs, 'publication_period_start', publication_cover_date)
        publication_period_end = self.get_value_or_default(kwargs, 'publication_period_end', publication_cover_date)

        return self.cls(
            publication = publication,
            refresh_full_details = self.get_value_or_default(kwargs, 'refresh_full_details', self.faker.random.choice([True, False])),
            catalog = kwargs.get('catalog') or choice(primary_catalogs),
            catalog_identifier = kwargs.get('catalog_identifier') or self.faker.unique.pystr(min_chars=5, max_chars=20),
            doi = doi,
            title = kwargs.get('title') or self.faker.sentence(nb_words=6),
            publication_cover_date = publication_cover_date,
            publication_period_start = publication_period_start,
            publication_period_end = publication_period_end,
            subtype = self.get_value_or_default(kwargs, 'subtype', self.faker.subtype().choice_from_db()),
            abstract = self.get_value_or_default(kwargs, 'abstract', self.faker.paragraph(nb_sentences=5)),
            volume = self.get_value_or_default(kwargs, 'volume', self.faker.random_int(min=1, max=12)),
            issue = self.get_value_or_default(kwargs, 'issue', self.faker.random_int(min=1, max=30)),
            pages = self.get_value_or_default(kwargs, 'pages', f'p{self.faker.random_int(min=1, max=100)}'),
            funding_text = self.get_value_or_default(kwargs, 'funding_text', self.faker.paragraph(nb_sentences=3)),
            href = self.get_value_or_default(kwargs, 'href', self.faker.uri()),
            journal = self.faker.journal().get_from_source_or_id_or_new(
                source=kwargs,
                object_key='journal',
                id_key='journal_id',
            ),
            is_open_access = self.get_value_or_default(kwargs, 'is_open_access', self.faker.random.choice([True, False])),
            sponsors=set(self.faker.sponsor().get_list_from_source_or_ids_or_new(
                source=kwargs,
                objects_key='sponsors',
                ids_key='sponsor_ids',
                count=self.faker.random_int(min=1, max=3),
            )),
            keywords=set(self.faker.keyword().get_list_from_source_or_ids_or_new(
                source=kwargs,
                objects_key='keywords',
                ids_key='keyword_ids',
                count=self.faker.random_int(min=1, max=5),
            )),
            catalog_publication_sources=self.faker.source().get_list_from_source_or_ids_or_new(
                source=kwargs,
                objects_key='catalog_publication_sources',
                ids_key='catalog_publication_source_ids',
                count=self.faker.random_int(min=1, max=5),
            ),
        )
    

class NihrAcknowledgementFakeCreator(FakeCreator):
    cls = NihrAcknowledgement
    DEFAULT_VALUES = NihrAcknowledgement.DEFAULT_VALUES

    def get(self, **kwargs):
        return self.cls(
            name = self.get_value_or_default(kwargs, 'name', self.faker.unique.word()),
            acknowledged = self.get_value_or_default(kwargs, 'acknowledged', self.faker.boolean()),
            colour = self.get_value_or_default(kwargs, 'colour', self.faker.hex_color()),
        )


class SubtypeFakeCreator(FakeCreator):
    cls = Subtype
    DEFAULT_VALUES = Subtype.DEFAULT_VALUES

    def get(self, **kwargs):
        return self.cls(
            code = self.get_value_or_default(kwargs, 'code', self.faker.unique.word()),
            description = self.get_value_or_default(kwargs, 'description', self.faker.unique.sentence(nb_words=3)),
        )
    

class JournalFakeCreator(FakeCreator):
    cls = Journal
    
    def get(self, **kwargs):
        return self.cls(
            name = kwargs.get('name') or self.faker.unique.company(),
            preprint = kwargs.get('preprint', self.faker.random.choice([True, False])),
        )


class SponsorFakeCreator(FakeCreator):
    cls = Sponsor

    def get(self, **kwargs):
        return self.cls(
            name = self.get_value_or_default(kwargs, 'name', self.faker.unique.company()),
        )   


class KeywordFakeCreator(FakeCreator):
    cls = Keyword
    
    def get(self, **kwargs):
        return self.cls(
            keyword = kwargs.get('keyword') or self.faker.unique.word(),
        )


class InstitutionFakeCreator(FakeCreator):
    cls = Institution
    
    def get(self, **kwargs):
        return self.cls(
            catalog = kwargs.get('catalog') or choice(primary_catalogs),
            catalog_identifier = kwargs.get('catalog_identifier') or self.faker.unique.pystr(min_chars=5, max_chars=20),
            name = kwargs.get('name') or self.faker.company(),
            country_code = kwargs.get('country_code') or self.faker.country_code(),
            sector = kwargs.get('sector') or self.faker.word(),
            refresh_full_details = kwargs.get('refresh_full_details', False),
            home_institution = kwargs.get('home_institution', False),
        )


class AcademicsProvider(BaseProvider):
    @cache
    def nihr_acknowledgement(self):
        return NihrAcknowledgementFakeCreator(self)

    @cache
    def academic(self):
        return AcademicFakeCreator(self)

    @cache
    def theme(self):
        return ThemeCreator(self)

    @cache
    def user(self):
        return UserCreator(self)

    @cache
    def folder(self):
        return FolderCreator(self)
    
    @cache
    def folder_doi(self):
        return FolderDoiCreator(self)

    @cache
    def affiliation(self):
        return AffiliationCreator(self)
    
    @cache
    def source(self):
        return SourceFakeCreator(self)

    @cache
    def publication(self):
        return PublicationFakeCreator(self)

    @cache
    def subtype(self):
        return SubtypeFakeCreator(self)

    @cache
    def journal(self):
        return JournalFakeCreator(self)

    @cache
    def sponsor(self):
        return SponsorFakeCreator(self)

    @cache
    def keyword(self):
        return KeywordFakeCreator(self)

    @cache
    def catalog_publication(self):
        return CatalogPublicationFakeCreator(self)
    
    @cache
    def institution(self):
        return InstitutionFakeCreator(self)

