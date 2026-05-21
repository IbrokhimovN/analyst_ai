from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from .views import leads, analytics, ai

urlpatterns = [
    # Leads
    path('leads/', leads.LeadListView.as_view(), name='lead-list'),
    path('leads/<int:pk>/', leads.LeadDetailView.as_view(), name='lead-detail'),
    # Contacts
    path('contacts/', leads.ContactListView.as_view(), name='contact-list'),
    path('contacts/<int:pk>/', leads.ContactDetailView.as_view(), name='contact-detail'),
    # Analytics
    path('analytics/summary/', analytics.SummaryView.as_view(), name='analytics-summary'),
    path('analytics/funnel/', analytics.FunnelView.as_view(), name='analytics-funnel'),
    path('analytics/by-manager/', analytics.ByManagerView.as_view(), name='analytics-by-manager'),
    path('analytics/leads-trend/', analytics.LeadsTrendView.as_view(), name='analytics-leads-trend'),
    path('analytics/revenue-trend/', analytics.RevenueTrendView.as_view(), name='analytics-revenue-trend'),
    # AI
    path('ai/chat/', ai.AIChatView.as_view(), name='ai-chat'),
    path('ai/report/weekly/', ai.WeeklyReportView.as_view(), name='ai-weekly-report'),
    # Auth
    path('auth/token/', TokenObtainPairView.as_view(), name='token-obtain'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    # Docs
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='docs'),
]
