"""The scheduled-publication pass — shipped by the library.

Wire it in the settings module itself::

    from stapel_cms.beat import get_cms_beat_schedule

    CELERY_BEAT_SCHEDULE = {**get_cms_beat_schedule(), ...}

Every minute, scheduled snapshots whose ``publish_at`` has come are promoted
(facts emitted, cache invalidated). The public read already serves a due
snapshot without the beat; the pass makes it durable and announced. Celery
is optional: ``manage.py cms_publish_due`` runs the same pass.
"""
from __future__ import annotations

PUBLISH_DUE_TASK_NAME = "stapel_cms.beat.publish_due"
PUBLISH_DUE_BEAT_KEY = "cms-publish-due"
PUBLISH_DUE_INTERVAL_SECONDS = 60


def publish_due() -> int:
    """One promotion pass. A plain callable for hosts without Celery."""
    from .services.content import promote_due

    return promote_due()


def get_cms_beat_schedule() -> dict:
    """Beat entry for the pass. Add to ``CELERY_BEAT_SCHEDULE``."""
    return {PUBLISH_DUE_BEAT_KEY: {"task": PUBLISH_DUE_TASK_NAME, "schedule": float(PUBLISH_DUE_INTERVAL_SECONDS)}}


try:  # pragma: no cover - exercised by whichever profile the host installs
    from celery import shared_task
except ImportError:
    pass
else:
    publish_due = shared_task(name=PUBLISH_DUE_TASK_NAME)(publish_due)


__all__ = ["PUBLISH_DUE_BEAT_KEY", "PUBLISH_DUE_TASK_NAME", "get_cms_beat_schedule", "publish_due"]
