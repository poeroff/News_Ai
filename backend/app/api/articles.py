from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..crawlers.naver_sections import ECONOMY_SUBSECTIONS, IT_SCIENCE_SUBSECTIONS, WORLD_SUBSECTIONS
from ..database import get_db
from ..models import Article

CATEGORY_SECTIONS: dict[str, list[str]] = {
    "economy": ["101", *ECONOMY_SUBSECTIONS.keys()],
    "world": ["104", *WORLD_SUBSECTIONS.keys()],
    "it-science": ["105", *IT_SCIENCE_SUBSECTIONS.keys()],
}
# 홈은 정치 없이 경제/세계/IT과학을 합쳐 최신순으로 보여준다.
CATEGORY_SECTIONS["home"] = [sid for sections in CATEGORY_SECTIONS.values() for sid in sections]

router = APIRouter()


@router.get("/articles/{category}")
async def get_articles(category: str, db: AsyncSession = Depends(get_db)):
    sections = CATEGORY_SECTIONS.get(category)
    if sections is None:
        raise HTTPException(status_code=404, detail="unknown category")

    # cluster_id == id 인 행만 골라서 같은 사건으로 묶인 기사들 중 대표 기사 하나만 노출
    stmt = (
        select(Article)
        .where(Article.section.in_(sections), Article.id == Article.cluster_id)
        .order_by(Article.id.desc())
        .limit(100)
    )
    articles = (await db.scalars(stmt)).all()
    return [
        {
            "title": a.title,
            "link": a.link,
            "summary": a.summary,
            "press": a.press,
            "thumbnail": a.thumbnail,
            "articleDate": a.article_date,
        }
        for a in articles
    ]
