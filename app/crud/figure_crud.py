from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound
from sqlalchemy import func
from fastapi import HTTPException

from app.models.figures_model import Figure, FigureToUser, CollectType
from app.schemas.figure_schema import (
    CollectTypeCreate, 
    FigureCreate, FigureUpdate,
    FigureToUserCreate, FigureToUserUpdate, FigureToUserRead
)

from sqlalchemy import func, cast, text
from sqlalchemy.types import Text


# — CollectType CRUD —

def create_collect_type(db: Session, data: CollectTypeCreate) -> CollectType:
    ct = CollectType(**data.dict())
    db.add(ct)
    db.commit()
    db.refresh(ct)
    return ct

def get_collect_type(db: Session, ct_id: int) -> CollectType:
    ct = db.query(CollectType).get(ct_id)
    if not ct:
        raise NoResultFound(f"CollectType id={ct_id} not found")
    return ct

def list_collect_types(db: Session) -> List[CollectType]:
    return db.query(CollectType).all()

def update_collect_type(db: Session, ct_id: int, data: CollectTypeCreate) -> CollectType:
    ct = get_collect_type(db, ct_id)
    ct.name = data.name
    db.commit()
    db.refresh(ct)
    return ct

def delete_collect_type(db: Session, ct_id: int) -> None:
    ct = get_collect_type(db, ct_id)
    db.delete(ct)
    db.commit()


# — Figure CRUD —

def create_figure(db: Session, data: FigureCreate) -> Figure:
    fig = Figure(**data.dict())
    db.add(fig)
    db.commit()
    db.refresh(fig)
    return fig

def get_figure(db: Session, fig_id: int) -> Figure:
    fig = db.query(Figure).get(fig_id)
    if not fig:
        raise NoResultFound(f"Figure id={fig_id} not found")
    return fig

def list_figures(db: Session) -> List[Figure]:
    return db.query(Figure).all()

def update_figure(db: Session, fig_id: int, data: FigureUpdate) -> Figure:
    fig = get_figure(db, fig_id)
    for field, val in data.dict(exclude_none=True).items():
        setattr(fig, field, val)
    db.commit()
    db.refresh(fig)
    return fig

def delete_figure(db: Session, fig_id: int) -> None:
    fig = get_figure(db, fig_id)
    db.delete(fig)
    db.commit()


# — FigureToUser CRUD —

def list_user_figures(db: Session, user_id: int) -> List[FigureToUser]:
    return db.query(FigureToUser).filter_by(user_id=user_id).all()

