# app/core/db.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import MetaData
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://aml1:aml1@db:5432/lego_db")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base(metadata=MetaData(schema='figure'))

def get_db():
    """
    FastAPI-dpendency для получения сессии БД
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()