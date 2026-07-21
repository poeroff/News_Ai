import os
import sys

import requests
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

# 금융위원회_KRX상장종목정보 (data.go.kr publicDataPk=15094775)
BASE_URL = "http://apis.data.go.kr/1160100/service/GetKrxListedInfoService/getItemInfo"


def get_item_info(
    *,
    like_itms_nm: str | None = None,   # 종목명 (부분검색)
    isin_cd: str | None = None,        # ISIN코드 (완전검색)
    bas_dt: str | None = None,         # 기준일자 YYYYMMDD
    num_of_rows: int = 10,
    page_no: int = 1,
) -> dict:
    service_key = os.environ["DATA_GO_KR_SERVICE_KEY"]
    params = {
        "serviceKey": service_key,
        "resultType": "json",
        "numOfRows": num_of_rows,
        "pageNo": page_no,
    }
    if like_itms_nm:
        params["likeItmsNm"] = like_itms_nm
    if isin_cd:
        params["isinCd"] = isin_cd
    if bas_dt:
        params["basDt"] = bas_dt

    res = requests.get(BASE_URL, params=params, timeout=10)
    res.raise_for_status()
    return res.json()


if __name__ == "__main__":
    data = get_item_info(like_itms_nm="SK하이닉스")
    items = data["response"]["body"]["items"].get("item", [])
    for item in items:
        print(item)
