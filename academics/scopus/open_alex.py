import pyalex
from academics.config import Config
from pyalex import Authors, Works


def get_open_alex():
    config = Config()
    pyalex.config.email = config.OPEN_ALEX_EMAIL

    author = Authors().filter(orcid="https://orcid.org/0000-0002-5542-8448").get()[0]
    works = Works().filter(**{"author.id": author['id']}).filter(publication_year="2022").get()

    print(works[0])
