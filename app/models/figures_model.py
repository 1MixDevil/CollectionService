from sqlalchemy import Column, Integer, String, Numeric, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.core.db import Base

# models/figure.py

class Figure(Base):
    __tablename__  = "figures"
    __table_args__ = {"schema": "figure"}

    id                = Column(Integer, primary_key=True, index=True)
    name              = Column(String, unique=False, nullable=False)
    bricklink_id      = Column(String, unique=True, nullable=False)
    type_collected_id = Column(Integer, ForeignKey("figure.type_of_collect.id"))

    owned_by       = relationship("FigureToUser", back_populates="figure")
    type_collected = relationship("CollectType", back_populates="figures")


class FigureToUser(Base):
    __tablename__  = "figure_to_user"
    __table_args__ = {"schema": "figure"}

    id          = Column(Integer, primary_key=True)
    price_buy   = Column(Numeric(10, 2), nullable=True)
    price_sale  = Column(Numeric(10, 2), nullable=True)
    description = Column(String, nullable=True)
    buy_date    = Column(Date, nullable=True)
    sale_date   = Column(Date, nullable=True)

    user_id     = Column(Integer, nullable=False)
    figure_id   = Column(Integer, ForeignKey("figure.figures.id"), nullable=False)

    figure = relationship("Figure", back_populates="owned_by")


class CollectType(Base):
    __tablename__  = "type_of_collect"
    __table_args__ = {"schema": "figure"}

    id      = Column(Integer, primary_key=True)
    name    = Column(String, unique=False, nullable=False) #Star Wars
    article = Column(String, unique=True, nullable=False) #sw
    pad_len = Column(Integer, unique=False, nullable=False) # 4(sw/1234/)

    figures = relationship("Figure", back_populates="type_collected")
