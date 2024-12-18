from pathlib import Path
from flask import current_app, render_template
from lbrc_flask.database import db
from lbrc_flask.celery import celery
from lbrc_flask.logging import log_exception
from lbrc_flask.emailing import email

from academics.model.academic import Academic
from academics.model.folder import Folder
from academics.model.security import User
from academics.model.theme import Theme
from academics.services.academic_searching import academic_search_query
from flask_mail import Attachment


@celery.task(
    bind=True,
    autoretry_for=(Exception,),
    max_retries=2,
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
            attachements=[
                Path('static/pdf/Academics - Assess Publication Relevance to BRC Objectives.pdf'),
                Path('static/pdf/Academics - Logging In.pdf'),
            ]
        )

    except Exception as e:
        log_exception(e)
        raise e


@celery.task(
    bind=True,
    autoretry_for=(Exception,),
    max_retries=2,
    )
def email_theme_folder_academics_publication(self, folder_id: int, theme_id: int):

    try:
        folder: Folder = db.session.get(Folder, folder_id)
        theme: Theme = db.session.get(Theme, theme_id)

        q = academic_search_query({
            'folder_id': folder.id,
            'theme_id': theme.id,
            'is_user': True,
        })

        for a in db.session.execute(q).scalars():
            email_theme_folder_academic_publication_list.delay(
                folder_id=folder_id,
                theme_id=theme_id,
                academic_id=a.id,
            )

    except Exception as e:
        log_exception(e)
        raise e


@celery.task(
    bind=True,
    autoretry_for=(Exception,),
    max_retries=2,
    )
def email_theme_folder_academic_publication_list(self, folder_id: int, theme_id: int, academic_id: int):

    try:
        folder: Folder = db.session.get(Folder, folder_id)
        theme: Theme = db.session.get(Theme, theme_id)
        academic: Academic = db.session.get(Academic, academic_id)

        if academic.user:
            email(
                subject=f"Your publications in folder '{folder.name.title()}'",
                message=render_template('email/email_theme_folder_academic_publication_list/txt.txt', folder=folder, theme=theme, academic=academic),
                recipients=[academic.user.email],
                html_template='email/email_theme_folder_academic_publication_list/html.html',
                folder=folder,
                theme=theme,
                academic=academic,
            )

    except Exception as e:
        log_exception(e)
        raise e
