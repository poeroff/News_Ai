import asyncio
import json
from datetime import datetime, timezone

from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

RANKING_URL = "https://news.naver.com/main/ranking/popularDay.naver?mid=etc&sid1=111"

# 언론사별 랭킹 뉴스(news.naver.com/main/ranking) 페이지 레이아웃.
# 언론사 박스(.rankingnews_box)마다 그 언론사의 인기 기사 TOP5가 들어있다.
RANKING_SCHEMA = {
    "name": "NaverRankingBox",
    "baseSelector": ".rankingnews_box",
    "fields": [
        {"name": "outlet_name", "selector": ".rankingnews_name", "type": "text"},
        {
            "name": "articles",
            "selector": ".rankingnews_list li",
            "type": "nested_list",
            "fields": [
                {"name": "title", "selector": ".list_title", "type": "text"},
                {"name": "link", "selector": ".list_title", "type": "attribute", "attribute": "href"},
                {"name": "time_text", "selector": ".list_time", "type": "text"},
                # 화면 상단(뷰포트) 근처 항목만 src로 바로 내려주고, 아래쪽은 지연 로딩용
                # data-src에 실제 이미지 URL이 들어있어 둘 다 뽑아서 fallback으로 처리한다.
                {"name": "thumbnail_src", "selector": ".list_img img", "type": "attribute", "attribute": "src"},
                {
                    "name": "thumbnail_data_src",
                    "selector": ".list_img img",
                    "type": "attribute",
                    "attribute": "data-src",
                },
            ],
        },
    ],
}


async def fetch_ranking() -> list[dict]:
    config = CrawlerRunConfig(
        extraction_strategy=JsonCssExtractionStrategy(RANKING_SCHEMA),
        wait_for="css:.rankingnews_box",
        cache_mode=CacheMode.BYPASS,
    )
    async with AsyncWebCrawler() as crawler:
        # crawl4ai/Playwright가 드물게 응답 없이 멈추는 경우가 있어 자체 타임아웃으로 방어
        result = await asyncio.wait_for(crawler.arun(url=RANKING_URL, config=config), timeout=60)
    boxes = json.loads(result.extracted_content) if result.extracted_content else []

    outlets = []
    for box in boxes:
        outlet_name = (box.get("outlet_name") or "").strip()
        if not outlet_name:
            continue
        articles = []
        for i, a in enumerate(box.get("articles", []), start=1):
            title = (a.get("title") or "").strip()
            link = a.get("link")
            if not title or not link:
                continue
            articles.append(
                {
                    "rank": i,
                    "title": title,
                    "link": link,
                    "timeText": (a.get("time_text") or "").strip(),
                    "thumbnail": a.get("thumbnail_data_src") or a.get("thumbnail_src"),
                }
            )
        if articles:
            outlets.append({"outletName": outlet_name, "articles": articles})
    return outlets


# fetch_ranking()은 헤드리스 브라우저를 띄우는 무거운 작업이라, 요청마다 실행하지 않고
# 1시간 주기 백그라운드 작업으로 갱신한 결과를 메모리에 캐싱해서 API는 즉시 응답한다.
_cache: dict | None = None


async def refresh_ranking_cache() -> None:
    global _cache
    outlets = await fetch_ranking()
    _cache = {"outlets": outlets, "updatedAt": datetime.now(timezone.utc).isoformat()}


def get_cached_ranking() -> dict | None:
    return _cache


async def refresh_ranking_job() -> None:
    try:
        await refresh_ranking_cache()
    except Exception as e:
        print(f"[랭킹] 크롤링 실패: {e}")
