import asyncio
import os
from datetime import datetime

import requests
from fastapi import FastAPI
from sqlalchemy import select, update

from ..crawlers import KST
from ..database import AsyncSessionLocal
from ..llm.qwen import generate_predictive_summary
from ..models import StockArticle
from .auth import APP_KEY, APP_SECRET, get_valid_token

# KIS prdy_vrss_sign: 1=상한 2=상승 3=보합 4=하한 5=하락
_SIGN_TO_DIRECTION = {
    "1": "up",
    "2": "up",
    "3": "flat",
    "4": "down",
    "5": "down",
}


def _fetch_stock_price(access_token: str, stock_code: str) -> dict:
    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {access_token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "FHKST01010100",  # 주식현재가 시세(실전투자)
        "custtype": "P",
    }
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": stock_code,
    }
    res = requests.get(
        f"{os.environ['KIS_BASE_URL']}/uapi/domestic-stock/v1/quotations/inquire-price",
        headers=headers,
        params=params,
        timeout=10,
    )
    res.raise_for_status()
    return res.json()


async def refresh_stock_change_job(app: FastAPI) -> None:
    token = get_valid_token(app)
    if token is None:
        print("[전일대비율] 캐싱된 KIS 토큰이 없어 건너뜀")
        return

    today = datetime.now(KST).strftime("%Y-%m-%d")
    async with AsyncSessionLocal() as session:
        # llm_summary가 이미 채워진 기사는 다시 건드리지 않음 (하루에 여러 번 돌아도 덮어쓰기 없음)
        articles = (
            await session.execute(
                select(StockArticle).where(
                    StockArticle.article_date == today,
                    StockArticle.llm_summary.is_(None),
                )
            )
        ).scalars().all()

        # 시세는 종목당 한 번만 조회 (같은 종목 기사가 여러 개일 수 있음)
        price_cache: dict[str, tuple[str | None, str | None]] = {}
        updated = 0
        for article in articles:
            if article.stock_code not in price_cache:
                try:
                    data = await asyncio.to_thread(_fetch_stock_price, token, article.stock_code)
                    output = data.get("output", {})
                    price_cache[article.stock_code] = (
                        output.get("prdy_ctrt"),
                        _SIGN_TO_DIRECTION.get(output.get("prdy_vrss_sign")),
                    )
                except Exception as e:
                    print(f"[전일대비율] {article.stock_code} 시세 조회 실패: {e}")
                    price_cache[article.stock_code] = (None, None)
                # 장 마감 후라 값이 바뀔 일은 없으니 재시도는 안 하고, 연속 호출 부하만 줄이게 텀만 둠
                await asyncio.sleep(0.2)
            change_percent, direction = price_cache[article.stock_code]

            # 시세 -> LLM 순서: 본문 + 방금 조회한 실제 등락률/방향 + 기사 날짜·시각을 넘겨서
            # "예측하는 말투"의 코멘트를 정답 라벨(llm_summary)로 생성한다.
            # 필요한 값 중 하나라도 없으면(크롤링/시세조회 결함) 가짜 값으로 채우지 않고 건너뜀
            llm_summary = None
            if article.body and article.article_date and article.article_time and change_percent and direction:
                try:
                    llm_summary = await asyncio.to_thread(
                        generate_predictive_summary,
                        article.body,
                        change_percent,
                        direction,
                        article.article_date,
                        article.article_time,
                    )
                except Exception as e:
                    print(f"[호재악재] {article.link} 요약 실패: {e}")

            await session.execute(
                update(StockArticle)
                .where(StockArticle.id == article.id)
                .values(
                    change_percent=change_percent,
                    change_direction=direction,
                    llm_summary=llm_summary,
                )
            )
            updated += 1
        await session.commit()
    print(f"[전일대비율] {updated}건 갱신")
    
    
    
    
