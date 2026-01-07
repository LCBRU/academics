from datetime import datetime
from random import choice, choices, randint
import string
from functools import cache
from academics.model.academic import Academic, Affiliation, Source
from faker.providers import BaseProvider
from lbrc_flask.pytest.faker import FakeCreator, UserCreator as BaseUserCreator
from academics.model.folder import Folder
from academics.model.security import User
from academics.model.theme import Theme
from academics.model.catalog import primary_catalogs


class ThemeCreator(FakeCreator):
    cls = Theme
    
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


class AcademicsProvider(BaseProvider):
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
    def affiliation(self):
        return AffiliationCreator(self)
    
    @cache
    def source(self):
        return SourceFakeCreator(self)
