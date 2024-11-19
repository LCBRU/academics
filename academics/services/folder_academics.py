from sqlalchemy import and_, case, distinct, func, select
from academics.model.academic import Academic
from academics.model.folder import FolderDoi, FolderDoiUserRelevance
from academics.model.publication import Publication
from academics.services.academic_searching import academic_search_query
from academics.services.publication_searching import publication_academics_query, publication_folder_query
from sqlalchemy.orm import with_expression, Mapped, query_expression


class FolderAcademic(Academic):
    folder_publication_count: Mapped[int] = query_expression()
    folder_relevant_count: Mapped[int] = query_expression()
    folder_not_relevant_count: Mapped[int] = query_expression()
    folder_unset_count: Mapped[int] = query_expression()


def folder_academics_search_query_with_folder_summary(folder_id: int, search_string: str):
    publication_academics_q = publication_academics_query().cte('publication_academics')
    publication_folder_q = publication_folder_query().cte('publication_folder')
    folder_publication_user_relevance_q = folder_publication_user_relevance_query().cte('folder_publication_user_relevance')
    academic_search_query_q = academic_search_query({
        'search': search_string,
        'folder_id': folder_id
    }).cte('academic_search')

    q = (
        select(FolderAcademic)
        .select_from(publication_academics_q)
        .join(Academic, Academic.id == publication_academics_q.c.academic_id)
        .join(folder_publication_user_relevance_q, and_(
            folder_publication_user_relevance_q.c.publication_id == publication_academics_q.c.publication_id,
            folder_publication_user_relevance_q.c.academic_id == Academic.id,
            folder_publication_user_relevance_q.c.folder_id == folder_id,
        ), isouter=True)
        .where(publication_academics_q.c.publication_id.in_(
            select(publication_folder_q.c.publication_id)
            .where(publication_folder_q.c.folder_id == folder_id)
        ))
        .where(Academic.id.in_(select(academic_search_query_q.c.id)))
        .group_by(Academic.id)
        .order_by(Academic.last_name, Academic.first_name)
        .options(with_expression(
            FolderAcademic.folder_publication_count,
            func.count(distinct(publication_academics_q.c.publication_id))
        ))
        .options(with_expression(
            FolderAcademic.folder_relevant_count,
            func.count(distinct(case(
                (folder_publication_user_relevance_q.c.relevant == 1, publication_academics_q.c.publication_id),
                else_=None
            )))
        ))
        .options(with_expression(
            FolderAcademic.folder_not_relevant_count,
            func.count(distinct(case(
                (folder_publication_user_relevance_q.c.relevant == 0, publication_academics_q.c.publication_id),
                else_=None
            )))
        ))
        .options(with_expression(
            FolderAcademic.folder_unset_count,
            func.count(distinct(case(
                (folder_publication_user_relevance_q.c.relevant == None, publication_academics_q.c.publication_id),
                else_=None
            )))
        ))
    )

    return q


def folder_publication_user_relevance_query():
    return (
        select(
            FolderDoi.folder_id,
            Publication.id.label('publication_id'),
            Academic.id.label('academic_id'),
            FolderDoiUserRelevance.relevant
        )
        .select_from(Publication)
        .join(Publication.folder_dois)
        .join(FolderDoi.user_statuses)
        .join(Academic, Academic.user_id == FolderDoiUserRelevance.user_id)
    )
