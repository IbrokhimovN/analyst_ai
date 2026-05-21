from django.urls import path
from .webhooks import amocrm_webhook, amocrm_webhook_verify
from .views import amocrm_auth, amocrm_callback, amocrm_sync_now

app_name = 'amocrm'

urlpatterns = [
    path('auth/', amocrm_auth, name='auth'),
    path('callback/', amocrm_callback, name='callback'),
    path('sync/', amocrm_sync_now, name='sync'),
    path('webhook/', amocrm_webhook, name='webhook'),
    path('webhook/verify/', amocrm_webhook_verify, name='webhook-verify'),
]
