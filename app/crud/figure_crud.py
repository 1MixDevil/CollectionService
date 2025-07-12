from typing import List
from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound
from sqlalchemy import func

from app.models.figures_model import Figure, FigureToUser, CollectType
from app.schemas.figure_schema import (
    CollectTypeCreate, 
    FigureCreate, FigureUpdate,
    FigureToUserCreate, FigureToUserUpdate
)


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
    fig = db.query(Figure).filter_by(bricklink_id=data.bricklink_id).first()
    if not fig:
        raise NoResultFound(f"Figure with bricklink_id={data.bricklink_id} not found")
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
    return rec

def get_user_figure_record(db: Session, rec_id: int) -> FigureToUser:
    rec = db.query(FigureToUser).get(rec_id)
    if not rec:
        raise NoResultFound(f"FigureToUser id={rec_id} not found")
    return rec

def update_user_figure(db: Session, rec_id: int, data: FigureToUserUpdate) -> FigureToUser:
    rec = get_user_figure_record(db, rec_id)
    for field, val in data.dict(exclude_none=True).items():
        setattr(rec, field, val)
    db.commit()
    db.refresh(rec)
    return rec

def delete_user_figure(db: Session, rec_id: int) -> None:
    rec = get_user_figure_record(db, rec_id)
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
