from sqlalchemy import and_, case, distinct, func, or_, select
from academics.model.academic import Academic
from academics.model.folder import Folder, FolderDoi, FolderDoiUserRelevance
from academics.model.publication import CatalogPublication, Publication
from academics.services.publication_searching import catalog_publication_academics
from sqlalchemy.orm import with_expression, Mapped, query_expression


class FolderAcademic(Academic):
    folder_publication_count: Mapped[int] = query_expression()
    folder_relevant_count: Mapped[int] = query_expression()
    folder_not_relevant_count: Mapped[int] = query_expression()
    folder_unset_count: Mapped[int] = query_expression()



def folder_academics_search_query_with_folder_summary(search_data):
    cpa = catalog_publication_academics(search_data)

    q = (
        select(FolderAcademic)
        .select_from(cpa)
        .join(CatalogPublication, CatalogPublication.id == cpa.c.catalog_publication_id)
        .join(CatalogPublication.publication)
        .join(Academic, Academic.id == cpa.c.academic_id)
        .join(Publication.folder_dois)
        .join(FolderDoi.folder)
        .join(FolderDoiUserRelevance, and_(
            FolderDoiUserRelevance.folder_doi_id == FolderDoi.id,
            FolderDoiUserRelevance.user_id == Academic.user_id,
        ), isouter=True)
        .group_by(Academic.id)
        .order_by(Academic.last_name, Academic.first_name)
        .options(with_expression(FolderAcademic.folder_publication_count, func.count(distinct(CatalogPublication.publication_id))))
        .options(with_expression(FolderAcademic.folder_relevant_count, func.count(distinct(case(
            (FolderDoiUserRelevance.relevant == 1, FolderDoiUserRelevance.publication_id),
            else_=None
        )))))
        .options(with_expression(FolderAcademic.folder_not_relevant_count, func.count(distinct(case(
            (FolderDoiUserRelevance.relevant == 0, CatalogPublication.publication_id),
            else_=None
        )))))
        .options(with_expression(FolderAcademic.folder_unset_count, func.count(distinct(case(
            (FolderDoiUserRelevance.relevant == None, CatalogPublication.publication_id),
            else_=None
        )))))
    )

    if x := search_data.get('folder_id'):
        x = int(x)
        q = q.where(Folder.id == x)

    if x := search_data.get('search'):
        for word in x.split():
            q = q.where(or_(
                Academic.first_name.like(f"%{word}%"),
                Academic.last_name.like(f"%{word}%"),
            ))

    return q
