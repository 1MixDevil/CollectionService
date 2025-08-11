from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound
import asyncio

from app.core.db import get_db
from app.schemas.figure_schema import (
    CollectTypeCreate, CollectTypeRead,
    FigureCreate, FigureRead, FigureUpdate, FigureDetail, SimilarFigure, BulkAddResponse, BulkAddError,
    FigureToUserCreate, FigureToUserRead, FigureToUserUpdate, FigureToUserReadFull, FigureInfo
)
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.crud.figure_crud import (
    # CollectType
    create_collect_type, get_collect_type, list_collect_types, update_collect_type, delete_collect_type,
    # Figure
    create_figure, get_figure, list_figures, update_figure, delete_figure,
    # FigureToUser
    list_user_figures, add_figure_to_user, update_user_figure, delete_user_figure,
    # detail
    get_figure_detail, get_figure_info_crud, get_similar_figures, get_all_figures
)

from app.models.figures_model import FigureToUser

from app.businessLogic.parser import FastFigureUpdater

router = APIRouter(prefix="/figure", tags=["figure"])


# — CollectType endpoints —

@router.post("/types/", response_model=CollectTypeRead, status_code=status.HTTP_201_CREATED)
def create_type(ct: CollectTypeCreate, db: Session = Depends(get_db)):
    return create_collect_type(db, ct)

@router.get("/types/", response_model=List[CollectTypeRead])
def read_types(db: Session = Depends(get_db)):
    return list_collect_types(db)

@router.get("/types/{ct_id}", response_model=CollectTypeRead)
def read_type(ct_id: int, db: Session = Depends(get_db)):
    try:
        return get_collect_type(db, ct_id)
    except NoResultFound as e:
        raise HTTPException(404, str(e))

@router.patch("/types/{ct_id}", response_model=CollectTypeRead)
def patch_type(ct_id: int, ct: CollectTypeCreate, db: Session = Depends(get_db)):
    try:
        return update_collect_type(db, ct_id, ct)
    except NoResultFound as e:
        raise HTTPException(404, str(e))

@router.delete("/types/{ct_id}", status_code=status.HTTP_204_NO_CONTENT)
def del_type(ct_id: int, db: Session = Depends(get_db)):
    try:
        delete_collect_type(db, ct_id)
    except NoResultFound as e:
        raise HTTPException(404, str(e))


# — Figure endpoints —

@router.post("/", response_model=FigureRead, status_code=status.HTTP_201_CREATED)
def create_fig(fig: FigureCreate, db: Session = Depends(get_db)):
    return create_figure(db, fig)

@router.get("/", response_model=List[FigureRead])
def read_all_figures(db: Session = Depends(get_db)):
    return list_figures(db)

@router.get("/{fig_id}", response_model=FigureDetail)
def read_figure(fig_id: int, db: Session = Depends(get_db)):
    try:
        fig, owned, count = get_figure_detail(db, fig_id)
        # маппим вручную в Pydantic
        return FigureDetail.from_orm(fig).copy(update={
            "owned_by": owned,
            "owners_count": count
        })
    except NoResultFound as e:
        raise HTTPException(404, str(e))

@router.patch("/{fig_id}", response_model=FigureRead)
def patch_figure(fig_id: int, data: FigureUpdate, db: Session = Depends(get_db)):
    try:
        return update_figure(db, fig_id, data)
    except NoResultFound as e:
        raise HTTPException(404, str(e))

@router.delete("/{fig_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_fig(fig_id: int, db: Session = Depends(get_db)):
    try:
        delete_figure(db, fig_id)
    except NoResultFound as e:
        raise HTTPException(404, str(e))


# Новый endpoint для очистки всей коллекции пользователя
@router.delete(
    "/user/{user_id}/collection",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить все фигурки пользователя",
    description="Полностью очищает коллекцию заданного пользователя"
)
def clear_user_collection_endpoint(user_id: int, db: Session = Depends(get_db)):
    """
    Bulk delete all FigureToUser records for given user in one operation.
    """
    try:
        # Импортируйте модель FigureToUser сверху файла:
        # from app.models.figures_model import FigureToUser
        delete_count = (
            db.query(FigureToUser)
              .filter(FigureToUser.user_id == user_id)
              .delete(synchronize_session=False)
        )
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при очистке коллекции: {e}"
        )
    return

@router.get(
    "/user/{user_id}/",
    response_model=List[FigureToUserRead],
    status_code=status.HTTP_200_OK
)
def read_user_figures(user_id: int, db: Session = Depends(get_db)):
    records = list_user_figures(db, user_id)
    result = []
    for rec in records:
        # rec.figure — это ORM‑объект Figure
        result.append(FigureToUserRead(
            id=rec.id,
            bricklink_id=rec.figure.bricklink_id,
            name=rec.figure.name,
            price_buy=rec.price_buy,
            price_sale=rec.price_sale,
            description=rec.description,
            buy_date=rec.buy_date,
            sale_date=rec.sale_date,
        ))
    return result

@router.post("/user/", response_model=FigureToUserRead, status_code=status.HTTP_201_CREATED)
def create_user_figure(rec: FigureToUserCreate, db: Session = Depends(get_db)):
    return add_figure_to_user(db, rec)

