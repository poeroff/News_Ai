from contextlib import asynccontextmanager
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.articles import router as articles_router
from .api.ranking import router as ranking_router
from .api.routes import router
from .crawlers.krx_stocks import refresh_stocks_job
from .crawlers.mt_stock_news import refresh_stock_news_job
from .crawlers.naver_common import KST
from .crawlers.naver_ranking import refresh_ranking_job
from .crawlers.naver_sections import refresh_sections_job
from .database import Base, engine
from .kis.auth import KISTokenCache, refresh_kis_token_job
from .kis.price import refresh_stock_change_job
from .models import Article, Stock, StockArticle  # noqa: F401  (registers the tables with Base.metadata)

scheduler = AsyncIOScheduler(timezone="Asia/Seoul")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    app.state.kis_token = KISTokenCache()
    # 매일(요일 제한 없이) 정해진 주기로 반복 - 첫 실행은 앱 기동 즉시, 이후 interval마다
    # 컨테이너 OS 타임존이 UTC라 datetime.now()는 naive UTC 시각을 반환하므로,
    # 반드시 타임존 정보(KST)를 붙여야 스케줄러가 다른 타임존으로 오인하지 않는다.
    now = datetime.now(KST)
    scheduler.add_job(refresh_sections_job, IntervalTrigger(seconds=180), next_run_time=now, id="sections")
    scheduler.add_job(refresh_ranking_job, IntervalTrigger(seconds=600), next_run_time=now, id="ranking")
    scheduler.add_job(refresh_stock_news_job, IntervalTrigger(seconds=60), next_run_time=now, id="stock_news")
    # 상장종목 목록만 월~금 09:00(KST)에 한 번씩
    # CronTrigger는 scheduler의 timezone을 자동으로 물려받지 않고 기본값(UTC)을 쓰므로 명시해야 함
    scheduler.add_job(
        refresh_stocks_job,
        CronTrigger(day_of_week="mon-fri", hour=9, minute=0, timezone="Asia/Seoul"),
        id="stocks",
    )
    # KIS 접근 토큰은 발급 후 24시간 유효 -> 매일 00시에 갱신 (앱 기동 시에도 즉시 한 번 캐싱)
    scheduler.add_job(
        refresh_kis_token_job,
        CronTrigger(hour=0, minute=0, timezone="Asia/Seoul"),
        args=[app],
        next_run_time=now,
        id="kis_token",
    )
    # 장 마감 후 당일 종목뉴스에 등락률 채워넣기 (매일 20:00 KST)
    scheduler.add_job(
        refresh_stock_change_job,
        CronTrigger(hour=00, minute=52, timezone="Asia/Seoul"),
        args=[app],
        id="stock_change",
    )
    
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
app.include_router(router)
app.include_router(ranking_router)
app.include_router(articles_router)