def add_figure_to_user(db: Session, data: FigureToUserCreate) -> FigureToUser:
    fig = db.query(Figure).filter_by(bricklink_id=(data.bricklink_id).lower()).first()
    print(fig)
    if not fig:
        # Вместо NoResultFound возвращаем HTTP-ошибку
        raise HTTPException(
            status_code=404,
            detail=f"Фигурка с артикулом {data.bricklink_id} не найдена"
        )
    rec = FigureToUser(
        user_id     = data.user_id,
        figure_id   = fig.id,
        price_buy   = data.price_buy,
        price_sale  = data.price_sale,
        description = data.description,
        buy_date    = data.buy_date,
        sale_date   = data.sale_date,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return FigureToUserRead(
        id=rec.id,
        user_id=rec.user_id,
        figure_id=rec.figure_id,
        bricklink_id=rec.figure.bricklink_id, 
        name=rec.figure.name, 
        price_buy=rec.price_buy,
        price_sale=rec.price_sale,
        description=rec.description,
        buy_date=rec.buy_date,
        sale_date=rec.sale_date,
    )

def get_user_figure_record(
    db: Session,
    user_id: int,
    bricklink_id: str
) -> FigureToUser:
    """
    Ищет первую запись FigureToUser для данного пользователя и bricklink_id.
    Если не найдена — бросает NoResultFound.
    """
    rec = (
        db.query(FigureToUser)
          .join(Figure, Figure.id == FigureToUser.figure_id)
          .filter(
              FigureToUser.user_id == user_id,
              Figure.bricklink_id  == bricklink_id
          )
          .first()
    )
    if not rec:
        raise NoResultFound(
            f"No FigureToUser for user_id={user_id} and bricklink_id={bricklink_id}"
        )
    return rec

def update_user_figure(db: Session, rec_id: int, data: FigureToUserUpdate) -> FigureToUser:
    rec = get_user_figure_record(db, rec_id)
    for field, val in data.dict(exclude_none=True).items():
        setattr(rec, field, val)
    db.commit()
    db.refresh(rec)
    return rec

def delete_user_figure(db: Session, user_id: str, bricklink_id: str) -> None:
    rec = get_user_figure_record(db, user_id, bricklink_id)
    db.delete(rec)
    db.commit()


def get_figure_detail(db: Session, fig_id: int):
    # основная фигура
    fig = get_figure(db, fig_id)
    # список связей
    owned = db.query(FigureToUser).filter_by(figure_id=fig_id).all()
    # считаем владельцев
    count = db.query(func.count(FigureToUser.id)).filter_by(figure_id=fig_id).scalar() or 0
    return fig, owned, count

def get_figure_info_crud(db: Session, user_id: int, bricklink_id: str):
    # 1) Сам объект Figure
    fig = db.query(Figure).filter(Figure.bricklink_id == bricklink_id).first()
    if not fig:
        return None, None

    # 2) Запись пользователя (если есть)
    rec = (
        db.query(FigureToUser)
          .filter(FigureToUser.figure_id == fig.id,
                  FigureToUser.user_id   == user_id)
          .first()
    )

    # 3) Вручную собираем Pydantic‑модель
    user_record = None
    if rec:
        user_record = FigureToUserRead(
            id           = rec.id,
            user_id      = rec.user_id,
            bricklink_id = fig.bricklink_id,  # или rec.figure.bricklink_id
            name         = fig.name,
            price_buy    = float(rec.price_buy)   if rec.price_buy  is not None else None,
            price_sale   = float(rec.price_sale)  if rec.price_sale is not None else None,
            description  = rec.description,
            buy_date     = rec.buy_date,
            sale_date    = rec.sale_date,
        )

    return fig, user_record

def get_similar_figures(db, typo: str, limit: int = 5, threshold: float = 0.3):
    # Подставляем свою схему в search_path, чтобы найти similarity и gin_trgm_ops
    db.execute(text("SET search_path TO figure;"))

    typo_text = cast(typo, Text)
    query = (
        db.query(
            Figure.id,
            Figure.name,
            Figure.bricklink_id,
            func.similarity(Figure.name, typo_text).label("similarity")
        )
        .filter(func.similarity(Figure.name, typo_text) >= threshold)
        .order_by(func.similarity(Figure.name, typo_text).desc())
        .limit(limit)
    )
    return query.all()

def get_all_figures(db: Session, prefix: Optional[str] = None) -> List[str]:
    """
    Запрашивает из БД все bricklink_id; если передан `prefix`, то только начи-
    нающиеся с него, и возвращает их отсортированными.
    """
    query = db.query(Figure.bricklink_id)
    if prefix:
        print(prefix)
        print(prefix)
        print(prefix)
        # SQL: WHERE bricklink_id LIKE 'SW%'
        query = query.filter(Figure.bricklink_id.like(f"{prefix}%"))
    # ORDER BY bricklink_id
    rows = query.order_by(Figure.bricklink_id).all()
    # .all() возвращает список кортежей [(id,), ...]
    return [row[0] for row in rows]


def add_figures_to_user_bulk(
    db: Session,
    recs: List[FigureToUserCreate]
) -> Tuple[List[FigureToUserRead], List[str]]:
    """
    Bulk add multiple figures to a user's collection.
    Returns a tuple of (successfully_created, failed_bricklink_ids).
    """
    created_objs = []
    failed = []

    for rec in recs:
        fig = db.query(Figure).filter(Figure.bricklink_id == rec.bricklink_id).one_or_none()
        if not fig:
            failed.append(rec.bricklink_id)
            continue
        obj = FigureToUser(
            user_id=rec.user_id,
            figure_id=fig.id,
            price_buy=rec.price_buy,
            price_sale=rec.price_sale,
            description=rec.description,
            buy_date=rec.buy_date,
            sale_date=rec.sale_date,
        )
        db.add(obj)
        created_objs.append(obj)

    db.commit()

    created = []
    for obj in created_objs:
        db.refresh(obj)
        created.append(FigureToUserRead.from_orm(obj))

    return created, failed
