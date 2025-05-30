from functools import wraps
from flask import abort
from flask_login import current_user
from lbrc_flask.requests import get_value_from_all_arguments
from lbrc_flask.database import db

from academics.model.folder import Folder
from academics.model.group import Group
from academics.services.folder import folder_author_users
from academics.services.folder_academics import folder_academics_search_query_with_folder_summary, is_current_user_a_folder_academic


def assert_folder_user():
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            folder_id = get_value_from_all_arguments('folder_id') or get_value_from_all_arguments('id')

            if folder_id:
                folder = db.get_or_404(Folder, folder_id)

                if current_user not in [folder.owner] + list(folder.shared_users):
                    if not is_current_user_a_folder_academic(folder):
                        abort(403)

            return f(*args, **kwargs)

        return decorated_function
    return decorator


def assert_folder_user_or_author():
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            folder_id = get_value_from_all_arguments('folder_id') or get_value_from_all_arguments('id')

            if folder_id:
                folder = db.get_or_404(Folder, folder_id)

                if folder.author_access == True:
                    fau = folder_author_users(folder)
                else:
                    fau = []

                if current_user not in [folder.owner] + list(folder.shared_users) + list(fau):
                    abort(403)

            return f(*args, **kwargs)

        return decorated_function
    return decorator


def assert_group_user():
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            group_id = get_value_from_all_arguments('group_id') or get_value_from_all_arguments('id')

            if group_id:
                group = db.get_or_404(Group, group_id)

                if current_user not in [group.owner] + list(group.shared_users):
                    abort(403)

            return f(*args, **kwargs)

        return decorated_function
    return decorator
