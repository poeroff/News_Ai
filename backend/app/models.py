from sqlalchemy import ForeignKey, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Article(Base):
    __tablename__ = "articles"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    section: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str | None] = mapped_column(String(500))
    link: Mapped[str] = mapped_column(String(768), nullable=False, unique=True)
    summary: Mapped[str | None] = mapped_column(Text)
    press: Mapped[str | None] = mapped_column(String(255))
    thumbnail: Mapped[str | None] = mapped_column(String(1000))
    article_date: Mapped[str | None] = mapped_column(String(50))
    # 같은 사건으로 묶인 기사들이 공유하는 값 (그 클러스터 대표 기사의 id)
    cluster_id: Mapped[int | None] = mapped_column(
        ForeignKey("articles.id"), index=True
    )
    # jhgan/ko-sroberta-multitask 임베딩 벡터 (float32, 768차원) 바이너리
    embedding: Mapped[bytes | None] = mapped_column(LargeBinary)


class Stock(Base):
    __tablename__ = "stocks"
    stock_code: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    market: Mapped[str | None] = mapped_column(String(50))
    industry: Mapped[str | None] = mapped_column(String(255))
    main_products: Mapped[str | None] = mapped_column(String(500))
    listed_date: Mapped[str | None] = mapped_column(String(50))
    settlement_month: Mapped[str | None] = mapped_column(String(20))
    ceo_name: Mapped[str | None] = mapped_column(String(255))
    homepage: Mapped[str | None] = mapped_column(String(500))
    region: Mapped[str | None] = mapped_column(String(100))


class StockArticle(Base):
    __tablename__ = "stock_articles"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(
        String(10), ForeignKey("stocks.stock_code"), nullable=False, index=True
    )
    title: Mapped[str | None] = mapped_column(String(500))
    link: Mapped[str] = mapped_column(String(768), nullable=False, unique=True)
    summary: Mapped[str | None] = mapped_column(Text)
    thumbnail: Mapped[str | None] = mapped_column(String(1000))
    # 기사 상세 페이지에서 긁은 본문 전체 (LLM 호재/악재 판별용)
    body: Mapped[str | None] = mapped_column(Text)
    # LLM이 본문+등락률+날짜를 보고 "예측하는 말투"로 생성한 코멘트 (파인튜닝용 정답 라벨)
    llm_summary: Mapped[str | None] = mapped_column(Text)
    change_percent: Mapped[str | None] = mapped_column(String(20))
    change_direction: Mapped[str | None] = mapped_column(String(10))
    article_date: Mapped[str | None] = mapped_column(String(50))
    # article_date는 날짜 필터링(WHERE article_date == today)에 쓰여서 형식을 못 바꾸니
    # 시각(HH:MM)은 LLM 프롬프트용으로 별도 컬럼에 보관
    article_time: Mapped[str | None] = mapped_column(String(10))
