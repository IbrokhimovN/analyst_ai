import logging

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt

from .services import AmoCRMService
from .sync import sync_all_now

logger = logging.getLogger(__name__)

def amocrm_auth(request):
    auth_url = (
        f"https://{settings.AMOCRM_DOMAIN}/oauth?"
        f"client_id={settings.AMOCRM_CLIENT_ID}"
        f"&redirect_uri={settings.AMOCRM_REDIRECT_URI}"
        f"&response_type=code"
        f"&state=amocrm_auth"
    )
    return HttpResponseRedirect(auth_url)

def amocrm_callback(request):
    code = request.GET.get('code')
    if not code:
        messages.error(request, "AmoCRM dan authorization code kelmadi!")
        return redirect('dashboard:index')

    try:
        service = AmoCRMService()
        token_data = service.exchange_code(code)

        from .models import AmoCRMToken
        AmoCRMToken.objects.all().delete()
        AmoCRMToken.objects.create(
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
        )

        logger.info("AmoCRM token muvaffaqiyatli saqlandi")
        messages.success(request, "AmoCRM muvaffaqiyatli ulandi! Ma'lumotlar sinxronlanmoqda...")

        result = sync_all_now()
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
    try:
        from .models import AmoCRMToken
        if not AmoCRMToken.objects.exists():
            return JsonResponse(
                {"error": "AmoCRM token topilmadi! Avval /amocrm/auth/ orqali ulaning."},
                status=400
            )

        result = sync_all_now()
        return JsonResponse({
            "status": "success",
            "message": "Ma'lumotlar muvaffaqiyatli sinxronlandi",
            **result,
        })

    except Exception as e:
        logger.error(f"Sinxronlash xatolik: {e}")
        return JsonResponse({"error": str(e)}, status=500)