@router.patch("/user/{rec_id}", response_model=FigureToUserRead)
def patch_user_figure(rec_id: int, data: FigureToUserUpdate, db: Session = Depends(get_db)):
    try:
        return update_user_figure(db, rec_id, data)
    except NoResultFound as e:
        raise HTTPException(404, str(e))

@router.delete("/user/", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_figure_endpoint(user_id: str, bricklink_id: str, db: Session = Depends(get_db)):
    try:
        delete_user_figure(db, user_id, bricklink_id)
    except NoResultFound as e:
        raise HTTPException(404, str(e))
    
@router.put("/update_figures/")
async def update_figures(
    article: str,
    max_miss: int = 20,
    db: Session = Depends(get_db)
):
    added = await FastFigureUpdater.update(db, article, max_miss)
    return {"added": added}

@router.put("/update_figures_all/", status_code=status.HTTP_200_OK)
async def update_all_figures(
    max_miss: int = 50,
    db: Session = Depends(get_db)
):
    """
    Запустить обновление данных для всех доступных артикулей параллельно.
    Возвращает словарь с количеством добавленных фигур по каждому артикулу и общую сумму.
    """
    # Получаем все типы коллекций (каждый содержит поле article)
    from app.models.figures_model import CollectType, Figure

    collect_types = db.query(CollectType).all()
    if not collect_types:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Не найден ни один тип для обновления"
        )

    # Формируем задачи для параллельного обновления
    tasks = []
    for ct in collect_types:
        tasks.append(
            FastFigureUpdater.update(db, ct.article, max_miss)
        )

    # Выполняем все задачи параллельно
    results = await asyncio.gather(*tasks, return_exceptions=True)

    summary = {}
    total_added = 0

    for ct, res in zip(collect_types, results):
        if isinstance(res, Exception):
            # Если при обновлении произошла ошибка, фиксируем её текст
            summary[ct.article] = f"error: {res}"
        else:
            summary[ct.article] = res
            total_added += res

    return {"added_per_article": summary, "total_added": total_added}


@router.get(
    "/info/",
    response_model=FigureInfo,
    status_code=status.HTTP_200_OK
)
def get_figure_info(
    user_id:     int     = Query(..., description="ID пользователя"),
    bricklink_id:str    = Query(..., description="Bricklink ID фигурки"),
    db:          Session = Depends(get_db),
):
    
    fig, user_record = get_figure_info_crud(db, user_id, bricklink_id)
    if not fig:
        raise HTTPException(status_code=404, detail="Figure not found")

    return FigureInfo(
        id                = fig.id,
        name              = fig.name,
        bricklink_id      = fig.bricklink_id,
        type_collected_id = fig.type_collected_id,
        user_record       = user_record,
    )

@router.get(
    "/similar/",
    response_model=List[SimilarFigure],
    status_code=status.HTTP_200_OK,
    summary="Поиск похожих названий фигурок",
    description="Ищет по pg_trgm сходству и возвращает топ-N совпадений.",
)
def find_similar_figures(
    name: str = Query(..., description="Примерное имя фигурки"),
    limit: int = Query(5, ge=1, le=50, description="Максимум результатов"),
    threshold: float = Query(0.3, ge=0.0, le=1.0, description="Порог сходства (0–1)"),
    db: Session = Depends(get_db),
) -> List[SimilarFigure]:
    # вызываем CRUD‑функцию
    results = get_similar_figures(db, typo=name, limit=limit, threshold=threshold)

    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Похожих фигурок не найдено",
        )

    # results — список tuples или ORM‑объектов с полями id, name, similarity
    return [
        SimilarFigure(id=r.id, name=r.name, bricklink_id=r.bricklink_id, similarity=r.similarity)
        for r in results
    ]

@router.get(
    "/all/",
    response_model=List[str],
    summary="Вернуть все bricklink_id фигурок",
)
def read_all_figures(
    prefix: Optional[str] = Query(None, description="Если указан — фильтрация по префиксу, например 'SW'"),
    db: Session = Depends(get_db)
) -> List[str]:
    """
    Возвращает отсортированный список всех `bricklink_id` из таблицы фигурок.
    """
    try:
        serials = get_all_figures(db, prefix=prefix)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return serials

@router.post(
    "/user/bulk/",
    response_model=BulkAddResponse,
    status_code=status.HTTP_200_OK,
    summary="Добавить несколько фигурок пользователю",
    description="Принимает список фигурок и возвращает разделение на успешно добавленные и не добавленные."
)
def bulk_add_figures_to_user(
    items: List[FigureToUserCreate],
    db: Session = Depends(get_db)
) -> BulkAddResponse:
    successes: List[FigureToUserRead] = []
    failures: List[BulkAddError] = []

    for idx, item in enumerate(items):
        try:
            # Вызов вашего CRUD‑метода
            rec = add_figure_to_user(db, item)
            successes.append(rec)
        except NoResultFound as e:
            failures.append(BulkAddError(
                index=idx,
                payload=item.dict(),
                error=f"NotFound: {e}"
            ))
            db.rollback()
        except Exception as e:
            failures.append(BulkAddError(
                index=idx,
                payload=item.dict(),
                error=str(e)
            ))
            db.rollback()

    return BulkAddResponse(successes=successes, failures=failures)
