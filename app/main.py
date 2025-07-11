# app/main.py
from fastapi import FastAPI
from app.routers import figure_router


app = FastAPI(title="Collection Service")

app.include_router(figure_router.router)