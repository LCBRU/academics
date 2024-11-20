from flask import current_app
from lbrc_flask.database import db
from lbrc_flask.celery import celery
from lbrc_flask.logging import log_exception
from lbrc_flask.emailing import email

from academics.model.folder import Folder
from academics.model.security import User
from academics.model.theme import Theme


@celery.task()
def email_theme_folder_publication_list(folder_id: int, theme_id: int, user_id: int):

    try:
        folder: Folder = db.session.get(Folder, folder_id)
        theme: Theme = db.session.get(Theme, theme_id)
        user: User = db.session.get(User, user_id)




        print('A'*100)
        
    except Exception as e:
        log_exception(e)
