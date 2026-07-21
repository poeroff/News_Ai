import os
import sys

import requests
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

BASE_URL = "https://openapi.koreainvestment.com:9443"

APP_KEY = os.environ["KIS_APP_KEY"]
APP_SECRET = os.environ["KIS_APP_SECRET"]


def get_access_token() -> str:
    res = requests.post(
        f"{BASE_URL}/oauth2/tokenP",
        json={
            "grant_type": "client_credentials",
            "appkey": APP_KEY,
            "appsecret": APP_SECRET,
        },
        timeout=10,
    )
    res.raise_for_status()
    return res.json()["access_token"]


def get_stock_price(access_token: str, stock_code: str) -> dict:
    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {access_token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        # 주식현재가 시세(실전투자) tr_id
        "tr_id": "FHKST01010100",
        "custtype": "P",
    }
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": stock_code,
    }
    res = requests.get(
        f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-price",
        headers=headers,
        params=params,
        timeout=10,
    )
    res.raise_for_status()
    return res.json()


if __name__ == "__main__":
    token = get_access_token()
    print("access_token 발급 성공:", token[:20], "...")

    data = get_stock_price(token, "000660")  # SK하이닉스
    output = data.get("output", {})
    print("전체 응답:", data)
    print()
    print("현재가:", output.get("stck_prpr"))
    print("전일대비:", output.get("prdy_vrss"))
    print("전일대비 부호:", output.get("prdy_vrss_sign"))
    print("전일대비율(change_percent):", output.get("prdy_ctrt"))
