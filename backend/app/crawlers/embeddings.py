import re

import numpy as np
from sentence_transformers import SentenceTransformer

_model: SentenceTransformer | None = None

# 언론사마다 붙이는 [속보], (종합), 따옴표 등은 실제 의미 비교에 방해가 되므로 제거
_TITLE_NOISE_RE = re.compile(r"[\[(【][^\])】]{0,20}[\])】]|[\"'“”‘’]")


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("jhgan/ko-sroberta-multitask")
    return _model


def normalize_title(title: str) -> str:
    cleaned = _TITLE_NOISE_RE.sub("", title)
    return re.sub(r"\s+", " ", cleaned).strip()


def embed(text: str) -> np.ndarray:
    # normalize_embeddings=True -> 단위벡터로 반환되어 내적(dot)이 곧 코사인 유사도
    return get_model().encode(text, normalize_embeddings=True).astype(np.float32)


def cosine_sim_batch(vec: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    return matrix @ vec
