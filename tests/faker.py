from random import choices, randint
import string

from faker import Faker
from academics.model.academic import Academic
from faker.providers import BaseProvider
from lbrc_flask.pytest.faker import FakeCreator, UserCreator as BaseUserCreator
from functools import cache
from academics.model.folder import Folder
from academics.model.security import User
from academics.model.theme import Theme


class ThemeCreator(FakeCreator):
    @property
    def cls(self):
        return Theme
    
    def get(self, **kwargs):
        existing = self.count_in_db()

        name = self.faker.unique.word()

        result = self.cls(
            name = kwargs.get('name') or f"{name}_{existing}",
        )

        return result


class ThemeProvider(BaseProvider):
    __provider__ = 'ThemeProvider'.lower()

    @cache
    def theme(self):
        return ThemeCreator(self)


class FolderCreator(FakeCreator):
    @property
    def cls(self):
        return Folder
    
    def get(self, **kwargs):
        existing = self.count_in_db()

        name = self.faker.unique.word()

        result = self.cls(
            name = kwargs.get('name') or f"{name}_{existing}",
        )

        return result


class FolderProvider(BaseProvider):
    __provider__ = 'FolderProvider'.lower()

    @cache
    def folder(self):
        return FolderCreator(self)


class UserCreator(BaseUserCreator):
    @property
    def cls(self):
        return User
    
    def get(self, **kwargs):
        result = super().get(**kwargs)

        print('Theme count in user', self.faker.theme().count_in_db())
        result.theme = self.faker.theme().get_value_or_get(kwargs, 'theme')

        print('Theme in user', result.theme)

        if (folder := kwargs.get('folder')) is not None:
            result.folders.append(folder)

        print('Theme count in user after', self.faker.theme().count_in_db())

        return result


class UserProvider(BaseProvider):
    __provider__ = 'UserProvider'.lower()

    @cache
    def user(self):
        return UserCreator(self)


class AcademicFakeCreator(FakeCreator):
    @property
    def cls(self):
        return Academic
    
    def get(self, create_user=False, **kwargs):
        has_left_brc = kwargs.get('has_left_brc') or False
        left_brc_date = kwargs.get('left_brc_date')

        if has_left_brc and left_brc_date is None:
            left_brc_date = self.faker.date()
        
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


class AcademicProvider(BaseProvider):
    __provider__ = 'AcademicProvider'.lower()

    @cache
    def academic(self):
        return AcademicFakeCreator(self)