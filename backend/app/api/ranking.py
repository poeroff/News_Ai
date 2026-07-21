from datetime import datetime, timezone

from fastapi import APIRouter

from ..crawlers.naver_ranking import fetch_ranking, get_cached_ranking

router = APIRouter()


@router.get("/ranking")
async def get_ranking():
    cached = get_cached_ranking()
    if cached is not None:
        return cached
    # 서버 기동 직후, 아직 백그라운드 캐시가 한 번도 채워지지 않은 경우에만 즉석 크롤링
    outlets = await fetch_ranking()
    return {
        "outlets": outlets,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }
