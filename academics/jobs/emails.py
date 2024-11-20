from flask import current_app, render_template
from lbrc_flask.database import db
from lbrc_flask.celery import celery
from lbrc_flask.logging import log_exception
from lbrc_flask.emailing import email

from academics.model.folder import Folder
from academics.model.security import User
from academics.model.theme import Theme


@celery.task(
    bind=True,
    autoretry_for=(Exception,),
    max_retries=5,
    interval_start=5,
    interval_step=5,
    )
def email_theme_folder_publication_list(self, folder_id: int, theme_id: int, user_id: int):

    try:
        folder: Folder = db.session.get(Folder, folder_id)
        theme: Theme = db.session.get(Theme, theme_id)
        user: User = db.session.get(User, user_id)

        email(
            subject=f"Publications in folder '{folder.name.title()}'",
            message=render_template('email/email_theme_folder_publication_list/txt.txt', folder=folder, theme=theme),
            recipients=[user.email],
            html_template='email/email_theme_folder_publication_list/html.html',
            folder=folder,
            theme=theme,
        )

    except Exception as e:
        log_exception(e)
        raise e
