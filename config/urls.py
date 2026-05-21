"""
URL configuration for AmoCRM AI Dashboard.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    # Template pages
    path('', include('apps.dashboard.urls')),
    # REST API
    path('api/v1/', include('apps.api.v1.urls')),
    # AmoCRM OAuth callback
    path('amocrm/', include('apps.amocrm.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
