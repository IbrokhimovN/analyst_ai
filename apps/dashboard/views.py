from django.views.generic import TemplateView
from django.utils import timezone

from apps.analytics.services import AnalyticsService
from apps.amocrm.models import Lead, Contact


class DashboardView(TemplateView):
    """Bosh sahifa — SAVDO BO'LIMI INTERAKTIV DASHBOARD."""
    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # CRM source filter (query param: ?source=amocrm yoki ?source=bitrix)
        source = self.request.GET.get('source', None)
        if source and source not in ('amocrm', 'bitrix'):
            source = None

        try:
            service = AnalyticsService()
            summary = service.get_summary(source=source)
            managers = service.get_by_manager(source=source)
            funnel = service.get_funnel(source=source)
            leads_trend = service.get_leads_trend(days=7, source=source)

            # Kunlik umumiy ko'rsatkichlar
            ctx["stats"] = summary

            # Savdo voronkasi (funnel)
            ctx["funnel_data"] = funnel

            # Menejerlar reytingi
            ctx["managers"] = managers

            # Top managers (for follow-up tracking)
            ctx["top_managers"] = managers[:6]

            # Haftalik trend
            ctx["leads_trend"] = leads_trend

            # Sana
            ctx["current_date"] = timezone.now()
            ctx["manager_count"] = len(managers)

            # CRM source statistikasi
            ctx["amocrm_count"] = Lead.objects.filter(source='amocrm').count()
            ctx["bitrix_count"] = Lead.objects.filter(source='bitrix').count()

        except Exception:
            ctx["stats"] = {}
            ctx["funnel_data"] = []
            ctx["managers"] = []
            ctx["top_managers"] = []
            ctx["leads_trend"] = []
            ctx["current_date"] = timezone.now()
            ctx["manager_count"] = 0
            ctx["amocrm_count"] = 0
            ctx["bitrix_count"] = 0

        ctx["current_source"] = source or 'all'
        return ctx


class LeadsView(TemplateView):
    """Leadlar ro'yxati sahifasi."""
    template_name = "dashboard/leads.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        source = self.request.GET.get('source', None)
        ctx["current_source"] = source or 'all'
        return ctx


class ContactsView(TemplateView):
    """Kontaktlar ro'yxati sahifasi."""
    template_name = "dashboard/contacts.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        source = self.request.GET.get('source', None)
        ctx["current_source"] = source or 'all'
        return ctx


class AnalyticsView(TemplateView):
    """Tahlil va grafiklar sahifasi."""
    template_name = "dashboard/analytics.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        source = self.request.GET.get('source', None)
        ctx["current_source"] = source or 'all'
        return ctx


class AIChatView(TemplateView):
    """AI bilan chat sahifasi."""
    template_name = "dashboard/ai_chat.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        source = self.request.GET.get('source', None)
        ctx["current_source"] = source or 'all'
        return ctx
