from typing import List, Optional
from datetime import date
from pydantic import BaseModel, Field


# — CollectType —

class CollectTypeCreate(BaseModel):
    name: str = Field(..., example="Vintage")

class CollectTypeRead(BaseModel):
    id: int
    name: str

    class Config:
        orm_mode = True


# — Figure —

class FigureBase(BaseModel):
    name: str = Field(..., example="Lego X-Wing")
    bricklink_id: str = Field(..., example="75102")
    type_collected_id: int = Field(..., example=1)

class FigureCreate(FigureBase):
    pass

class FigureUpdate(BaseModel):
    name: Optional[str]
    bricklink_id: Optional[str]
    type_collected_id: Optional[int]

class FigureRead(FigureBase):
    id: int
    type_collected: CollectTypeRead

    class Config:
        orm_mode = True

# Детальная информация о связи «Figure ↔ User»
class FigureToUserRead(BaseModel):
    id: int
    user_id: int
    bricklink_id: str                # ← добавили
    price_buy: Optional[float]
    price_sale: Optional[float]
    description: Optional[str]
    buy_date: Optional[date]
    sale_date: Optional[date]

    class Config:
        orm_mode = True

# Детальный вывод одной Figure
class FigureDetail(FigureRead):
    owners_count: int = Field(..., example=5)
    owned_by: List[FigureToUserRead] = []

    class Config:
        orm_mode = True


# — FigureToUser —

class FigureToUserCreate(BaseModel):
    user_id: int                = Field(..., example=42)
    bricklink_id: str           = Field(..., example="75102")
    price_buy: Optional[float]  = Field(None, allow_none=True) #  <--  Здесь!
    price_sale: Optional[float] = Field(None, allow_none=True) #  <--  И здесь!
    description: Optional[str]  = Field(None, allow_none=True)  #  <--  И тут!
    buy_date: Optional[date]    = Field(None, allow_none=True)    #  <--  И здесь!
    sale_date: Optional[date]   = Field(None, allow_none=True)   #  <--  И здесь!

class FigureToUserUpdate(BaseModel):
    price_buy: Optional[float]
    price_sale: Optional[float]
    description: Optional[str]
    buy_date: Optional[date]
    sale_date: Optional[date]

class FigureToUserReadFull(FigureToUserRead):
    figure: FigureRead

    class Config:
        orm_mode = True
