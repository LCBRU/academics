from random import choices, randint
import string
from academics.model.academic import Academic
from faker.providers import BaseProvider
from lbrc_flask.pytest.faker import FakeCreator, UserCreator as BaseUserCreator
from functools import cache
from academics.model.security import User
from academics.model.theme import Theme


class ThemeCreator(FakeCreator):
    def __init__(self):
        super().__init__(Theme)
        self.c = 0

    def get(self, **kwargs):
        self.c += 1

        name = self.faker.unique.word()

        result = self.cls(
            name = kwargs.get('name') or f"{name}_{self.c}",
        )

        return result


class ThemeProvider(BaseProvider):
    @cache
    def theme(self):
        return ThemeCreator()


class UserCreator(BaseUserCreator):
    def __init__(self):
        super().__init__(User)
        print('A'*10)
        self.faker.add_provider(ThemeProvider)
    
    def get(self, **kwargs):
        result = super().get(**kwargs)

        result.theme = self.faker.theme().get_value_or_get(kwargs, 'theme')

        return result


class UserProvider(BaseProvider):
    @cache
    def user(self):
        return UserCreator()


class AcademicFakeCreator(FakeCreator):
    def __init__(self):
        super().__init__(Academic)
        self.faker.add_provider(UserProvider)

    def get(self, **kwargs):
        has_left_brc = kwargs.get('has_left_brc') or False
        left_brc_date = kwargs.get('left_brc_date')

        if has_left_brc and left_brc_date is None:
            left_brc_date = self.faker.date()

        result = self.cls(
            first_name = kwargs.get('first_name') or self.faker.first_name(),
            last_name = kwargs.get('last_name') or self.faker.last_name(),
            initials = kwargs.get('initials') or ''.join(self.faker.random_letters(length=self.faker.random_int(min=0, max=3))),
            orcid = kwargs.get('orcid') or ''.join(choices(string.ascii_uppercase + string.digits, k=randint(10, 15))),
            google_scholar_id = kwargs.get('google_scholar_id') or ''.join(choices(string.ascii_uppercase + string.digits, k=randint(10, 15))),
            updating = kwargs.get('updating') or False,
            initialised = kwargs.get('initialised') or True,
            error = kwargs.get('error') or False,
            has_left_brc = has_left_brc,
            left_brc_date = left_brc_date,
            user = self.faker.user().get_value_or_get(kwargs, 'user'),
        )

        return result


class AcademicProvider(BaseProvider):
    @cache
    def academic(self):
        return AcademicFakeCreator()
