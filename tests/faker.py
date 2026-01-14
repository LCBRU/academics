from datetime import datetime
from random import choice, choices, randint
import string
from functools import cache
from academics.model.academic import Academic, Affiliation, Source
from faker.providers import BaseProvider
from lbrc_flask.pytest.faker import FakeCreator, UserCreator as BaseUserCreator, FakeCreatorArgs
from academics.model.folder import Folder, FolderDoi
from academics.model.institutions import Institution
from academics.model.publication import Journal, Keyword, NihrAcknowledgement, Publication, Sponsor, Subtype
from academics.model.security import User
from academics.model.theme import Theme
from academics.model.catalog import primary_catalogs
from academics.security import ROLE_EDITOR


class ThemeCreator(FakeCreator):
    cls = Theme
    DEFAULT_VALUES = Theme.DEFAULT_VALUES
    
    def _create_item(self, save: bool, args: FakeCreatorArgs):
        return self.cls(
            name = args.get('name', self.faker.unique.word()),
        )


class FolderCreator(FakeCreator):
    cls = Folder

    def _create_item(self, save: bool, args: FakeCreatorArgs):
        return self.cls(
            name = args.get('name', self.faker.unique.word()),
        )


class FolderDoiCreator(FakeCreator):
    cls = FolderDoi
    
    def _create_item(self, save: bool, args: FakeCreatorArgs):
        folder = self.faker.folder().get_from_source_or_id_or_new(
            source=args.arguments,
            object_key='folder',
            id_key='folder_id',
        )
        
        if 'doi' in args.arguments:
            doi = args.arguments['doi']
        else:
            publication = self.faker.publication().get_from_source_or_id_or_new(
                source=args.arguments,
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
    
    def _create_item(self, save: bool, args: FakeCreatorArgs):
        return self.cls(
            catalog = args.get('catalog', choice(primary_catalogs)),
            catalog_identifier = args.get('catalog_identifier', self.faker.unique.pystr(min_chars=5, max_chars=20)),
            name = args.get('name', self.faker.company()),
            address = args.get('address', self.faker.address()),
            country = args.get('country', self.faker.country()),
            refresh_details = args.get('refresh_details', False),
            home_organisation = args.get('home_organisation', False),
            international = args.get('international', False),
            industry = args.get('industry', False),
        )


class UserCreator(BaseUserCreator):
    cls = User
    
    def _create_item(self, save: bool, args: FakeCreatorArgs):
        result = super()._create_item(save=save, args=args)

        result.theme = args.get('theme', self.faker.theme().get(save=save))

        if (folder := args.get('folder')) is not None:
            result.folders.append(folder)

        return result
    
    def editor(self):
        return self.get(rolename=ROLE_EDITOR, save=True)


class AcademicFakeCreator(FakeCreator):
    cls = Academic
    
    def _create_item(self, save: bool, args: FakeCreatorArgs):
        has_left_brc = args.get('has_left_brc', False)
        left_brc_date = args.get('left_brc_date')

        if has_left_brc and left_brc_date is None:
            left_brc_date = datetime.strptime(self.faker.date(), '%Y-%m-%d').date()
        
        user_id = args.get('user_id')

        if (args.get('create_user', False) == True):
            user = self.faker.user().get(save=save)

        if (user := args.get('user')) is not None:
            user_id = user.id

        result = self.cls(
            first_name = args.get('first_name', self.faker.first_name()),
            last_name = args.get('last_name', self.faker.last_name()),
            initials = args.get('initials', ''.join(self.faker.random_letters(length=self.faker.random_int(min=0, max=3)))),
            orcid = args.get('orcid', ''.join(choices(string.ascii_uppercase + string.digits, k=randint(10, 15)))),
            google_scholar_id = args.get('google_scholar_id', ''.join(choices(string.ascii_uppercase + string.digits, k=randint(10, 15)))),
            # here
            updating = args.get('updating', False),
            initialised = args.get('initialised', True),
            error = args.get('error', False),
            has_left_brc = has_left_brc,
            left_brc_date = left_brc_date,
            user = user,
            user_id = user_id
        )

        if (theme := args.get('theme')) is not None:
            result.themes.append(theme)

        return result


class SourceFakeCreator(FakeCreator):
    cls = Source
    
    def _create_item(self, save: bool, args: FakeCreatorArgs):
        academic_id = args.get('academic_id')

        if (academic := args.get('academic')) is not None:
            academic_id = academic.id
        
        affiliations = args.get('affiliations', [self.faker.affiliation().get() for _ in range(randint(1, 3))])
        first_name = args.get('first_name', self.faker.first_name())
        initials = args.get('initials', ''.join(self.faker.random_letters(length=self.faker.random_int(min=0, max=3))))
        last_name = args.get('last_name', self.faker.last_name())
        display_name = args.get('display_name', ' '.join(filter(None, [first_name, initials, last_name])))


        result = self.cls(
            catalog = args.get('catalog', choice(primary_catalogs)),
            catalog_identifier = args.get('catalog_identifier', self.faker.unique.pystr(min_chars=5, max_chars=20)),
            academic_id = academic_id,
            academic = academic,
            affiliations = affiliations,
            first_name = first_name,
            last_name = last_name,
            initials = initials,
            display_name = display_name,
            href = args.get('href', self.faker.url()),
            orcid = args.get('orcid', self.faker.unique.orcid()),
            citation_count = args.get('citation_count', self.faker.random_int(min=0, max=10000)),
            document_count = args.get('document_count', self.faker.random_int(min=0, max=500)),
            h_index = args.get('h_index', self.faker.random_int(min=0, max=100)),
            last_fetched_datetime = args.get('last_fetched_datetime', self.faker.date_time()),
            error = args.get('error', False),
        )

        return result


class PublicationFakeCreator(FakeCreator):
    cls = Publication
    
    def _create_item(self, save: bool, args: FakeCreatorArgs):
        validation_historic = args.get('validation_historic', self.faker.random.choice([True, False]))
        not_brc = args.get('not_brc', self.faker.random.choice([True, False]))
        doi = args.get('doi', self.faker.doi())
        vancouver = args.get('vancouver', f"{self.faker.last_name()}, {self.faker.first_name()[0]}. Sample Publication Title. Journal Name. {self.faker.year()};{self.faker.random_int(min=1, max=100)}({self.faker.random_int(min=1, max=12)}):{self.faker.random_int(min=1, max=500)}-{self.faker.random_int(min=501, max=1000)}.")
        refresh_full_details = args.get('refresh_full_details', self.faker.random.choice([True, False]))
        auto_nihr_acknowledgement = self.faker.nihr_acknowledgement().get_from_source_or_id_or_new(
            source=args.arguments,
            object_key='auto_nihr_acknowledgement',
            id_key='auto_nihr_acknowledgement_id',
        )
        nihr_acknowledgement = self.faker.nihr_acknowledgement().get_from_source_or_id_or_new(
            source=args.arguments,
            object_key='nihr_acknowledgement',
            id_key='nihr_acknowledgement_id',
        )
        strict_nihr_acknowledgement_match = args.get('strict_nihr_acknowledgement', self.faker.pyint())
        preprint = args.get('preprint', self.faker.random.choice([True, False]))
        institutions = set(self.faker.institution().get_list_from_source_or_ids_or_new(
            source=args.arguments,
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
    
    def _create_item(self, save: bool, args: FakeCreatorArgs):
        publication = self.faker.publication().get_from_source_or_id_or_new(
            source=args.arguments,
            object_key='publication',
            id_key='publication_id',
        )

        if 'doi' in args.arguments:
            doi = args.get('doi')
        elif publication is not None:
            doi = publication.doi
        else:
            doi = self.faker.doi()

        publication_cover_date = args.get('publication_cover_date', self.faker.date_between(start_date='-2y', end_date='today'))
        publication_period_start = args.get('publication_period_start', publication_cover_date)
        publication_period_end = args.get('publication_period_end', publication_cover_date)

        return self.cls(
            publication = publication,
            refresh_full_details = args.get('refresh_full_details', self.faker.random.choice([True, False])),
            catalog = args.get('catalog', choice(primary_catalogs)),
            catalog_identifier = args.get('catalog_identifier', self.faker.unique.pystr(min_chars=5, max_chars=20)),
            doi = doi,
            title = args.get('title', self.faker.sentence(nb_words=6)),
            publication_cover_date = publication_cover_date,
            publication_period_start = publication_period_start,
            publication_period_end = publication_period_end,
            subtype = args.get('subtype', self.faker.subtype().choice_from_db()),
            abstract = args.get('abstract', self.faker.paragraph(nb_sentences=5)),
            volume = args.get('volume', self.faker.random_int(min=1, max=12)),
            issue = args.get('issue', self.faker.random_int(min=1, max=30)),
            pages = args.get('pages', f'p{self.faker.random_int(min=1, max=100)}'),
            funding_text = args.get('funding_text', self.faker.paragraph(nb_sentences=3)),
            href = args.get('href', self.faker.uri()),
            journal = self.faker.journal().get_from_source_or_id_or_new(
                source=args.arguments,
                object_key='journal',
                id_key='journal_id',
            ),
            is_open_access = args.get('is_open_access', self.faker.random.choice([True, False])),
            sponsors=set(self.faker.sponsor().get_list_from_source_or_ids_or_new(
                source=args.arguments,
                objects_key='sponsors',
                ids_key='sponsor_ids',
                count=self.faker.random_int(min=1, max=3),
            )),
            keywords=set(self.faker.keyword().get_list_from_source_or_ids_or_new(
                source=args.arguments,
                objects_key='keywords',
                ids_key='keyword_ids',
                count=self.faker.random_int(min=1, max=5),
            )),
            catalog_publication_sources=self.faker.source().get_list_from_source_or_ids_or_new(
                source=args.arguments,
                objects_key='catalog_publication_sources',
                ids_key='catalog_publication_source_ids',
                count=self.faker.random_int(min=1, max=5),
            ),
        )
    

class NihrAcknowledgementFakeCreator(FakeCreator):
    cls = NihrAcknowledgement
    DEFAULT_VALUES = NihrAcknowledgement.DEFAULT_VALUES

    def _create_item(self, save: bool, args: FakeCreatorArgs):
        return self.cls(
            name = args.get('name', self.faker.unique.word()),
            acknowledged = args.get('acknowledged', self.faker.boolean()),
            colour = args.get('colour', self.faker.hex_color()),
        )


class SubtypeFakeCreator(FakeCreator):
    cls = Subtype
    DEFAULT_VALUES = Subtype.DEFAULT_VALUES

    def _create_item(self, save: bool, args: FakeCreatorArgs):
        return self.cls(
            code = args.get('code', self.faker.unique.word()),
            description = args.get('description', self.faker.unique.sentence(nb_words=3)),
        )
    

class JournalFakeCreator(FakeCreator):
    cls = Journal
    
    def _create_item(self, save: bool, args: FakeCreatorArgs):
        return self.cls(
            name = args.get('name', self.faker.unique.company()),
            preprint = args.get('preprint', self.faker.random.choice([True, False])),
        )


class SponsorFakeCreator(FakeCreator):
    cls = Sponsor

    def _create_item(self, save: bool, args: FakeCreatorArgs):
        return self.cls(
            name = args.get('name', self.faker.unique.company()),
        )   


class KeywordFakeCreator(FakeCreator):
    cls = Keyword
    
    def _create_item(self, save: bool, args: FakeCreatorArgs):
        return self.cls(
            keyword = args.get('keyword', self.faker.unique.word()),
        )


class InstitutionFakeCreator(FakeCreator):
    cls = Institution
    
    def _create_item(self, save: bool, args: FakeCreatorArgs):
        return self.cls(
            catalog = args.get('catalog', choice(primary_catalogs)),
            catalog_identifier = args.get('catalog_identifier', self.faker.unique.pystr(min_chars=5, max_chars=20)),
            name = args.get('name', self.faker.company()),
            country_code = args.get('country_code', self.faker.country_code()),
            sector = args.get('sector', self.faker.word()),
            refresh_full_details = args.get('refresh_full_details', False),
            home_institution = args.get('home_institution', False),
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

