from typing import Optional
from flask import render_template
from sqlalchemy import or_, select
from wtforms import EmailField, HiddenField, SelectField, StringField
from lbrc_flask.forms import FlashingForm
from wtforms.validators import Length, DataRequired
from academics.model.security import User, UserPicker
from academics.model.theme import Theme
from lbrc_flask.database import db
from lbrc_flask.security import system_user_id
from lbrc_flask.response import refresh_response


class UserEditForm(FlashingForm):
    id = HiddenField('id')
    email = EmailField('Email', validators=[Length(max=255), DataRequired()], render_kw={'autocomplete': 'off'})
    first_name = StringField('First Name', validators=[Length(max=255), DataRequired()], render_kw={'autocomplete': 'off'})
    last_name = StringField('Last Name', validators=[Length(max=255), DataRequired()], render_kw={'autocomplete': 'off'})
    theme = SelectField('Theme', coerce=int, default=0, validators=[DataRequired()])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        themes = db.session.execute(
            select(Theme).order_by(Theme.name)
        )
        self.theme.choices = [(0, '')] + [(t.id, t.name) for t in themes]


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


def render_user_search_add(add_url: str, success_callback: Optional[callable]=None):
    form = UserEditForm()

    if form.validate_on_submit():
        user = User()
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.username = form.email.data
        user.email = form.email.data
        user.theme_id = form.theme.data

        db.session.add(user)
        db.session.commit()

        if success_callback is not None:
            success_callback(user)

        return refresh_response()

    return render_template(
        "lbrc/search_form_result.html",
        warning="No users match your search criteria.  Use this form to add a new user.",
        title=f"Add user",
        form=form,
        url=add_url,
    )


def user_search_query(search_data):
    search_data = search_data or {}

    q =  (
        select(UserPicker)
        .where(User.active == True)
        .where(User.id != system_user_id())
        .order_by(User.last_name, User.first_name, User.id)
    )

    if x := search_data.get('search'):
        for word in x.split():
            q = q.where(or_(
                User.first_name.like(f"%{word}%"),
                User.last_name.like(f"%{word}%"),
                User.email.like(f"%{word}%"),
                User.username.like(f"%{word}%"),
            ))

    return q

