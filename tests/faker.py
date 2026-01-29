from datetime import datetime
from random import choice, choices, randint
import string
from functools import cache
from academics.model.academic import Academic, Affiliation, CatalogPublicationsSources, Source
from faker.providers import BaseProvider
from lbrc_flask.pytest.faker import FakeCreator, UserCreator as BaseUserCreator, FakeCreatorArgs
from academics.model.folder import Folder, FolderDoi
from academics.model.group import Group
from academics.model.institutions import Institution
from academics.model.publication import CatalogPublication, Journal, Keyword, NihrAcknowledgement, Publication, Sponsor, Subtype
from academics.model.security import User
from academics.model.theme import Theme
from academics.model.catalog import primary_catalogs
from academics.security import ROLE_EDITOR, ROLE_VALIDATOR


class ThemeCreator(FakeCreator):
    cls = Theme
    DEFAULT_VALUES = Theme.DEFAULT_VALUES
    
    def _create_item(self, save: bool, args: FakeCreatorArgs):
        return self.cls(
            name = args.get('name', self.faker.unique.word()),
        )


class GroupCreator(FakeCreator):
    cls = Group

    def _create_item(self, save: bool, args: FakeCreatorArgs):
        params = dict(
            name = args.get('name', self.faker.unique.word()),
        )

        if 'owner' in args:
            owner = args.get('owner')

            if owner.id is not None:
                params['owner_id'] = owner.id
            else:
                params['owner'] = owner
        elif 'owner_id' in args:
            params['owner_id'] = args.get('owner_id')
        else:
            params['owner'] = self.faker.user().get(save=save)

        if "shared_users" in args:
            params['shared_users'] = set(args.get('shared_users'))
        elif "shared_user_ids" in args:
            params['shared_users'] = set([self.faker.user().get_by_id(id) for id in args.get('shared_user_ids')])
        else:
            params['shared_users'] = set(self.faker.user().get_list(save=save, item_count=self.faker.random_int(min=1, max=3)))

        if "academics" in args:
            params['academics'] = set(args.get('academics'))
        elif "academic_ids" in args:
            params['academics'] = set([self.faker.academic().get_by_id(id) for id in args.get('academic_ids')])
        else:
            params['academics'] = set(self.faker.academic().get_list(save=save, item_count=self.faker.random_int(min=1, max=3)))

        return self.cls(**params)

    def assert_equal(self, expected: Group, actual: Group):
        assert expected.name == actual.name
        assert expected.owner_id == actual.owner_id
        # assert expected.academics == actual.academics
        # assert expected.shared_users == actual.shared_users


class FolderCreator(FakeCreator):
    cls = Folder

    def _create_item(self, save: bool, args: FakeCreatorArgs):
        params = dict(
            name = args.get('name', self.faker.unique.word()),
            description = args.get('description', self.faker.sentence(nb_words=6)),
            autofill_year = args.get('autofill_year', None),
            author_access = args.get('author_access', self.faker.random.choice([True, False])),
        )

        if 'owner' in args:
            owner = args.get('owner')

            if owner.id is not None:
                params['owner_id'] = owner.id
            else:
                params['owner'] = owner
        elif 'owner_id' in args:
            params['owner_id'] = args.get('owner_id')
        else:
            params['owner'] = self.faker.user().get(save=save)

        if "shared_users" in args:
            params['shared_users'] = set(args.get('shared_users'))
        elif "shared_user_ids" in args:
            params['shared_users'] = set([self.faker.user().get_by_id(id) for id in args.get('shared_user_ids')])
        else:
            params['shared_users'] = set(self.faker.user().get_list(save=save, item_count=self.faker.random_int(min=1, max=3)))

        return self.cls(**params)
    
    def assert_equal(self, expected: Folder, actual: Folder):
        assert expected.name == actual.name
        assert expected.description == actual.description
        assert expected.autofill_year == actual.autofill_year
        assert expected.owner_id == actual.owner_id


