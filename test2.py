import io
import sys

import pandas as pd
import requests

sys.stdout.reconfigure(encoding="utf-8")

# KIND(한국거래소 상장공시시스템) 상장법인목록 다운로드
KIND_CORP_LIST_URL = "https://kind.krx.co.kr/corpgeneral/corpList.do?method=download"


def get_listed_companies() -> pd.DataFrame:
    res = requests.get(KIND_CORP_LIST_URL, timeout=10)
    res.raise_for_status()
    # 실제로는 HTML 테이블이 .xls 확장자로 내려오므로 read_html로 파싱, EUC-KR 인코딩
    df = pd.read_html(io.BytesIO(res.content), encoding="euc-kr", header=0)[0]
    # 종목코드는 6자리 숫자 문자열로 유지 (앞자리 0 보존)
    df["종목코드"] = df["종목코드"].astype(str).str.zfill(6)
    return df


if __name__ == "__main__":
    df = get_listed_companies()
    print(df.shape)
    print(df.head())
    print(df[df["회사명"] == "SK하이닉스"])

