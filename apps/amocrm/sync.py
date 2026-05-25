import logging
from datetime import datetime, timezone as tz

from .services import AmoCRMService
from .models import Lead, Contact, Pipeline, PipelineStatus, User

logger = logging.getLogger(__name__)

def _ts(value):
    if not value:
        return None
    return datetime.fromtimestamp(value, tz=tz.utc)

def sync_pipelines(service=None):
    service = service or AmoCRMService()
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
            },
        )
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
                },
            )

    logger.info("%s pipeline sinxronlandi", len(pipelines))
    return len(pipelines)

def sync_users(service=None):
    service = service or AmoCRMService()
    data = service.get_users()
    users = data.get("_embedded", {}).get("users", [])

    for u_data in users:
        rights = u_data.get("rights")
        role = rights.get("role", "") if isinstance(rights, dict) else ""
        User.objects.update_or_create(
            amocrm_id=u_data["id"],
            defaults={
                "name": u_data.get("name", ""),
                "email": u_data.get("email", ""),
                "role": role,
                "raw_data": u_data,
            },
        )

    logger.info("%s foydalanuvchi sinxronlandi", len(users))
    return len(users)

def sync_leads(service=None):
    service = service or AmoCRMService()
    page = 1
    total = 0

    while True:
        data = service.get_leads(page=page)
        items = data.get("_embedded", {}).get("leads", [])
        if not items:
            break

        for item in items:
            pipeline_ref = None
            status_ref = None
            if item.get("pipeline_id"):
                pipeline_ref = Pipeline.objects.filter(
                    amocrm_id=item["pipeline_id"]
                ).first()
            if item.get("status_id") and pipeline_ref:
                status_ref = PipelineStatus.objects.filter(
                    amocrm_id=item["status_id"], pipeline=pipeline_ref
                ).first()

            loss_reason = ""
            reasons = item.get("_embedded", {}).get("loss_reason")
            if reasons:
                loss_reason = reasons[0].get("name", "")

            if not loss_reason:
                for field in item.get("custom_fields_values", []) or []:
                    field_name = field.get("field_name", "")
                    if field_name in ["Etiroz sababi", "Yutqazish sababi", "Rad etish sababi"] or "sabab" in field_name.lower() or "etiroz" in field_name.lower():
                        values = field.get("values", [])
                        if values:
                            loss_reason = values[0].get("value", "")
                            break

            Lead.objects.update_or_create(
                amocrm_id=item["id"],
                defaults={
                    "name": item.get("name", ""),
                    "price": item.get("price", 0),
                    "status_id": item.get("status_id"),
                    "pipeline_id": item.get("pipeline_id"),
                    "responsible_user_id": item.get("responsible_user_id"),
                    "pipeline_ref": pipeline_ref,
                    "status_ref": status_ref,
                    "loss_reason": loss_reason,
                    "created_at": _ts(item.get("created_at")),
                    "updated_at": _ts(item.get("updated_at")),
                    "closed_at": _ts(item.get("closed_at")),
                    "raw_data": item,
                },
            )
            total += 1
        page += 1

    logger.info("%s lead sinxronlandi", total)
    return total

def sync_contacts(service=None):
    service = service or AmoCRMService()
    page = 1
    total = 0

    while True:
        data = service.get_contacts(page=page)
        items = data.get("_embedded", {}).get("contacts", [])
        if not items:
            break

        for item in items:
            phone = ""
            email = ""
            for field in item.get("custom_fields_values", []) or []:
                if field.get("field_code") == "PHONE":
                    phone = field["values"][0]["value"] if field.get("values") else ""
                elif field.get("field_code") == "EMAIL":
                    email = field["values"][0]["value"] if field.get("values") else ""

            Contact.objects.update_or_create(
                amocrm_id=item["id"],
                defaults={
                    "name": item.get("name", ""),
                    "first_name": item.get("first_name", ""),
                    "last_name": item.get("last_name", ""),
                    "phone": phone,
                    "email": email,
                    "responsible_user_id": item.get("responsible_user_id"),
                    "created_at": _ts(item.get("created_at")),
                    "updated_at": _ts(item.get("updated_at")),
                    "raw_data": item,
                },
            )
            total += 1
        page += 1

    logger.info("%s kontakt sinxronlandi", total)
    return total

def sync_all_now():
    service = AmoCRMService()
    result = {"pipelines": 0, "users": 0, "leads": 0, "contacts": 0}

    for key, fn in (
        ("pipelines", sync_pipelines),
        ("users", sync_users),
        ("leads", sync_leads),
        ("contacts", sync_contacts),
    ):
        try:
            result[key] = fn(service)
        except Exception as exc:
            logger.error("%s sinxronlashda xatolik: %s", key, exc)

    logger.info("Sinxronlash tugadi: %s", result)
    return result
