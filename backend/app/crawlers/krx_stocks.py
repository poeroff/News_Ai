import asyncio
import io

import pandas as pd
import requests
from sqlalchemy.dialects.mysql import insert as mysql_insert

from ..database import AsyncSessionLocal
from ..models import Stock

# KIND(한국거래소 상장공시시스템) 상장법인목록 다운로드
KIND_CORP_LIST_URL = "https://kind.krx.co.kr/corpgeneral/corpList.do?method=download"

COLUMN_MAP = {
    "회사명": "name",
    "시장구분": "market",
    "종목코드": "stock_code",
    "업종": "industry",
    "주요제품": "main_products",
    "상장일": "listed_date",
    "결산월": "settlement_month",
    "대표자명": "ceo_name",
    "홈페이지": "homepage",
    "지역": "region",
}


def _fetch_listed_companies() -> list[dict]:
    res = requests.get(KIND_CORP_LIST_URL, timeout=30)
    res.raise_for_status()
    # 실제로는 HTML 테이블이 .xls 확장자로 내려오므로 read_html로 파싱, EUC-KR 인코딩
    # BytesIO로 감싸지 않으면 pandas가 바이트 내용을 파일 경로로 오인해 FileNotFoundError 발생 (pandas>=3.0)
    df = pd.read_html(io.BytesIO(res.content), encoding="euc-kr", header=0)[0]
    # 종목코드는 6자리 숫자 문자열로 유지 (앞자리 0 보존)
    df["종목코드"] = df["종목코드"].astype(str).str.zfill(6)
    df = df.rename(columns=COLUMN_MAP)[list(COLUMN_MAP.values())]
    rows = df.to_dict(orient="records")
    # 빈 셀은 float NaN으로 남는데 MySQL 드라이버가 이를 받아들이지 못해 None으로 치환
    for row in rows:
        for key, value in row.items():
            if pd.isna(value):
                row[key] = None
    return rows


async def save_stocks(rows: list[dict]) -> int:
    if not rows:
        return 0
    async with AsyncSessionLocal() as session:
        stmt = mysql_insert(Stock).values(rows)
        # 종목코드가 이미 있으면 나머지 컬럼을 최신 정보로 덮어씀 (매일 전체 목록 재수집)
        update_cols = {
            col: stmt.inserted[col] for col in COLUMN_MAP.values() if col != "stock_code"
        }
        stmt = stmt.on_duplicate_key_update(**update_cols)
        await session.execute(stmt)
        await session.commit()
    return len(rows)


async def refresh_stocks() -> int:
    rows = await asyncio.to_thread(_fetch_listed_companies)
    return await save_stocks(rows)


async def refresh_stocks_job() -> None:
    # APScheduler(CronTrigger)가 월~금 09:00(KST)에 호출하는 잡. 잡 콜백에서 예외가
    # 새면 스케줄러가 죽지 않고 로깅만 하지만, 기존 크롤러들과 로그 포맷을 맞추기 위해 직접 처리.
    try:
        count = await refresh_stocks()
        print(f"[상장종목] {count}건 갱신")
    except Exception as e:
        print(f"[상장종목] 갱신 실패: {e}")
