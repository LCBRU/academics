from lbrc_flask.security import init_roles, init_users

ROLE_VALIDATOR = 'validator'
ROLE_NEW_PUBLICATION_RECIPIENT = 'new publication recipient'
ROLE_EDITOR = 'editor'


def get_roles():
    return [
        ROLE_VALIDATOR,
        ROLE_NEW_PUBLICATION_RECIPIENT,
        ROLE_EDITOR,
    ]


def init_authorization():
    init_roles(get_roles())
    init_users()
