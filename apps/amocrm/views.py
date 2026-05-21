import logging

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt

from .services import AmoCRMService

logger = logging.getLogger(__name__)


def amocrm_auth(request):
    """AmoCRM OAuth jarayonini boshlash — foydalanuvchini AmoCRM ga yo'naltirish."""
    auth_url = (
        f"https://{settings.AMOCRM_DOMAIN}/oauth?"
        f"client_id={settings.AMOCRM_CLIENT_ID}"
        f"&redirect_uri={settings.AMOCRM_REDIRECT_URI}"
        f"&response_type=code"
        f"&state=amocrm_auth"
    )
    return HttpResponseRedirect(auth_url)


def amocrm_callback(request):
    """AmoCRM OAuth callback — code ni token ga almashtirish."""
    code = request.GET.get('code')
    if not code:
        messages.error(request, "AmoCRM dan authorization code kelmadi!")
        return redirect('dashboard:index')

    try:
        service = AmoCRMService()
        token_data = service.exchange_code(code)

        from .models import AmoCRMToken
        AmoCRMToken.objects.all().delete()  # Eski tokenlarni o'chirish
        AmoCRMToken.objects.create(
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
        )

        logger.info("AmoCRM token muvaffaqiyatli saqlandi")
        messages.success(request, "AmoCRM muvaffaqiyatli ulandi! Ma'lumotlar sinxronlanmoqda...")

        # Dastlabki sinxronlash — sinxron ravishda (bir martalik)
        result = _sync_all_now()
        messages.success(
            request,
            f"Sinxronlash tugadi: {result['pipelines']} pipeline, "
            f"{result['leads']} lead, {result['contacts']} kontakt, "
            f"{result['users']} foydalanuvchi"
        )

    except Exception as e:
        logger.error(f"AmoCRM callback xatolik: {e}")
        messages.error(request, f"AmoCRM ulanishda xatolik: {e}")

    return redirect('dashboard:index')


@csrf_exempt
def amocrm_sync_now(request):
    """Bir martalik sinxronlash — AmoCRM dan barcha ma'lumotlarni tortib olish."""
    try:
        from .models import AmoCRMToken
        if not AmoCRMToken.objects.exists():
            return JsonResponse(
                {"error": "AmoCRM token topilmadi! Avval /amocrm/auth/ orqali ulaning."},
                status=400
            )

        result = _sync_all_now()
        return JsonResponse({
            "status": "success",
            "message": "Ma'lumotlar muvaffaqiyatli sinxronlandi",
            **result,
        })

    except Exception as e:
        logger.error(f"Sinxronlash xatolik: {e}")
        return JsonResponse({"error": str(e)}, status=500)


def _sync_all_now():
    """Barcha ma'lumotlarni sinxron ravishda tortib olish (Celery'siz)."""
    from datetime import datetime, timezone as tz
    from .services import AmoCRMService
    from .models import Lead, Contact, Pipeline, PipelineStatus, User

    service = AmoCRMService()
    result = {"pipelines": 0, "leads": 0, "contacts": 0, "users": 0}

    # 1. Pipelines va statuslar
    logger.info("Pipeline sinxronlash boshlandi...")
    try:
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
        result["pipelines"] = len(pipelines)
        logger.info(f"{len(pipelines)} pipeline sinxronlandi")
    except Exception as e:
        logger.error(f"Pipeline sinxronlashda xatolik: {e}")

    # 2. Users
    logger.info("Foydalanuvchilar sinxronlash boshlandi...")
    try:
        data = service.get_users()
        users = data.get("_embedded", {}).get("users", [])
        for u_data in users:
            User.objects.update_or_create(
                amocrm_id=u_data["id"],
                defaults={
                    "name": u_data.get("name", ""),
                    "email": u_data.get("email", ""),
                    "role": u_data.get("rights", {}).get("role", "") if isinstance(u_data.get("rights"), dict) else "",
                    "raw_data": u_data,
                }
            )
        result["users"] = len(users)
        logger.info(f"{len(users)} foydalanuvchi sinxronlandi")
    except Exception as e:
        logger.error(f"Foydalanuvchilar sinxronlashda xatolik: {e}")

    # 3. Leads (barcha sahifalar)
    logger.info("Leadlar sinxronlash boshlandi...")
    try:
        page = 1
        total_leads = 0
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
                    created_at = datetime.fromtimestamp(item["created_at"], tz=tz.utc)
                if item.get("updated_at"):
                    updated_at = datetime.fromtimestamp(item["updated_at"], tz=tz.utc)
                if item.get("closed_at"):
                    closed_at = datetime.fromtimestamp(item["closed_at"], tz=tz.utc)

                # Pipeline va Status FK ni topish
                pipeline_ref = None
                status_ref = None
                if item.get("pipeline_id"):
                    pipeline_ref = Pipeline.objects.filter(amocrm_id=item["pipeline_id"]).first()
                if item.get("status_id") and pipeline_ref:
                    status_ref = PipelineStatus.objects.filter(
                        amocrm_id=item["status_id"], pipeline=pipeline_ref
                    ).first()

                # Loss reason
                loss_reason = ""
                if item.get("_embedded", {}).get("loss_reason"):
                    reasons = item["_embedded"]["loss_reason"]
                    if reasons:
                        loss_reason = reasons[0].get("name", "")

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
                        "created_at": created_at,
                        "updated_at": updated_at,
                        "closed_at": closed_at,
                        "raw_data": item,
                    }
                )
                total_leads += 1
            page += 1

        result["leads"] = total_leads
        logger.info(f"{total_leads} lead sinxronlandi")
    except Exception as e:
        logger.error(f"Lead sinxronlashda xatolik: {e}")

    # 4. Contacts (barcha sahifalar)
    logger.info("Kontaktlar sinxronlash boshlandi...")
    try:
        page = 1
        total_contacts = 0
        while True:
            data = service.get_contacts(page=page)
            items = data.get("_embedded", {}).get("contacts", [])
            if not items:
                break

            for item in items:
                phone = ''
                email = ''
                for field in item.get("custom_fields_values", []) or []:
                    if field.get("field_code") == "PHONE":
                        phone = field["values"][0]["value"] if field.get("values") else ''
                    elif field.get("field_code") == "EMAIL":
                        email = field["values"][0]["value"] if field.get("values") else ''

                created_at = None
                updated_at = None
                if item.get("created_at"):
                    created_at = datetime.fromtimestamp(item["created_at"], tz=tz.utc)
                if item.get("updated_at"):
                    updated_at = datetime.fromtimestamp(item["updated_at"], tz=tz.utc)

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
                total_contacts += 1
            page += 1

        result["contacts"] = total_contacts
        logger.info(f"{total_contacts} kontakt sinxronlandi")
    except Exception as e:
        logger.error(f"Kontakt sinxronlashda xatolik: {e}")

    logger.info(f"Sinxronlash tugadi: {result}")
    return result
