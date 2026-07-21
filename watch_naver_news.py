#!/usr/bin/env python3
"""
네이버 뉴스 섹션을 주기적으로 폴링하면서 새로 올라온 기사만 SQLite DB에 적재하는 감시 스크립트.
Usage:
  python watch_naver_news.py                          # 정치(100) 섹션, 180초 주기로 계속 감시
  python watch_naver_news.py --sections 100,101,105    # 여러 섹션 동시 감시
  python watch_naver_news.py --interval 60             # 폴링 주기 변경
  python watch_naver_news.py --once                    # 한 번만 수집하고 종료 (테스트/크론용)
"""

import argparse
import asyncio
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

DB_PATH = Path(__file__).parent / "naver_news.db"
SECTION_NAMES = {
    "100": "정치", "101": "경제", "102": "사회",
    "103": "생활/문화", "104": "세계", "105": "IT/과학",
}
THUMBNAIL_DATE_RE = re.compile(r"/(\d{4})/(\d{2})/(\d{2})/")

# is_blind = 헤드라인 캐러셀의 비활성(숨김) 슬라이드라 실제 화면엔 없음 -> 제외.
SCHEMA = {
    "name": "NaverNewsArticle",
    "baseSelector": ".sa_item:not(.is_blind)",
    "fields": [
        {"name": "title", "selector": ".sa_text_title .sa_text_strong", "type": "text"},
        {"name": "link", "selector": "a.sa_text_title", "type": "attribute", "attribute": "href"},
        {"name": "summary", "selector": ".sa_text_lede", "type": "text"},
        {"name": "press", "selector": ".sa_text_press", "type": "text"},
        {"name": "thumbnail", "selector": ".sa_thumb img", "type": "attribute", "attribute": "src"},
    ],
}


def init_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section TEXT NOT NULL,
            title TEXT,
            link TEXT NOT NULL UNIQUE,
            summary TEXT,
            press TEXT,
            thumbnail TEXT,
            article_date TEXT,
            first_seen_at TEXT NOT NULL
        )
        """
    )
    # 이전 스키마로 만들어진 DB에 comment_count 컬럼이 남아있으면 제거 (SQLite 3.35+)
    columns = [row[1] for row in conn.execute("PRAGMA table_info(articles)")]
    if "comment_count" in columns:
        conn.execute("ALTER TABLE articles DROP COLUMN comment_count")
    conn.commit()
    return conn


async def fetch_section(crawler: AsyncWebCrawler, section: str) -> list[dict]:
    url = f"https://news.naver.com/section/{section}"
    config = CrawlerRunConfig(
        extraction_strategy=JsonCssExtractionStrategy(SCHEMA),
        wait_for="css:.sa_item",
        cache_mode=CacheMode.BYPASS,
    )
    result = await crawler.arun(url=url, config=config)
    return json.loads(result.extracted_content) if result.extracted_content else []


def save_new_articles(conn: sqlite3.Connection, section: str, articles: list[dict]) -> int:
    now = datetime.now(timezone.utc).isoformat()
    new_count = 0
    for a in articles:
        link = a.get("link")
        if not link:
            continue
        thumb = a.get("thumbnail")
        m = THUMBNAIL_DATE_RE.search(thumb) if thumb else None
        article_date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None
        try:
            conn.execute(
                """INSERT INTO articles
                   (section, title, link, summary, press, thumbnail, article_date, first_seen_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    section,
                    a.get("title"),
                    link,
                    a.get("summary"),
                    a.get("press"),
                    thumb,
                    article_date,
                    now,
                ),
            )
            new_count += 1
        except sqlite3.IntegrityError:
            pass  # link UNIQUE 제약 -> 이미 저장된 기사는 건너뜀
    conn.commit()
    return new_count


async def run_cycle(crawler: AsyncWebCrawler, conn: sqlite3.Connection, sections: list[str]) -> int:
    cycle_new = 0
    for section in sections:
        name = SECTION_NAMES.get(section, section)
        try:
            articles = await fetch_section(crawler, section)
        except Exception as e:
            print(f"[{name}] 크롤링 실패: {e}")
            continue
        added = save_new_articles(conn, section, articles)
        cycle_new += added
        if added:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [{name}] 새 기사 {added}건 추가")
    return cycle_new


async def watch(sections: list[str], interval: int, once: bool) -> None:
    conn = init_db()
    print(f"DB: {DB_PATH}")
    print(f"감시 섹션: {[SECTION_NAMES.get(s, s) for s in sections]}")
    if not once:
        print(f"주기: {interval}초 (Ctrl+C로 종료)\n")

    async with AsyncWebCrawler() as crawler:
        if once:
            added = await run_cycle(crawler, conn, sections)
            print(f"완료. 새 기사 {added}건 저장됨.")
        else:
            while True:
                cycle_new = await run_cycle(crawler, conn, sections)
                if cycle_new == 0:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 새 기사 없음")
                await asyncio.sleep(interval)

    conn.close()


def main():
    parser = argparse.ArgumentParser(description="네이버 뉴스 실시간 감시 크롤러")
    parser.add_argument("--sections", default="100", help="쉼표로 구분된 섹션 코드 (예: 100,101,102)")
    parser.add_argument("--interval", type=int, default=180, help="폴링 주기(초), 기본 180초")
    parser.add_argument("--once", action="store_true", help="한 번만 수집하고 종료")
    args = parser.parse_args()

    sections = [s.strip() for s in args.sections.split(",") if s.strip()]

    try:
        asyncio.run(watch(sections, args.interval, args.once))
    except KeyboardInterrupt:
        print("\n종료됨.")


if __name__ == "__main__":
    main()