class FolderDoiCreator(FakeCreator):
    cls = FolderDoi
    
    def _create_item(self, save: bool, args: FakeCreatorArgs):
        print(f"Folder {args.get('folder')}")
        if "folder" in args:
            folder = args.get('folder')
        elif "folder_id" in args:
            folder = self.faker.folder().get_by_id(args.get('folder_id'))
        else:
            folder = self.faker.folder().get(save=save)
        
        print(f"DOI {args.get('doi')}")
        print(f"publication {args.get('publication')}")
        if 'doi' in args:
            doi = args.get('doi')
        elif "publication" in args:
            publication = args.get('publication')
            doi = publication.doi
        elif "publication_id" in args:
            publication = self.faker.publication().get_by_id(args.get('publication_id'))
            doi = publication.doi
        else:
            publication = self.faker.publication().get(save=save)
            doi = publication.doi

        return self.cls(
            folder = folder,
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
    
    def editor(self, save):
        return self.get(rolename=ROLE_EDITOR, save=save)

    def validator(self, save):
        return self.get(rolename=ROLE_VALIDATOR, save=save)


class AcademicFakeCreator(FakeCreator):
    cls = Academic
    
    def _create_item(self, save: bool, args: FakeCreatorArgs):
        has_left_brc = args.get('has_left_brc', (randint(1, 10) >= 9))
        left_brc_date = args.get('left_brc_date')

        if has_left_brc and left_brc_date is None:
            left_brc_date = datetime.strptime(self.faker.date(), '%Y-%m-%d').date()
        
        params = {
            'first_name': args.get('first_name', self.faker.first_name()),
            'last_name': args.get('last_name', self.faker.last_name()),
            'initials': args.get('initials', ''.join(self.faker.random_letters(length=self.faker.random_int(min=0, max=3)))),
            'orcid': args.get('orcid', ''.join(choices(string.ascii_uppercase + string.digits, k=randint(10, 15)))),
            'google_scholar_id': args.get('google_scholar_id', ''.join(choices(string.ascii_uppercase + string.digits, k=randint(10, 15)))),
            'updating': args.get('updating', False),
            'initialised': args.get('initialised', True),
            'error': args.get('error', False),
            'has_left_brc': has_left_brc,
            'left_brc_date': left_brc_date,
        }

        if "user_id" in args:
            params['user_id'] = args.get('user_id')
        elif "user" in args:
            user = args.get('user')
            params['user'] = user
        elif (randint(1, 10) >= 9):
            user = self.faker.user().get(save=save)
            params['user'] = user

        result = self.cls(**params)

        if (theme := args.get('theme')) is not None:
            result.themes.append(theme)

        return result


class SourceFakeCreator(FakeCreator):
    cls = Source
    
    def _create_item(self, save: bool, args: FakeCreatorArgs):
        academic_id = args.get('academic_id')

        if (academic := args.get('academic')) is not None:
            academic_id = academic.id
        
        affiliations = args.get('affiliations', [self.faker.affiliation().get(save=save) for _ in range(randint(1, 3))])
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

        if 'auto_nihr_acknowledgement' in args:
            auto_nihr_acknowledgement = args.get('auto_nihr_acknowledgement')
        elif 'auto_nihr_acknowledgement_id' in args:
            auto_nihr_acknowledgement = self.faker.nihr_acknowledgement().get_by_id(args.get('auto_nihr_acknowledgement_id'))
        else:
            auto_nihr_acknowledgement = self.faker.nihr_acknowledgement().get(save=save)

        if 'nihr_acknowledgement' in args:
            nihr_acknowledgement = args.get('nihr_acknowledgement')
        elif 'nihr_acknowledgement_id' in args:
            nihr_acknowledgement = self.faker.nihr_acknowledgement().get_by_id(args.get('nihr_acknowledgement_id'))
        else:
            nihr_acknowledgement = self.faker.nihr_acknowledgement().get(save=save)

        strict_nihr_acknowledgement_match = args.get('strict_nihr_acknowledgement', self.faker.pyint())
        preprint = args.get('preprint', self.faker.random.choice([True, False]))

        if "institutions" in args:
            institutions = args.get('institutions')
        elif "institution_ids" in args:
            institutions = set([self.faker.institution().get_by_id(id) for id in args.get('institution_ids')])
        else:
            institutions = set(self.faker.institution().get_list(save=save, item_count=self.faker.random_int(min=1, max=3)))

        if "folders" in args:
            folders = set(args.get('folders'))
        elif "folder_ids" in args:
            folders = set(self.faker.folder().get_by_ids(args.get('folder_ids')))
        else:
            folders = set(self.faker.folder().get_list(save=save, item_count=self.faker.random_int(min=1, max=3)))

        if 'supplementary_authors' in args:
            supplementary_authors = args.get('supplementary_authors')
        elif 'supplementary_author_ids' in args:
            supplementary_authors = set([self.faker.academic().get_by_id(id) for id in args.get('supplementary_author_ids')])
        else:
            supplementary_authors = set(self.faker.academic().get_list(save=save, item_count=self.faker.random_int(min=0, max=2)))

        result = self.cls(
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
        )

        for folder in folders:
            self.faker.folder_doi().get(
                save=save,
                folder=folder,
                doi=result.doi,
            )
        
        for author in supplementary_authors:
            result.supplementary_authors.append(author)

        return result
    

class CatalogPublicationFakeCreator(FakeCreator):
    cls = CatalogPublication
    
    def _create_item(self, save: bool, args: FakeCreatorArgs):
        if 'publication' in args:
            publication = args.get('publication')
        elif 'publication_id' in args:
            publication = self.faker.publication().get_by_id(args.get('publication_id'))
        else:
            publication = self.faker.publication().get(save=save)

        if 'doi' in args:
            doi = args.get('doi')
        elif publication is not None:
            doi = publication.doi
        else:
            doi = self.faker.doi()

        publication_cover_date = args.get('publication_cover_date', self.faker.date_between(start_date='-2y', end_date='today'))
        publication_period_start = args.get('publication_period_start', publication_cover_date)
        publication_period_end = args.get('publication_period_end', publication_cover_date)

        if "journal" in args:
            journal = args.get('journal')
        elif "journal_id" in args:
            journal = self.faker.journal().get_by_id(args.get('journal_id'))
        else:
            journal = self.faker.journal().get(save=save)

        if "sponsors" in args:
            sponsors = set(args.get('sponsors'))
        elif "sponsor_ids" in args:
            sponsors = set([self.faker.sponsor().get_by_id(id) for id in args.get('sponsor_ids')])
        else:
            sponsors = set(self.faker.sponsor().get_list(save=save, item_count=self.faker.random_int(min=1, max=3)))

        if "keywords" in args:
            keywords = set(args.get('keywords'))
        elif "keyword_ids" in args:
            keywords = set([self.faker.keyword().get_by_id(id) for id in args.get('keyword_ids')])
        else:
            keywords = set(self.faker.keyword().get_list(save=save, item_count=self.faker.random_int(min=1, max=5)))

        result = self.cls(
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
            journal = journal,
            is_open_access = args.get('is_open_access', self.faker.random.choice([True, False])),
            sponsors=sponsors,
            keywords=set(keywords),
        )

        if "sources" in args:
            sources = args.get('sources')
        elif "source_ids" in args:
            sources = [self.faker.source().get_by_id(id) for id in args.get('sources_ids')]
        else:
            sources = self.faker.source().get_list(save=save, item_count=self.faker.random_int(min=1, max=5))

        for source in sources:
            result.catalog_publication_sources.append(
                CatalogPublicationsSources(
                    catalog_publication=result,
                    source=source,
                )
            )

        return result
    

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

    @cache
    def group(self):
        return GroupCreator(self)
