import json
import logging

from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

@csrf_exempt
@require_POST
def amocrm_webhook(request):
    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST.dict()
        logger.info(f"AmoCRM webhook qabul qilindi: {data}")

        if 'leads' in data:
            from .tasks import sync_leads
            sync_leads.delay()

        if 'contacts' in data:
            from .tasks import sync_contacts
            sync_contacts.delay()

        return JsonResponse({"status": "ok"})

    except Exception as e:
        logger.error(f"Webhook xatolik: {e}")
        return JsonResponse({"error": str(e)}, status=500)

def amocrm_webhook_verify(request):
    return HttpResponse("OK", status=200)
