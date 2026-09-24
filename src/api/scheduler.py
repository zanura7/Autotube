import os
from pathlib import Path

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.db.database import DATA_DIR

DATA_DIR.mkdir(parents=True, exist_ok=True)
jobstore_url = os.getenv(
    "AUTOTUBE_JOBSTORE_URL",
    f"sqlite:///{(Path(DATA_DIR) / 'jobs.sqlite').as_posix()}",
)

scheduler = AsyncIOScheduler(
    jobstores={"default": SQLAlchemyJobStore(url=jobstore_url)},
    timezone=os.getenv("AUTOTUBE_TIMEZONE", "UTC"),
)
