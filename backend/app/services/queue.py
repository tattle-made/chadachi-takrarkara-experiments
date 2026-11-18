"""The background job queue (oban, stored in Postgres) that sends takedown emails.

One "emails" queue, one job at a time, with a short pause between sends.
The queue runs inside the app: run_queue() starts it with the app and stops it
on shutdown. Routes add jobs with enqueue_sends().

oban is async (it runs on the app's event loop), but our DB and Google code is
sync. The two meet in two places:
- oban -> our code: the worker runs send_email in a separate thread
- our routes -> oban: enqueue_sends asks the event loop to add the jobs
"""

import asyncio
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import anyio.from_thread
from oban import Job, Oban
from oban.decorators import worker
from sqlmodel import Session

from app.core.config import settings
from app.core.db import engine
from app.services.sending import send_email

QUEUE = "emails"
# 1 try + 3 retries; temporary errors wait 1, 5, then 15 minutes
MAX_ATTEMPTS = 4
RETRY_DELAYS = [60, 300, 900]


@worker(queue=QUEUE, max_attempts=MAX_ATTEMPTS)
class SendEmailWorker:
    async def process(self, job: Job) -> None:
        """Send one email. A RetryableSendError makes oban retry it later."""
        email_id = uuid.UUID(job.args["email_id"])
        last_try = job.attempt >= job.max_attempts
        # send_email is sync: it waits on the DB and Google. Run on the event
        # loop, it would freeze the whole app until it finished, so it runs in
        # a separate thread while the loop carries on
        await asyncio.to_thread(_send, email_id, last_try)
        await asyncio.sleep(settings.SEND_GAP_SECONDS)

    def backoff(self, job: Job) -> int:
        """oban asks this after a failed try: how many seconds to wait before
        the next one. job.attempt is the try that just failed (1 -> 60s,
        2 -> 300s, 3 -> 900s)."""
        return RETRY_DELAYS[min(job.attempt, len(RETRY_DELAYS)) - 1]


def _send(email_id: uuid.UUID, last_try: bool) -> None:
    """send_email with a DB session of its own."""
    with Session(engine) as session:
        send_email(session=session, email_id=email_id, last_try=last_try)


def _dsn() -> str:
    """The DB address for oban. Ours is "postgresql+psycopg://...", where
    "+psycopg" tells SQLAlchemy which driver to use; oban uses psycopg directly,
    which only understands "postgresql://..."."""
    return str(settings.SQLALCHEMY_DATABASE_URI).replace(
        "postgresql+psycopg://", "postgresql://", 1
    )


@asynccontextmanager
async def run_queue() -> AsyncGenerator[None]:
    """Run the queue while the app runs (used by the app's lifespan in main.py).

    Before the yield (startup): open a pool of DB connections for oban and
    start it, so it watches oban_jobs and runs workers. After it (shutdown):
    stop oban, which waits for a send in progress, and close the pool.
    Does nothing if QUEUE_ENABLED is off (tests, which have no Postgres).
    """
    if not settings.QUEUE_ENABLED:
        yield
        return
    pool = await Oban.create_pool(_dsn())
    try:
        async with Oban(pool=pool, queues={QUEUE: 1}):
            yield
    finally:
        await pool.close()


def enqueue_sends(email_ids: list[uuid.UUID]) -> None:
    """Add one send job per email. Call from sync routes, after committing.

    Raises RuntimeError if not called from a FastAPI worker thread or if the
    queue isn't running.
    """
    # oban's enqueue is async and lives on the event loop; sync routes run in
    # separate threads, so ask the loop to run it and wait for it to finish
    anyio.from_thread.run(_enqueue, email_ids)


async def _enqueue(email_ids: list[uuid.UUID]) -> None:
    """Insert the jobs (all in one go)."""
    # .new() is added by @worker, so type checkers don't know it
    jobs = [
        SendEmailWorker.new({"email_id": str(i)})  # type: ignore
        for i in email_ids
    ]
    await Oban.get_instance().enqueue_many(jobs)
