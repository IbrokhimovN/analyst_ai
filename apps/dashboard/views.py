from django.views.generic import TemplateView
from django.utils import timezone

from apps.analytics.services import AnalyticsService
from apps.amocrm.models import Lead, Contact


class DashboardView(TemplateView):
    """Bosh sahifa — SAVDO BO'LIMI INTERAKTIV DASHBOARD."""
    template_name = "dashboard/index.html"

    # Davr (period) tanlovi — kunlik / haftalik / oylik / barchasi
    PERIOD_LABELS = {
        'day': 'Kunlik', 'week': 'Haftalik', 'month': 'Oylik', 'all': 'Barcha vaqt',
    }

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # CRM source filter (query param: ?source=amocrm yoki ?source=bitrix)
        source = self.request.GET.get('source', None)
        if source and source not in ('amocrm', 'bitrix'):
            source = None

        # Davr filtri (query param: ?period=day|week|month) — yo'q bo'lsa barchasi
        period = self.request.GET.get('period', None)
        if period not in ('day', 'week', 'month'):
            period = None

        try:
            service = AnalyticsService()

            # Kunlik umumiy ko'rsatkichlar
            ctx["stats"] = service.get_summary(source=source, period=period)

            # 4-bosqichli sotuv voronkasi (Lid → Call → Conversation → Sotuv)
            ctx["funnel"] = service.get_sales_funnel(source=source, period=period)

            # Asosiy konversiyalar (rings)
            ctx["conversions"] = service.get_conversions(source=source, period=period)

            # Menejerlar reytingi
            managers = service.get_by_manager(source=source, period=period)
            ctx["managers"] = managers
            ctx["top_managers"] = managers[:5]

            # Moliyaviy ko'rsatkichlar
            ctx["finance"] = service.get_finance(source=source, period=period)

            # Kunlik dinamika — oylik davrda 30 kun, aks holda 7 kun oynasi
            dyn_days = 30 if period == 'month' else 7
            ctx["daily_dynamics"] = service.get_daily_dynamics(days=dyn_days, source=source)

            # Yutqazish sabablari
            ctx["loss_reasons"] = service.get_loss_reasons(source=source, period=period)

            # Follow-up — qoldirilgan lidlar (yutqazganlar bo'yicha)
            ctx["followup"] = [m for m in managers if m["lost"]][:5] or managers[:5]

            # Insight va eng yaxshi kunlar
            ctx["insights"] = service.get_insights(source=source, period=period)
            ctx["best_days"] = service.get_best_days(source=source, period=period)

            # Sana
            ctx["current_date"] = timezone.now()
            ctx["manager_count"] = len(managers)

            # CRM source statistikasi
            ctx["amocrm_count"] = Lead.objects.filter(source='amocrm').count()
            ctx["bitrix_count"] = Lead.objects.filter(source='bitrix').count()

        except Exception:
            ctx["stats"] = {}
            ctx["funnel"] = []
            ctx["conversions"] = []
            ctx["managers"] = []
            ctx["top_managers"] = []
            ctx["finance"] = {}
            ctx["daily_dynamics"] = []
            ctx["loss_reasons"] = []
            ctx["followup"] = []
            ctx["insights"] = []
            ctx["best_days"] = []
            ctx["current_date"] = timezone.now()
            ctx["manager_count"] = 0
            ctx["amocrm_count"] = 0
            ctx["bitrix_count"] = 0

        ctx["current_source"] = source or 'all'
        ctx["current_period"] = period or 'all'
        ctx["current_period_label"] = self.PERIOD_LABELS.get(period or 'all', 'Barcha vaqt')
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
