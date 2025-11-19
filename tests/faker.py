from random import choices, randint
import string
from functools import cache
from academics.model.academic import Academic
from faker.providers import BaseProvider
from lbrc_flask.pytest.faker import FakeCreator, UserCreator as BaseUserCreator
from academics.model.folder import Folder
from academics.model.security import User
from academics.model.theme import Theme


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
