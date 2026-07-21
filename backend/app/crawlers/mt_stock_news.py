import asyncio
import json
import re
from urllib.parse import parse_qs, urlparse

from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
from sqlalchemy.dialects.mysql import insert as mysql_insert

from ..database import AsyncSessionLocal
from ..models import StockArticle

MT_STOCK_NEWS_URL = "https://www.mt.co.kr/stock/stocknews?page={page}"

# 머니투데이 종목뉴스 목록(mt.co.kr/stock/stocknews) 레이아웃.
# 각 li.article_item 안에 종목명/종목코드/등락률(.headline_stock)과 기사 본문이 함께 들어있다.
STOCK_NEWS_SCHEMA = {
    "name": "MTStockNews",
    "baseSelector": "li.article_item",
    "fields": [
        {"name": "stock_href", "selector": ".headline_stock a", "type": "attribute", "attribute": "href"},
        {"name": "title", "selector": "h3.headline.news--tertiary", "type": "text"},
        {"name": "link", "selector": "a[href*='/stock/20']", "type": "attribute", "attribute": "href"},
        {"name": "thumbnail", "selector": ".article_body figure.thumb img", "type": "attribute", "attribute": "src"},
        {"name": "summary", "selector": ".article_body .description", "type": "text"},
        {"name": "article_date", "selector": ".meta .article_date", "type": "text"},
    ],
}

# .meta .article_date는 "2026.07.13 10:48" 형식 -> 날짜/시각을 따로 뽑음
ARTICLE_DATETIME_RE = re.compile(r"(\d{4})\.(\d{2})\.(\d{2})(?:\s+(\d{2}):(\d{2}))?")

# 본문 맨 앞의 사진+캡션 줄 (예: ![캡션](url)[](url)캡션) - 분류에 불필요, 토큰만 먹음
LEADING_IMAGE_LINE_RE = re.compile(r"^!\[[^\n]*\n")
# 본문 중간의 종목 인라인 링크 [텍스트](url) -> 텍스트만 남기고 URL 제거
MD_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def _parse_stock_code(stock_href: str | None) -> str | None:
    if not stock_href:
        return None
    qs = parse_qs(urlparse(stock_href).query)
    return qs.get("keyword", [None])[0]


def _clean(value: str | None) -> str | None:
    return " ".join(value.split()) if value else value


async def fetch_stock_news(crawler: AsyncWebCrawler, page: int = 1) -> list[dict]:
    config = CrawlerRunConfig(
        extraction_strategy=JsonCssExtractionStrategy(STOCK_NEWS_SCHEMA),
        wait_for="css:li.article_item",
        cache_mode=CacheMode.BYPASS,
    )
    # crawl4ai/Playwright가 드물게 응답 없이 멈추는 경우가 있어 자체 타임아웃으로 방어
    result = await asyncio.wait_for(
        crawler.arun(url=MT_STOCK_NEWS_URL.format(page=page), config=config), timeout=60
    )
    raw = json.loads(result.extracted_content) if result.extracted_content else []

    articles = []
    for item in raw:
        link = item.get("link")
        stock_code = _parse_stock_code(item.get("stock_href"))
        # 종목코드가 없으면 stocks 테이블 FK를 만족시킬 수 없어 애초에 제외
        if not link or not stock_code:
            continue
        m = ARTICLE_DATETIME_RE.search(item.get("article_date") or "")
        article_date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None
        article_time = f"{m.group(4)}:{m.group(5)}" if m and m.group(4) else None
        articles.append(
            {
                "stock_code": stock_code,
                "title": _clean(item.get("title")),
                "link": link,
                "summary": _clean(item.get("summary")),
                "thumbnail": item.get("thumbnail"),
                "body": None,
                # 등락률은 장 마감 후 별도로 채워 넣을 예정이라 크롤링 시점엔 비워둠
                "change_percent": None,
                "change_direction": None,
                "article_date": article_date,
                "article_time": article_time,
            }
        )
    return articles


async def fetch_article_body(crawler: AsyncWebCrawler, link: str) -> str | None:
    # 목록 페이지의 summary는 짧은 미리보기라, LLM 호재/악재 판별용으로는
    # 기사 상세 페이지(#articleView)에서 본문 전체를 따로 긁는다.
    # css_selector로 스코프하면 crawl4ai가 그 영역만 마크다운으로 정리해서 준다.
    config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, css_selector="#articleView")
    result = await asyncio.wait_for(crawler.arun(url=link, config=config), timeout=60)
    if not result.markdown:
        return None
    text = LEADING_IMAGE_LINE_RE.sub("", result.markdown, count=1)
    text = MD_LINK_RE.sub(r"\1", text)
    return _clean(text)


async def save_new_articles(articles: list[dict]) -> int:
    if not articles:
        return 0
    async with AsyncSessionLocal() as session:
        # link UNIQUE 제약 위반 또는 stocks에 없는 종목코드(FK 위반)는 조용히 건너뜀
        stmt = mysql_insert(StockArticle).values(articles).prefix_with("IGNORE")
        result = await session.execute(stmt)
        await session.commit()
    return result.rowcount


# 직전 주기에 수집한 링크 집합. 이번 결과와 완전히 같으면 새 기사가 없다는 뜻이라
# INSERT를 건너뛰어 매분 도는 폴링이 DB에 불필요한 트래픽을 주지 않게 한다.
_last_seen_links: set[str] = set()


async def refresh_stock_news_job(pages: int = 2) -> None:
    global _last_seen_links
    try:
        async with AsyncWebCrawler() as crawler:
            articles = []
            for page in range(1, pages + 1):
                articles.extend(await fetch_stock_news(crawler, page))

            current_links = {a["link"] for a in articles}
            if current_links == _last_seen_links:
                print("[종목뉴스] 변경 없음, DB 조회 생략")
                return

            # 아직 못 본 링크만 상세 페이지까지 열어서 본문을 긁는다 (이미 본 건 어차피 INSERT IGNORE로 스킵됨)
            new_links = current_links - _last_seen_links
            for a in articles:
                if a["link"] in new_links:
                    try:
                        a["body"] = await fetch_article_body(crawler, a["link"])
                    except Exception as e:
                        print(f"[종목뉴스] 본문 수집 실패 ({a['link']}): {e}")

        new_count = await save_new_articles(articles)
        print(f"[종목뉴스] {new_count}건 신규 저장")
        _last_seen_links = current_links
    except Exception as e:
        print(f"[종목뉴스] 크롤링 실패: {e}")
