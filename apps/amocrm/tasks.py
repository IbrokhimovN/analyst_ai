import logging
from datetime import datetime, timezone

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def sync_leads(self):
    """AmoCRM dan barcha leadlarni sinxronlash."""
    from .services import AmoCRMService
    from .models import Lead

    try:
        service = AmoCRMService()
        page = 1
        total_synced = 0

        while True:
            data = service.get_leads(page=page)
            items = data.get("_embedded", {}).get("leads", [])
            if not items:
                break

            for item in items:
                created_at = None
                updated_at = None
                closed_at = None

                if item.get("created_at"):
                    created_at = datetime.fromtimestamp(item["created_at"], tz=timezone.utc)
                if item.get("updated_at"):
                    updated_at = datetime.fromtimestamp(item["updated_at"], tz=timezone.utc)
                if item.get("closed_at"):
                    closed_at = datetime.fromtimestamp(item["closed_at"], tz=timezone.utc)

                Lead.objects.update_or_create(
                    amocrm_id=item["id"],
                    defaults={
                        "name": item.get("name", ""),
                        "price": item.get("price", 0),
                        "status_id": item.get("status_id"),
                        "pipeline_id": item.get("pipeline_id"),
                        "responsible_user_id": item.get("responsible_user_id"),
                        "created_at": created_at,
                        "updated_at": updated_at,
                        "closed_at": closed_at,
                        "raw_data": item,
                    }
                )
                total_synced += 1

            page += 1

        logger.info(f"Jami {total_synced} lead sinxronlandi")
        return {"synced": total_synced}

    except Exception as exc:
        logger.error(f"Lead sinxronlashda xatolik: {exc}")
        self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def sync_contacts(self):
    """AmoCRM dan kontaktlarni sinxronlash."""
    from .services import AmoCRMService
    from .models import Contact

    try:
        service = AmoCRMService()
        page = 1
        total_synced = 0

        while True:
            data = service.get_contacts(page=page)
            items = data.get("_embedded", {}).get("contacts", [])
            if not items:
                break

            for item in items:
                # Telefon va email ajratib olish
                phone = ''
                email = ''
                for field in item.get("custom_fields_values", []):
                    if field.get("field_code") == "PHONE":
                        phone = field["values"][0]["value"] if field.get("values") else ''
                    elif field.get("field_code") == "EMAIL":
                        email = field["values"][0]["value"] if field.get("values") else ''

                created_at = None
                updated_at = None
                if item.get("created_at"):
                    created_at = datetime.fromtimestamp(item["created_at"], tz=timezone.utc)
                if item.get("updated_at"):
                    updated_at = datetime.fromtimestamp(item["updated_at"], tz=timezone.utc)

                Contact.objects.update_or_create(
                    amocrm_id=item["id"],
                    defaults={
                        "name": item.get("name", ""),
                        "first_name": item.get("first_name", ""),
                        "last_name": item.get("last_name", ""),
                        "phone": phone,
                        "email": email,
                        "responsible_user_id": item.get("responsible_user_id"),
                        "created_at": created_at,
                        "updated_at": updated_at,
                        "raw_data": item,
                    }
                )
                total_synced += 1

            page += 1

        logger.info(f"Jami {total_synced} kontakt sinxronlandi")
        return {"synced": total_synced}

    except Exception as exc:
        logger.error(f"Kontakt sinxronlashda xatolik: {exc}")
        self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def sync_pipelines(self):
    """Pipeline va statuslarni sinxronlash."""
    from .services import AmoCRMService
    from .models import Pipeline, PipelineStatus

    try:
        service = AmoCRMService()
        data = service.get_pipelines()
        pipelines = data.get("_embedded", {}).get("pipelines", [])

        for p_data in pipelines:
            pipeline, _ = Pipeline.objects.update_or_create(
                amocrm_id=p_data["id"],
                defaults={
                    "name": p_data.get("name", ""),
                    "sort": p_data.get("sort", 0),
                    "is_main": p_data.get("is_main", False),
                    "raw_data": p_data,
                }
            )

            # Statuslarni sinxronlash
            for s_data in p_data.get("_embedded", {}).get("statuses", []):
                PipelineStatus.objects.update_or_create(
                    amocrm_id=s_data["id"],
                    pipeline=pipeline,
                    defaults={
                        "name": s_data.get("name", ""),
                        "sort": s_data.get("sort", 0),
                        "color": s_data.get("color", ""),
                        "is_editable": s_data.get("is_editable", True),
                        "raw_data": s_data,
                    }
                )

        logger.info(f"{len(pipelines)} pipeline sinxronlandi")

    except Exception as exc:
        logger.error(f"Pipeline sinxronlashda xatolik: {exc}")
        self.retry(exc=exc, countdown=60)


@shared_task
def sync_all():
    """Barcha ma'lumotlarni sinxronlash (Celery Beat orqali chaqiriladi)."""
    sync_pipelines.delay()
    sync_leads.delay()
    sync_contacts.delay()
