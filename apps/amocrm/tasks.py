import logging

from celery import shared_task

from . import sync

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def sync_pipelines(self):
    try:
        return {"synced": sync.sync_pipelines()}
    except Exception as exc:
        logger.error("Pipeline sinxronlashda xatolik: %s", exc)
        self.retry(exc=exc, countdown=60)

@shared_task(bind=True, max_retries=3)
def sync_users(self):
    try:
        return {"synced": sync.sync_users()}
    except Exception as exc:
        logger.error("Foydalanuvchi sinxronlashda xatolik: %s", exc)
        self.retry(exc=exc, countdown=60)

@shared_task(bind=True, max_retries=3)
def sync_leads(self):
    try:
        return {"synced": sync.sync_leads()}
    except Exception as exc:
        logger.error("Lead sinxronlashda xatolik: %s", exc)
        self.retry(exc=exc, countdown=60)

@shared_task(bind=True, max_retries=3)
def sync_contacts(self):
    try:
        return {"synced": sync.sync_contacts()}
    except Exception as exc:
        logger.error("Kontakt sinxronlashda xatolik: %s", exc)
        self.retry(exc=exc, countdown=60)

@shared_task
def sync_all():
    return sync.sync_all_now()
