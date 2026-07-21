import requests

# docker-compose 내부 네트워크에서는 서비스명:컨테이너 내부 포트로 접근 (호스트용 8001 아님)
VLLM_BASE_URL = "http://vllm:8000/v1"
MODEL_NAME = "Qwen/Qwen2.5-14B-Instruct-AWQ"

_DIRECTION_KR = {"up": "상승", "down": "하락", "flat": "보합"}

# 파인튜닝용 정답 라벨을 만드는 프롬프트. 실제로는 결과(등락률)를 이미 알고 만들지만,
# 라벨 자체는 "예측하는 말투"로 써야 나중에 결과를 모르는 새 기사에 대해서도 모델이
# 같은 말투로 예측을 내놓게 된다 (사후 보고체로 학습시키면 추론 때 이상해짐).
#
# 주의: 실제 결과를 "참고사항"처럼 괄호로 약하게 넣었더니, 기사 내용이 강하게 긍정적/부정적일 때
# 모델이 실제 결과를 무시하고 기사 톤만 따라가 반대 방향으로 예측하는 경우가 있었다 (예: 실제로는
# -13% 급락했는데 "10~15% 상승 전망"이라고 씀). 그래서 실제 결과를 프롬프트 맨 앞/맨 뒤에 "반드시
# 지켜야 할 조건"으로 명시하고, 기사 톤과 실제 결과가 어긋나면 "재료소멸/이미 선반영" 논리로
# 풀어쓰라고 구체적으로 지시한다.
_PROMPT_TEMPLATE = """다음은 {article_date} {article_time}에 보도된 한 종목 관련 뉴스 기사 본문이다.

[실제 결과 - 반드시 지킬 것] 이 종목은 이 기사가 보도된 날 실제로 {change_percent}% {direction}했다.

애널리스트가 되어 이 기사를 근거로 이 종목 주가를 예측하는 코멘트를 작성해라. 아래 조건을 모두 반드시 지켜라:

1. 코멘트가 제시하는 예측 방향과 수치는 반드시 위 [실제 결과]와 일치해야 한다. 기사 내용이 아무리 긍정적으로 \
보여도 실제 결과가 하락이면 하락을, 아무리 부정적으로 보여도 실제 결과가 상승이면 상승을 예측해라. \
기사 톤과 실제 결과가 반대라면 "이미 선반영되어 있었다", "재료가 소멸됐다", "차익실현 매물이 나왔다", \
"시장이 이번 소식을 예상보다 약하게 받아들였다"처럼 실제 결과에 맞는 논리로 풀어서 설명해라. \
실제 결과와 반대되는 예측을 절대 쓰지 마라.
2. 언제, 어떤 뉴스가 나왔는지 (기사 날짜·시각과 핵심 내용)를 포함해라.
3. 왜 그 방향으로 움직일 것으로 보이는지 근거를 제시해라.
4. 주가가 대략 몇 % 정도 움직일 것으로 예상되는지 실제 수치와 비슷한 구체적인 수치로 제시해라.

문체 조건: 반드시 "~할 것으로 보인다", "~할 전망이다", "~할 가능성이 높다"처럼 아직 일어나지 않은 일을 예측하는 \
말투로 써라. "~했다", "주가가 올랐다"처럼 이미 벌어진 결과를 보고하는 말투는 쓰지 마라. 단, [실제 결과]의 \
구체적인 수치·방향을 답변에 그대로 노출하지는 마라 (자연스러운 예측처럼 보이게).

본문: {body}

다시 한번 강조: 이 코멘트가 예측하는 등락 방향은 반드시 {direction}이어야 하고, 수치는 {change_percent}%와 \
비슷해야 한다. 예측 코멘트만 출력하고 다른 설명은 붙이지 마라.
"""


def generate_predictive_summary(
    body: str,
    change_percent: str,
    direction: str,
    article_date: str,
    article_time: str,
) -> str:
    # 뉴스 기사는 항상 실제 게재 날짜·시각이 있다. 여기 None이 들어온다면 그건 "모르는 게
    # 정상"이 아니라 크롤러가 못 채운 데이터 결함이므로, 호출하는 쪽(price.py)에서
    # 이 값들이 다 갖춰진 기사만 걸러서 넘겨야 한다 (가짜 문자열로 때우지 않음).
    prompt = _PROMPT_TEMPLATE.format(
        article_date=article_date,
        article_time=article_time,
        # Qwen2.5는 원래 32K 토큰까지 지원하고, vLLM도 --max-model-len 16384로 띄워둬서
        # 본문을 자르지 않고 전체를 넣는다 (뒷부분에 핵심 내용이 있을 수 있으므로)
        body=body,
        change_percent=change_percent,
        direction=_DIRECTION_KR.get(direction, direction),
    )
    res = requests.post(
        f"{VLLM_BASE_URL}/chat/completions",
        json={
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": 400,
        },
        timeout=60,
    )
    res.raise_for_status()
    return res.json()["choices"][0]["message"]["content"].strip()
