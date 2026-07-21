import asyncio
import os
from dataclasses import dataclass
from datetime import datetime

import requests
from fastapi import FastAPI

from ..crawlers import KST


APP_KEY = os.environ["APPKEY"]
APP_SECRET = os.environ["APPSECRET"]


@dataclass
class KISTokenCache:
    access_token: str | None = None
    expires_at: datetime | None = None

    @property
    def is_valid(self) -> bool:
        return (
            self.access_token is not None
            and self.expires_at is not None
            and datetime.now(KST) < self.expires_at
        )


def _fetch_access_token() -> tuple[str, datetime]:
    res = requests.post(
        f"{os.environ['KIS_BASE_URL']}/oauth2/tokenP",
        json={
            "grant_type": "client_credentials",
            "appkey": os.environ["APPKEY"],
            "appsecret": os.environ["APPSECRET"],
        },
        timeout=10,
    )
    res.raise_for_status()
    data = res.json()
    # KIS가 응답에 실제 만료 시각을 내려주므로 직접 계산하지 않고 그대로 신뢰한다
    expires_at = datetime.strptime(data["access_token_token_expired"], "%Y-%m-%d %H:%M:%S").replace(
        tzinfo=KST
    )
    return data["access_token"], expires_at


async def refresh_kis_token_job(app: FastAPI) -> None:
    # 한국투자증권 접근 토큰은 발급 후 24시간 유효 -> 매일 00시에 갱신해서 app.state에 캐싱
    try:
        token, expires_at = await asyncio.to_thread(_fetch_access_token)
        app.state.kis_token = KISTokenCache(access_token=token, expires_at=expires_at)
        print(f"[KIS 토큰] 갱신 성공 (만료: {expires_at})")
    except Exception as e:
        print(f"[KIS 토큰] 갱신 실패: {e}")


def get_valid_token(app: FastAPI) -> str | None:
    cache: KISTokenCache = app.state.kis_token
    return cache.access_token if cache.is_valid else None
