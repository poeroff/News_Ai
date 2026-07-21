import re
from datetime import timedelta, timezone

KST = timezone(timedelta(hours=9))

# 제목 임베딩 코사인 유사도가 이 값 이상이면 같은 사건(클러스터)으로 간주
CLUSTER_SIM_THRESHOLD = 0.85

# 네이버 뉴스 썸네일 URL에 박혀있는 업로드 날짜(YYYY/MM/DD)를 뽑아내는 정규식
THUMBNAIL_DATE_RE = re.compile(r"/(\d{4})/(\d{2})/(\d{2})/")

# 네이버 뉴스 섹션 목록 페이지(news.naver.com/section/<id>) 공통 레이아웃.
# is_blind = 헤드라인 캐러셀의 비활성(숨김) 슬라이드라 실제 화면엔 없음 -> 제외.
NAVER_SECTION_SCHEMA = {
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

# 폴링 사이 급증하는 기사량 때문에 화면 상단 목록에서만 긁으면 페이지 밖으로 밀려난
# 기사를 놓칠 수 있어 "더보기" 버튼을 미리 몇 번 눌러 노출 범위를 넓혀둔다.
JS_LOAD_MORE = """
for (let i = 0; i < 3; i++) {
    const btn = document.querySelector('.section_more_inner._CONTENT_LIST_LOAD_MORE_BUTTON');
    if (btn) {
        btn.click();
        await new Promise(r => setTimeout(r, 1500));
    }
}
"""


def naver_section_url(section_id: str) -> str:
    return f"https://news.naver.com/section/{section_id}"


def naver_breakingnews_url(major_id: str, minor_id: str) -> str:
    return f"https://news.naver.com/breakingnews/section/{major_id}/{minor_id}"
