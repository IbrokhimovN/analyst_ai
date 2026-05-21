"""
Bitrix24 Sync Tasks — Bitrix24 dan ma'lumotlarni sinxronlash.

Bu tasklar alohida ishlaydi va Bitrix24 dan deallar,
kontaktlar, leadlar, va pipeline statuslarini tortib,
umumiy Lead/Contact modellariga yozadi (source='bitrix').
"""
import logging
from datetime import datetime, timezone as tz

from celery import shared_task
from dateutil import parser as dateparser
from django.utils import timezone

logger = logging.getLogger(__name__)


def _parse_bitrix_date(date_str):
    """Bitrix24 sana formatini datetime ga o'tkazish."""
    if not date_str:
        return None
    try:
        return dateparser.parse(date_str)
    except (ValueError, TypeError):
        return None


@shared_task(bind=True, max_retries=3)
def sync_bitrix_deals(self):
    """Bitrix24 dan deallarni sinxronlash → Lead modeliga (source='bitrix')."""
    from apps.crm.adapters.bitrix import Bitrix24Adapter
    from apps.amocrm.models import Lead

    try:
        adapter = Bitrix24Adapter()
        page = 1
        total_synced = 0

        while True:
            data = adapter.get_leads(page=page, limit=50)
            items = data.get("items", [])
            if not items:
                break

            for item in items:
                # Bitrix deal ID ni amocrm_id maydoniga yozamiz
                # prefix bilan ajratamiz: 1000000 + bitrix_id
                bitrix_id = item["id"]
                internal_id = 1000000 + bitrix_id

                created_at = _parse_bitrix_date(item.get("created_at"))
                updated_at = _parse_bitrix_date(item.get("updated_at"))
                closed_at = _parse_bitrix_date(item.get("closed_at"))

                Lead.objects.update_or_create(
                    amocrm_id=internal_id,
                    defaults={
                        "source": "bitrix",
                        "name": item.get("name", ""),
                        "price": item.get("price", 0),
                        "status_id": hash(item.get("stage_id", "")) % 100000,
                        "pipeline_id": int(item.get("pipeline_id", 0) or 0),
                        "responsible_user_id": item.get("responsible_user_id", 0),
                        "created_at": created_at,
                        "updated_at": updated_at,
                        "closed_at": closed_at,
                        "raw_data": item.get("raw", item),
                    }
                )
                total_synced += 1

            if not data.get("has_more"):
                break
            page += 1

        logger.info(f"Bitrix24: {total_synced} deal sinxronlandi")
        return {"synced": total_synced}

    except Exception as exc:
        logger.error(f"Bitrix24 deal sinxronlashda xatolik: {exc}")
        self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def sync_bitrix_contacts(self):
    """Bitrix24 dan kontaktlarni sinxronlash."""
    from apps.crm.adapters.bitrix import Bitrix24Adapter
    from apps.amocrm.models import Contact

    try:
        adapter = Bitrix24Adapter()
        page = 1
        total_synced = 0

        while True:
            data = adapter.get_contacts(page=page, limit=50)
            items = data.get("items", [])
            if not items:
                break

            for item in items:
                bitrix_id = item["id"]
                internal_id = 1000000 + bitrix_id

                created_at = _parse_bitrix_date(item.get("created_at"))
                updated_at = _parse_bitrix_date(item.get("updated_at"))

                Contact.objects.update_or_create(
                    amocrm_id=internal_id,
                    defaults={
                        "source": "bitrix",
                        "name": item.get("name", ""),
                        "first_name": item.get("first_name", ""),
                        "last_name": item.get("last_name", ""),
                        "phone": item.get("phone", ""),
                        "email": item.get("email", ""),
                        "company": item.get("company", ""),
                        "responsible_user_id": item.get("responsible_user_id", 0),
                        "created_at": created_at,
                        "updated_at": updated_at,
                        "raw_data": item.get("raw", item),
                    }
                )
                total_synced += 1

            if not data.get("has_more"):
                break
            page += 1

        logger.info(f"Bitrix24: {total_synced} kontakt sinxronlandi")
        return {"synced": total_synced}

    except Exception as exc:
        logger.error(f"Bitrix24 kontakt sinxronlashda xatolik: {exc}")
        self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def sync_bitrix_leads(self):
    """Bitrix24 dan Leadlarni (dastlabki murojaatlar) sinxronlash.

    Bu Bitrix24 ga xos entity — AmoCRM da bunday alohida entity yo'q.
    Lead konvertatsiya qilinganda Deal + Contact ga aylanadi.
    """
    from apps.crm.adapters.bitrix import Bitrix24Adapter
    from apps.amocrm.models import Lead

    try:
        adapter = Bitrix24Adapter()
        page = 1
        total_synced = 0

        while True:
            data = adapter.get_bitrix_leads(page=page, limit=50)
            items = data.get("items", [])
            if not items:
                break

            for item in items:
                bitrix_id = item["id"]
                # Bitrix Lead uchun 2000000 prefix
                internal_id = 2000000 + bitrix_id

                created_at = _parse_bitrix_date(item.get("created_at"))
                updated_at = _parse_bitrix_date(item.get("updated_at"))

                Lead.objects.update_or_create(
                    amocrm_id=internal_id,
                    defaults={
                        "source": "bitrix",
                        "name": item.get("name", ""),
                        "price": item.get("price", 0),
                        "status_id": hash(item.get("status_id", "")) % 100000,
                        "responsible_user_id": item.get("responsible_user_id", 0),
                        "created_at": created_at,
                        "updated_at": updated_at,
                        "raw_data": item.get("raw", item),
                    }
                )
                total_synced += 1

            if not data.get("has_more"):
                break
            page += 1

        logger.info(f"Bitrix24: {total_synced} lead sinxronlandi")
        return {"synced": total_synced}

    except Exception as exc:
        logger.error(f"Bitrix24 lead sinxronlashda xatolik: {exc}")
        self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def sync_bitrix_pipelines(self):
    """Bitrix24 dan pipeline va statuslarni sinxronlash."""
    from apps.crm.adapters.bitrix import Bitrix24Adapter
    from apps.amocrm.models import Pipeline, PipelineStatus

    try:
        adapter = Bitrix24Adapter()
        pipelines = adapter.get_pipelines()
        total = 0

        for p in pipelines:
            # Bitrix pipeline ID uchun 1000000 prefix
            internal_pipeline_id = 1000000 + int(p["id"])

            pipeline, _ = Pipeline.objects.update_or_create(
                amocrm_id=internal_pipeline_id,
                defaults={
                    "name": f"[Bitrix] {p['name']}",
                    "sort": p.get("sort", 0),
                    "is_main": p.get("is_main", False),
                    "raw_data": p.get("raw", {}),
                }
            )

            for s in p.get("statuses", []):
                status_id = hash(str(s["id"])) % 100000
                PipelineStatus.objects.update_or_create(
                    amocrm_id=status_id,
                    pipeline=pipeline,
                    defaults={
                        "name": s.get("name", ""),
                        "sort": s.get("sort", 0),
                        "color": s.get("color", ""),
                        "raw_data": s,
                    }
                )

            total += 1

        logger.info(f"Bitrix24: {total} pipeline sinxronlandi")

    except Exception as exc:
        logger.error(f"Bitrix24 pipeline sinxronlashda xatolik: {exc}")
        self.retry(exc=exc, countdown=60)


@shared_task
def sync_bitrix_all():
    """Bitrix24 dan barcha ma'lumotlarni sinxronlash."""
    from django.conf import settings

    if not getattr(settings, 'BITRIX_WEBHOOK_URL', ''):
        logger.warning("BITRIX_WEBHOOK_URL sozlanmagan — sync o'tkazilmaydi")
        return

    sync_bitrix_pipelines.delay()
    sync_bitrix_deals.delay()
    sync_bitrix_contacts.delay()
    sync_bitrix_leads.delay()
