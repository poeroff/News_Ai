import asyncio
import json
from datetime import datetime

import numpy as np
from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
from sqlalchemy import select, update
from sqlalchemy.dialects.mysql import insert as mysql_insert

from ..database import AsyncSessionLocal
from ..models import Article
from .embeddings import cosine_sim_batch, embed, normalize_title
from .naver_common import (
    CLUSTER_SIM_THRESHOLD,
    JS_LOAD_MORE,
    KST,
    NAVER_SECTION_SCHEMA,
    THUMBNAIL_DATE_RE,
    naver_breakingnews_url,
    naver_section_url,
)

MAIN_SECTIONS = {
    "101": "경제",
    "104": "세계",
    "105": "IT/과학",
}

# 경제(101) 하위 카테고리 - news.naver.com/breakingnews/section/101/<id>
ECONOMY_SUBSECTIONS = {
    "259": "금융",
    "258": "증권",
    "261": "산업/재계",
    "771": "중기/벤처",
    "260": "부동산",
    "262": "글로벌 경제",
    "310": "생활경제",
    "263": "경제 일반",
}

# IT/과학(105) 하위 카테고리 - news.naver.com/breakingnews/section/105/<id>
IT_SCIENCE_SUBSECTIONS = {
    "731": "모바일",
    "226": "인터넷/SNS",
    "227": "통신/뉴미디어",
    "230": "IT 일반",
    "732": "보안/해킹",
    "283": "컴퓨터",
    "229": "게임/리뷰",
    "228": "과학 일반",
}

# 세계(104) 하위 카테고리 - news.naver.com/breakingnews/section/104/<id>
WORLD_SUBSECTIONS = {
    "231": "아시아/호주",
    "232": "미국/중남미",
    "233": "유럽",
    "234": "중동/아프리카",
    "322": "세계 일반",
}

# (section_id, 이름, URL) 목록. section_id는 DB의 section 컬럼 값으로 그대로 저장됨.
SECTIONS: list[tuple[str, str, str]] = (
    [(sid, name, naver_section_url(sid)) for sid, name in MAIN_SECTIONS.items()]
    + [
        (sid, name, naver_breakingnews_url("101", sid))
        for sid, name in ECONOMY_SUBSECTIONS.items()
    ]
    + [
        (sid, name, naver_breakingnews_url("105", sid))
        for sid, name in IT_SCIENCE_SUBSECTIONS.items()
    ]
    + [
        (sid, name, naver_breakingnews_url("104", sid))
        for sid, name in WORLD_SUBSECTIONS.items()
    ]
)


async def fetch_section(crawler: AsyncWebCrawler, url: str) -> list[dict]:
    config = CrawlerRunConfig(
        extraction_strategy=JsonCssExtractionStrategy(NAVER_SECTION_SCHEMA),
        js_code=JS_LOAD_MORE,
        wait_for="css:.sa_item",
        cache_mode=CacheMode.BYPASS,
    )
    # crawl4ai/Playwright가 드물게 응답 없이 멈추는 경우가 있어, 이벤트 루프 전체가
    # 물리는 걸 막기 위해 자체적으로 타임아웃을 걸어 다음 섹션으로 넘어가게 한다.
    result = await asyncio.wait_for(crawler.arun(url=url, config=config), timeout=60)
    return json.loads(result.extracted_content) if result.extracted_content else []


def _today_str_kst() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d")


async def _load_todays_clusters(session, section_id: str) -> list[tuple[int, int, np.ndarray]]:
    today = _today_str_kst()
    rows = (
        await session.execute(
            select(Article.id, Article.cluster_id, Article.embedding).where(
                Article.section == section_id,
                Article.article_date == today,
                Article.embedding.is_not(None),
            )
        )
    ).all()
    return [(r.id, r.cluster_id, np.frombuffer(r.embedding, dtype=np.float32)) for r in rows]


async def save_new_articles(section_id: str, articles: list[dict]) -> int:
    new_count = 0
    async with AsyncSessionLocal() as session:
        clusters = await _load_todays_clusters(session, section_id)
        for a in articles:
            link = a.get("link")
            if not link:
                continue
            thumb = a.get("thumbnail")
            m = THUMBNAIL_DATE_RE.search(thumb) if thumb else None
            article_date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else _today_str_kst()

            title = a.get("title") or ""
            norm_title = normalize_title(title)
            vec = await asyncio.to_thread(embed, norm_title) if norm_title else None

            # 같은 섹션의 오늘(00시 KST 이후) 기사들과 제목 임베딩 코사인 유사도를 비교해
            # 같은 사건이면 대표 기사의 cluster_id를 물려받고, 새 사건이면 자기 자신의 id로 새 클러스터를 만든다.
            cluster_id = None
            if vec is not None and clusters:
                matrix = np.stack([c[2] for c in clusters])
                sims = cosine_sim_batch(vec, matrix)
                best = int(np.argmax(sims))
                if sims[best] >= CLUSTER_SIM_THRESHOLD:
                    cluster_id = clusters[best][1]

            # link UNIQUE 제약 -> 이미 저장된 기사는 무시 (INSERT IGNORE)
            stmt = (
                mysql_insert(Article)
                .values(
                    section=section_id,
                    title=title,
                    link=link,
                    summary=a.get("summary"),
                    press=a.get("press"),
                    thumbnail=thumb,
                    article_date=article_date,
                    cluster_id=cluster_id,
                    embedding=vec.tobytes() if vec is not None else None,
                )
                .prefix_with("IGNORE")
            )
            result = await session.execute(stmt)
            if result.rowcount:
                new_count += 1
                new_id = result.inserted_primary_key[0]
                if cluster_id is None:
                    await session.execute(
                        update(Article).where(Article.id == new_id).values(cluster_id=new_id)
                    )
                    cluster_id = new_id
                if vec is not None:
                    clusters.append((new_id, cluster_id, vec))
        await session.commit()
    return new_count


async def refresh_sections_job() -> None:
    async with AsyncWebCrawler() as crawler:
        for section_id, name, url in SECTIONS:
            try:
                articles = await fetch_section(crawler, url)
                await save_new_articles(section_id, articles)
            except Exception as e:
                print(f"[{name}] 크롤링 실패: {e}")
