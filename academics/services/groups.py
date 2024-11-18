from typing import Optional
from lbrc_flask.security import current_user_id
from sqlalchemy import func, select
from academics.model.group import Group
from lbrc_flask.database import db


def is_group_name_duplicate(name: str, group_id: Optional[int]):
    q = (
        select(func.count(Group.id))
        .where(Group.name == name)
        .where(Group.owner_id == current_user_id())
    )

    if group_id is not None:
        q = q.where(Group.id != group_id)

    return db.session.execute(q).scalar() > 0
