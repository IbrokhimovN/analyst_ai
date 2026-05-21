from django.urls import re_path
from .consumers import AIChatConsumer

websocket_urlpatterns = [
    re_path(r'ws/ai/$', AIChatConsumer.as_asgi()),
]
