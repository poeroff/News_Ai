from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db

router = APIRouter()


@router.get("/")
async def root():
    return {"message": "Hello Worldsss!"}


@router.get("/health/db")
async def health_db(db: AsyncSession = Depends(get_db)):
    await db.execute(text("SELECT 1"))
    return {"db": "ok"}
