from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from .views import leads, analytics, ai, dashboard_data

urlpatterns = [
    path('leads/', leads.LeadListView.as_view(), name='lead-list'),
    path('leads/<int:pk>/', leads.LeadDetailView.as_view(), name='lead-detail'),
    path('contacts/', leads.ContactListView.as_view(), name='contact-list'),
    path('contacts/<int:pk>/', leads.ContactDetailView.as_view(), name='contact-detail'),
    path('analytics/summary/', analytics.SummaryView.as_view(), name='analytics-summary'),
    path('analytics/funnel/', analytics.FunnelView.as_view(), name='analytics-funnel'),
    path('analytics/by-manager/', analytics.ByManagerView.as_view(), name='analytics-by-manager'),
    path('analytics/leads-trend/', analytics.LeadsTrendView.as_view(), name='analytics-leads-trend'),
    path('analytics/revenue-trend/', analytics.RevenueTrendView.as_view(), name='analytics-revenue-trend'),
    path('dashboard/data/', dashboard_data.DashboardDataView.as_view(), name='dashboard-data'),
    path('ai/chat/', ai.AIChatView.as_view(), name='ai-chat'),
    path('ai/chat/history/', ai.ChatHistoryView.as_view(), name='ai-chat-history'),
    path('ai/rag/upload/', ai.RAGUploadView.as_view(), name='ai-rag-upload'),
    path('ai/rag/documents/', ai.RAGDocumentsView.as_view(), name='ai-rag-documents'),
    path('ai/rag/documents/<int:pk>/', ai.RAGDocumentDetailView.as_view(), name='ai-rag-document'),
    path('ai/agent/analyze/', ai.AgentAnalyzeView.as_view(), name='ai-agent-analyze'),
    path('ai/card/analyze/', ai.CardAnalyzeView.as_view(), name='ai-card-analyze'),
    path('ai/card/render/', ai.CardRenderView.as_view(), name='ai-card-render'),
    path('ai/managers/', ai.ManagersListView.as_view(), name='ai-managers'),
    path('ai/report/weekly/', ai.WeeklyReportView.as_view(), name='ai-weekly-report'),
    path('ai/tts/', ai.TTSView.as_view(), name='ai-tts'),
    path('auth/token/', TokenObtainPairView.as_view(), name='token-obtain'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='docs'),
]
