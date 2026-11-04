import logging
from concurrent.futures import ThreadPoolExecutor
from threading import BoundedSemaphore
from uuid import uuid4

from sqlalchemy import select

from backend.db import Job, now

logger = logging.getLogger(__name__)


class QueueFull(RuntimeError):
    pass


class LocalRunner:
    """One worker, bounded admission, persistent states. One API process only."""

    def __init__(self, factory, capacity=4):
        self.factory = factory
        self.slots = BoundedSemaphore(capacity)
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="pitchsight")
        with factory.begin() as session:
            for job in session.scalars(select(Job).where(Job.state.in_(["queued", "running"]))):
                job.state, job.error, job.updated_at = (
                    "failed",
                    "Interrupted by application restart; submit again",
                    now(),
                )

    def submit(self, incident_id, kind, operation):
        if not self.slots.acquire(blocking=False):
            raise QueueFull("Local queue full; retry after a job completes")
        jid = uuid4().hex
        try:
            with self.factory.begin() as session:
                session.add(Job(id=jid, incident_id=incident_id, kind=kind, state="queued"))
            self.pool.submit(self._run, jid, operation)
        except Exception:
            self.slots.release()
            raise
        return jid

    def _update(self, jid, **values):
        with self.factory.begin() as session:
            job = session.get(Job, jid)
            for key, value in values.items():
                setattr(job, key, value)
            job.updated_at = now()

    def _run(self, jid, operation):
        try:
            self._update(jid, state="running", progress=5)
            operation(lambda progress: self._update(jid, progress=progress))
            self._update(jid, state="completed", progress=100)
        except Exception as exc:
            logger.exception("Job %s failed", jid)
            message = (
                str(exc)
                if isinstance(exc, ValueError)
                else "Processing failed; see local server log"
            )
            self._update(jid, state="failed", error=message)
        finally:
            self.slots.release()

    def close(self):
        self.pool.shutdown(wait=True)
