import re
from datetime import date

from django.views.generic import TemplateView
from django.utils import timezone

from apps.analytics.services import AnalyticsService
from apps.amocrm.models import Lead, Contact

PERIOD_LABELS = {
    'day': 'Kunlik', 'week': 'Haftalik', 'month': 'Oylik', 'all': 'Barcha vaqt',
}

RANGE_RE = re.compile(r'^range:\d{4}-\d{2}-\d{2}:\d{4}-\d{2}-\d{2}$')

def clean_period(value):
    if value in ('day', 'week', 'month'):
        return value
    if value and RANGE_RE.match(value):
        return value
    return None

def clean_source(value):
    return value if value in ('amocrm', 'bitrix') else None

def build_dashboard_context(source=None, period=None):
    ctx = {}
    try:
        service = AnalyticsService()

        ctx["stats"] = service.get_summary(source=source, period=period)
        ctx["funnel"] = service.get_sales_funnel(source=source, period=period)
        ctx["conversions"] = service.get_conversions(source=source, period=period)

        managers = service.get_by_manager(source=source, period=period)
        ctx["managers"] = managers
        # barcha menejerlar yuboriladi; frontend 5 tadan paginatsiya qiladi
        ctx["top_managers"] = managers

        ctx["finance"] = service.get_finance(source=source, period=period)

        if period and period.startswith('range:'):
            _, d1, d2 = period.split(':')
            ctx["daily_dynamics"] = service.get_daily_dynamics(
                source=source,
                date_from=date.fromisoformat(d1),
                date_to=date.fromisoformat(d2),
            )
        else:
            dyn_days = 30 if period == 'month' else 7
            ctx["daily_dynamics"] = service.get_daily_dynamics(
                days=dyn_days, source=source)

        ctx["loss_reasons"] = service.get_loss_reasons(source=source, period=period)
        ctx["followup"] = [m for m in managers if m["lost"]][:5] or managers[:5]
        ctx["insights"] = service.get_insights(source=source, period=period)
        ctx["best_days"] = service.get_best_days(source=source, period=period)

        ctx["current_date"] = timezone.now()
        ctx["manager_count"] = len(managers)
        ctx["amocrm_count"] = Lead.objects.filter(source='amocrm').count()
        ctx["bitrix_count"] = Lead.objects.filter(source='bitrix').count()

    except Exception:
        ctx.update({
            "stats": {}, "funnel": [], "conversions": [], "managers": [],
            "top_managers": [], "finance": {}, "daily_dynamics": [],
            "loss_reasons": [], "followup": [], "insights": [], "best_days": [],
            "current_date": timezone.now(), "manager_count": 0,
            "amocrm_count": 0, "bitrix_count": 0,
        })

    ctx["current_source"] = source or 'all'
    ctx["current_period"] = period or 'all'
    if period and period.startswith('range:'):
        _, d1, d2 = period.split(':')
        ctx["current_period_label"] = f'{d1} – {d2}'
    else:
        ctx["current_period_label"] = PERIOD_LABELS.get(period or 'all',
                                                        'Barcha vaqt')
    return ctx

class DashboardView(TemplateView):
    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        source = clean_source(self.request.GET.get('source'))
        period = clean_period(self.request.GET.get('period'))
        ctx.update(build_dashboard_context(source, period))
        return ctx

class LeadsView(TemplateView):
    template_name = "dashboard/leads.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        source = self.request.GET.get('source', None)
        ctx["current_source"] = source or 'all'
        return ctx

class ContactsView(TemplateView):
    template_name = "dashboard/contacts.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        source = self.request.GET.get('source', None)
        ctx["current_source"] = source or 'all'
        return ctx

class AnalyticsView(TemplateView):
    template_name = "dashboard/analytics.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        source = self.request.GET.get('source', None)
        ctx["current_source"] = source or 'all'
        return ctx

class AIChatView(TemplateView):
    template_name = "dashboard/ai_chat.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        source = self.request.GET.get('source', None)
        ctx["current_source"] = source or 'all'
        return ctx
