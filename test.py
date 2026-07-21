import asyncio
import json
import sys
from urllib.parse import parse_qs, urlparse

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

sys.stdout.reconfigure(encoding="utf-8")

# 종목뉴스 목록의 각 <li class="article_item">에서
# 종목명/종목코드/등락률 + 기사(제목/링크/썸네일/요약/날짜/기자)를 함께 추출
STOCK_NEWS_SCHEMA = {
    "name": "MTStockNews",
    "baseSelector": "li.article_item",
    "fields": [
        {"name": "stock_name", "selector": ".headline_stock a", "type": "text"},
        {"name": "stock_href", "selector": ".headline_stock a", "type": "attribute", "attribute": "href"},
        {"name": "change_percent", "selector": ".headline_stock span", "type": "text"},
        {"name": "change_direction", "selector": ".headline_stock span", "type": "attribute", "attribute": "class"},
        {"name": "title", "selector": "h3.headline.news--tertiary", "type": "text"},
        {"name": "link", "selector": "a[href*='/stock/20']", "type": "attribute", "attribute": "href"},
        {"name": "thumbnail", "selector": ".article_body figure.thumb img", "type": "attribute", "attribute": "src"},
        {"name": "summary", "selector": ".article_body .description", "type": "text"},
        {"name": "article_date", "selector": ".meta .article_date", "type": "text"},
        {"name": "writer", "selector": ".meta .writer", "type": "text"},
    ],
}


def parse_stock_code(stock_href: str | None) -> str | None:
    if not stock_href:
        return None
    qs = parse_qs(urlparse(stock_href).query)
    return qs.get("keyword", [None])[0]


def clean(value: str | None) -> str | None:
    return " ".join(value.split()) if value else value


async def main():
    browser_conf = BrowserConfig(headless=True)
    run_conf = CrawlerRunConfig(
        extraction_strategy=JsonCssExtractionStrategy(STOCK_NEWS_SCHEMA),
        cache_mode=CacheMode.BYPASS,
    )

    async with AsyncWebCrawler(config=browser_conf) as crawler:
        result = await crawler.arun(
            url="https://www.mt.co.kr/stock/stocknews?page=1",
            config=run_conf,
        )
        raw = json.loads(result.extracted_content) if result.extracted_content else []

        articles = []
        for item in raw:
            direction = "down" if "down" in (item.get("change_direction") or "") else "up"
            articles.append(
                {
                    "stock_name": clean(item.get("stock_name")),
                    "stock_code": parse_stock_code(item.get("stock_href")),
                    "change_percent": clean(item.get("change_percent")),
                    "change_direction": direction,
                    "title": clean(item.get("title")),
                    "link": item.get("link"),
                    "thumbnail": item.get("thumbnail"),
                    "summary": clean(item.get("summary")),
                    "article_date": clean(item.get("article_date")),
                    "writer": clean(item.get("writer")),
                }
            )

        print(json.dumps(articles, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())