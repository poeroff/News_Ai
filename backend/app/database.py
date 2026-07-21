import os
import re
import sys
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

# asyncmy는 INSERT IGNORE로 스킵된 중복 키를 SQLAlchemy 로깅(echo)이 아니라
# C 레벨에서 sys.stderr.write()로 직접 찍는다 (warnings.warn/print 어느 쪽도 아님).
# 실제 에러는 그대로 두고 이 특정 메시지만 걸러낸다.
_DUPLICATE_ENTRY_RE = re.compile(r"Duplicate entry .* for key")


class _FilteredStderr:
    def __init__(self, stream):
        self._stream = stream

    def __getattr__(self, name):
        return getattr(self._stream, name)

    def write(self, text: str) -> int:
        if _DUPLICATE_ENTRY_RE.search(text):
            return len(text)
        return self._stream.write(text)


sys.stderr = _FilteredStderr(sys.stderr)

DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
