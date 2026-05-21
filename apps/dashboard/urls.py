from django.urls import path
from .views import DashboardView, LeadsView, ContactsView, AnalyticsView, AIChatView

app_name = 'dashboard'

urlpatterns = [
    path('', DashboardView.as_view(), name='index'),
    path('leads/', LeadsView.as_view(), name='leads'),
    path('contacts/', ContactsView.as_view(), name='contacts'),
    path('analytics/', AnalyticsView.as_view(), name='analytics'),
    path('ai-chat/', AIChatView.as_view(), name='ai-chat'),
]
