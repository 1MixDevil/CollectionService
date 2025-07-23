from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound

from app.core.db import get_db
from app.schemas.figure_schema import (
    CollectTypeCreate, CollectTypeRead,
    FigureCreate, FigureRead, FigureUpdate, FigureDetail, SimilarFigure,
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
    get_figure_detail, get_figure_info_crud, get_similar_figures
)

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


# — FigureToUser endpoints (по пользователю) —

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
            user_id=rec.user_id,
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