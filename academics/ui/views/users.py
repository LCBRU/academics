from typing import Optional
from flask import render_template
from sqlalchemy import select
from wtforms import EmailField, HiddenField, SelectField, StringField
from lbrc_flask.forms import FlashingForm
from wtforms.validators import Length, DataRequired
from academics.model.security import User, UserPicker
from academics.model.theme import Theme
from lbrc_flask.database import db
from lbrc_flask.security import system_user_id


class UserEditForm(FlashingForm):
    id = HiddenField('id')
    email = EmailField('Email', validators=[Length(max=255), DataRequired()])
    first_name = StringField('Fire Name', validators=[Length(max=255), DataRequired()])
    last_name = StringField('Last Name', validators=[Length(max=255), DataRequired()])
    themes = SelectField('Theme', coerce=int, default=0, validators=[DataRequired()])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.themes.choices = [(0, '')] + [(t.id, t.name) for t in Theme.query.all()]


def render_user_search_results(
        results: list[UserPicker],
        title: str,
        add_url: str,
        results_url: str,
        results_url_args: Optional[dict]=None,
        ):
    
    if results_url_args is None:
        results_url_args = {}

    return render_template(
        "lbrc/search_add_results.html",
        add_title=title,
        add_url=add_url,
        results_url=results_url,
        results_url_args=results_url_args,
        results=results,
    )


def user_search_query(search_string: str):
    q =  (
        select(UserPicker)
        .where(User.active == True)
        .where((User.first_name + ' ' + User.last_name).like(f"%{search_string}%"))
        .where(User.id != system_user_id())
        .order_by(User.last_name, User.first_name, User.id)
    )
    
    return q

