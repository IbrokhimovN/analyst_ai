"""AmoCRM Celery tasklari.

Sinxronlash mantig'i `apps.amocrm.sync` modulida — bu tasklar faqat
shu funksiyalarni Celery kontekstida (retry bilan) o'rab ishga tushiradi.
Shu sababli avto-sinxronlash (Celery Beat) ham qo'lda sinxronlash bilan
bir xil to'liq ma'lumotni tortadi.
"""
import logging

from celery import shared_task

from . import sync

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def sync_pipelines(self):
    """Pipeline va statuslarni sinxronlash."""
    try:
        return {"synced": sync.sync_pipelines()}
    except Exception as exc:
        logger.error("Pipeline sinxronlashda xatolik: %s", exc)
        self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def sync_users(self):
    """AmoCRM foydalanuvchilarini (menejerlarni) sinxronlash."""
    try:
        return {"synced": sync.sync_users()}
    except Exception as exc:
        logger.error("Foydalanuvchi sinxronlashda xatolik: %s", exc)
        self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def sync_leads(self):
    """Leadlarni sinxronlash — loss_reason va FK lar bilan."""
    try:
        return {"synced": sync.sync_leads()}
    except Exception as exc:
        logger.error("Lead sinxronlashda xatolik: %s", exc)
        self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def sync_contacts(self):
    """Kontaktlarni sinxronlash."""
    try:
        return {"synced": sync.sync_contacts()}
    except Exception as exc:
        logger.error("Kontakt sinxronlashda xatolik: %s", exc)
        self.retry(exc=exc, countdown=60)


@shared_task
def sync_all():
    """Barcha ma'lumotlarni sinxronlash (Celery Beat orqali har 15 daqiqada).

    Ketma-ket bajariladi (pipelines → users → leads → contacts), chunki
    lead FK lari pipeline'ga bog'liq.
    """
    return sync.sync_all_now()
