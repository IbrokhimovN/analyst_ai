import logging
import re
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum, Count, Avg, Q, F
from django.utils import timezone

from apps.amocrm.models import Lead, Pipeline, PipelineStatus

logger = logging.getLogger(__name__)

WON_STATUS_ID = 142
LOST_STATUS_ID = 143

class AnalyticsService:

    PERIOD_DAYS = {'day': 1, 'week': 7, 'month': 30}

    _RANGE_RE = re.compile(r'^range:(\d{4}-\d{2}-\d{2}):(\d{4}-\d{2}-\d{2})$')

    def _parse_period(self, period):
        if not period:
            return None
        days = self.PERIOD_DAYS.get(period)
        if days:
            return ('days', days)
        match = self._RANGE_RE.match(period) if isinstance(period, str) else None
        if match:
            try:
                d1 = date.fromisoformat(match.group(1))
                d2 = date.fromisoformat(match.group(2))
            except ValueError:
                return None
            if d1 > d2:
                d1, d2 = d2, d1
            return ('range', d1, d2)
        return None

    def _base_queryset(self, source=None, period=None):
        qs = Lead.objects.all()
        if source:
            qs = qs.filter(source=source)
        parsed = self._parse_period(period)
        if parsed and parsed[0] == 'days':
            start = timezone.now() - timedelta(days=parsed[1])
            qs = qs.filter(created_at__gte=start)
        elif parsed and parsed[0] == 'range':
            qs = qs.filter(created_at__date__gte=parsed[1],
                           created_at__date__lte=parsed[2])
        return qs

    def _status_buckets(self):
        statuses = list(
            PipelineStatus.objects
            .exclude(amocrm_id__in=[WON_STATUS_ID, LOST_STATUS_ID])
            .order_by('sort')
            .values_list('amocrm_id', flat=True)
        )
        n = len(statuses)
        if n == 0:
            return [], []
        cut = max(1, n // 3)
        return statuses[:cut], statuses[-cut:]

    def get_summary(self, days=30, source=None, period=None):
        start_date = timezone.now() - timedelta(days=days)
        leads = self._base_queryset(source, period)
        recent_leads = leads.filter(created_at__gte=start_date)

        total_leads = leads.count()
        new_leads = recent_leads.count()

        won_leads = leads.filter(status_id=WON_STATUS_ID)
        lost_leads = leads.filter(status_id=LOST_STATUS_ID)
        won_count = won_leads.count()
        lost_count = lost_leads.count()

        total_revenue = won_leads.aggregate(total=Sum('price'))['total'] or Decimal('0')
        monthly_revenue = won_leads.filter(
            closed_at__gte=start_date
        ).aggregate(total=Sum('price'))['total'] or Decimal('0')

        avg_deal_size = won_leads.aggregate(avg=Avg('price'))['avg'] or Decimal('0')

        lead_value = total_revenue / total_leads if total_leads > 0 else Decimal('0')
        sale_value = avg_deal_size

        conversion_rate = 0
        closed_total = won_count + lost_count
        if closed_total > 0:
            conversion_rate = (won_count / closed_total) * 100

        return {
            'total_leads': total_leads,
            'new_leads': new_leads,
            'won_count': won_count,
            'lost_count': lost_count,
            'total_revenue': float(total_revenue),
            'monthly_revenue': float(monthly_revenue),
            'avg_deal_size': float(avg_deal_size),
            'lead_value': float(lead_value),
            'sale_value': float(sale_value),
            'conversion_rate': round(conversion_rate, 1),
            'period_days': days,
            'source': source or 'all',
        }

    def get_funnel(self, pipeline_id=None, source=None):
        leads = self._base_queryset(source)
        if pipeline_id:
            leads = leads.filter(pipeline_id=pipeline_id)

        pipeline_filter = {}
        if pipeline_id:
            pipeline_filter['pipeline__amocrm_id'] = pipeline_id

        statuses = PipelineStatus.objects.filter(**pipeline_filter).order_by('sort')

        funnel_data = []
        for status in statuses:
            count = leads.filter(status_id=status.amocrm_id).count()
            total_value = leads.filter(
                status_id=status.amocrm_id
            ).aggregate(total=Sum('price'))['total'] or 0

            funnel_data.append({
                'status_id': status.amocrm_id,
                'status_name': status.name,
                'color': status.color,
                'count': count,
                'total_value': float(total_value),
            })

        return funnel_data

    def get_by_manager(self, days=30, source=None, period=None):
        start_date = timezone.now() - timedelta(days=days)

        from apps.amocrm.models import User as AmoCRMUser

        managers = AmoCRMUser.objects.all()
        incoming_ids, negotiating_ids = self._status_buckets()
        result = []

        for manager in managers:
            manager_leads = self._base_queryset(source, period).filter(
                responsible_user_id=manager.amocrm_id
            )
            recent_leads = manager_leads.filter(created_at__gte=start_date)

            total = manager_leads.count()
            if total == 0:
                # deal/lead biriktirilmagan menejerni kartada ko'rsatmaymiz
                continue
            won = manager_leads.filter(status_id=WON_STATUS_ID).count()
            lost = manager_leads.filter(status_id=LOST_STATUS_ID).count()
            revenue = manager_leads.filter(
                status_id=WON_STATUS_ID
            ).aggregate(total=Sum('price'))['total'] or 0

            conversion = 0
            closed = won + lost
            if closed > 0:
                conversion = (won / closed) * 100

            in_incoming = (
                manager_leads.filter(status_id__in=incoming_ids).count()
                if incoming_ids else 0
            )
            calls = total - in_incoming
            conversations = won + (
                manager_leads.filter(status_id__in=negotiating_ids).count()
                if negotiating_ids else 0
            )
            convo_rate = round(conversations / calls * 100, 1) if calls else 0
            sale_rate = round(won / conversations * 100, 1) if conversations else 0
            lead_to_sale = round(won / total * 100, 1) if total else 0

            result.append({
                'manager_id': manager.amocrm_id,
                'manager_name': manager.name,
                'total_leads': total,
                'recent_leads': recent_leads.count(),
                'calls': calls,
                'conversations': conversations,
                'won': won,
                'lost': lost,
                'revenue': float(revenue),
                'conversion_rate': round(conversion, 1),
                'convo_rate': convo_rate,
                'sale_rate': sale_rate,
                'lead_to_sale': lead_to_sale,
            })

        result.sort(key=lambda x: x['revenue'], reverse=True)
        return result

    def get_leads_trend(self, days=30, source=None):
        start_date = timezone.now() - timedelta(days=days)

        from django.db.models.functions import TruncDate

        qs = self._base_queryset(source).filter(created_at__gte=start_date)

        daily = (
            qs
            .annotate(day=TruncDate('created_at'))
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )

        return [
            {'date': item['day'].isoformat(), 'count': item['count']}
            for item in daily
        ]

    def get_revenue_trend(self, days=30, source=None):
        start_date = timezone.now() - timedelta(days=days)

        from django.db.models.functions import TruncDate

        qs = self._base_queryset(source).filter(
            status_id=WON_STATUS_ID, closed_at__gte=start_date
        )

        daily = (
            qs
            .annotate(day=TruncDate('closed_at'))
            .values('day')
            .annotate(
                revenue=Sum('price'),
                count=Count('id'),
            )
            .order_by('day')
        )

        return [
            {
                'date': item['day'].isoformat(),
                'revenue': float(item['revenue']),
                'count': item['count'],
            }
            for item in daily
        ]

    def get_top_managers(self, limit=5, source=None, period=None):
        managers = self.get_by_manager(source=source, period=period)
        return managers[:limit]

    def get_sales_funnel(self, source=None, period=None):
        leads = self._base_queryset(source, period)
        total = leads.count()
        won = leads.filter(status_id=WON_STATUS_ID).count()

        incoming_ids, negotiating_ids = self._status_buckets()
        in_incoming = leads.filter(status_id__in=incoming_ids).count() if incoming_ids else 0
        negotiating = leads.filter(status_id__in=negotiating_ids).count() if negotiating_ids else 0

        calls = total - in_incoming
        conversations = won + negotiating

        stages = [
            {'name': 'Lid',          'count': total,         'color': '#3b82f6'},
            {'name': 'Call',         'count': calls,         'color': '#38bdf8'},
            {'name': 'Conversation', 'count': conversations, 'color': '#22c55e'},
            {'name': 'Sotuv',        'count': won,           'color': '#f59e0b'},
        ]
        for s in stages:
            s['pct'] = round(s['count'] / total * 100, 1) if total else 0
        return stages

    def get_conversions(self, source=None, period=None):
        funnel = {s['name']: s['count'] for s in self.get_sales_funnel(source, period)}
        lid = funnel.get('Lid', 0)
        call = funnel.get('Call', 0)
        conv = funnel.get('Conversation', 0)
        sale = funnel.get('Sotuv', 0)

        def rate(num, den):
            return round(num / den * 100, 1) if den else 0

        return [
            {'label': 'Call → Conversation', 'pct': rate(conv, call),
             'num': conv, 'den': call, 'color': '#3b82f6'},
            {'label': 'Conversation → Sale', 'pct': rate(sale, conv),
             'num': sale, 'den': conv, 'color': '#f59e0b'},
            {'label': 'Lid → Sale (umumiy)', 'pct': rate(sale, lid),
             'num': sale, 'den': lid, 'color': '#22c55e'},
        ]

    def get_loss_reasons(self, source=None, limit=5, period=None):
        all_lost = self._base_queryset(source, period).filter(
            status_id=LOST_STATUS_ID
        )

        with_reason = all_lost.exclude(loss_reason='').exclude(
            loss_reason__isnull=True
        )
        rows = list(
            with_reason.values('loss_reason')
            .annotate(count=Count('id'))
            .order_by('-count')[:limit]
        )
        if rows:
            return [{'reason': r['loss_reason'], 'count': r['count']}
                    for r in rows]

        from apps.amocrm.models import User as AmoCRMUser

        combo_rows = list(
            all_lost.values('pipeline_ref__name', 'responsible_user_id')
            .annotate(count=Count('id'))
            .order_by('-count')[:limit]
        )
        if combo_rows:
            user_ids = [r['responsible_user_id'] for r in combo_rows]
            user_names = dict(
                AmoCRMUser.objects.filter(
                    amocrm_id__in=user_ids
                ).values_list('amocrm_id', 'name')
            )
            return [{
                'reason': '{} — {}'.format(
                    r['pipeline_ref__name'] or 'Noma\'lum',
                    user_names.get(r['responsible_user_id'],
                                   f"#{r['responsible_user_id']}")
                ),
                'count': r['count'],
            } for r in combo_rows]

        manager_rows = list(
            all_lost.values('responsible_user_id')
            .annotate(count=Count('id'))
            .order_by('-count')[:limit]
        )
        if manager_rows:
            user_names = dict(
                AmoCRMUser.objects.filter(
                    amocrm_id__in=[r['responsible_user_id']
                                   for r in manager_rows]
                ).values_list('amocrm_id', 'name')
            )
            return [{
                'reason': user_names.get(r['responsible_user_id'],
                                         f"#{r['responsible_user_id']}"),
                'count': r['count'],
            } for r in manager_rows]

        total_lost = all_lost.count()
        if total_lost:
            return [{'reason': 'Sabab ko\'rsatilmagan', 'count': total_lost}]
        return []

    def get_best_days(self, source=None, limit=3, period=None):
        from django.db.models.functions import ExtractIsoWeekDay

        names = {
            1: 'Dushanba', 2: 'Seshanba', 3: 'Chorshanba', 4: 'Payshanba',
            5: 'Juma', 6: 'Shanba', 7: 'Yakshanba',
        }
        leads = self._base_queryset(source, period).exclude(created_at__isnull=True)
        rows = (
            leads.annotate(wd=ExtractIsoWeekDay('created_at'))
            .values('wd')
            .annotate(
                leads=Count('id'),
                won=Count('id', filter=Q(status_id=WON_STATUS_ID)),
            )
        )
        result = []
        for r in rows:
            leads_n = r['leads']
            won_n = r['won']
            result.append({
                'day': names.get(r['wd'], '—'),
                'leads': leads_n,
                'won': won_n,
                'conversion': round(won_n / leads_n * 100, 1) if leads_n else 0,
            })
        result.sort(key=lambda x: x['leads'], reverse=True)
        return result[:limit]

    def get_finance(self, source=None, period=None):
        summary = self.get_summary(source=source, period=period)
        total_leads = summary['total_leads']
        won = summary['won_count']
        total_revenue = summary['total_revenue']
        return {
            'total_revenue': total_revenue,
            'avg_deal': summary['avg_deal_size'],
            'lead_value': round(total_revenue / total_leads) if total_leads else 0,
            'sale_value': round(total_revenue / won) if won else 0,
        }

    def get_daily_dynamics(self, days=7, source=None, date_from=None, date_to=None):
        from django.db.models.functions import TruncDate

        if date_from and date_to:
            start, end = date_from, date_to
            span = (end - start).days + 1
            if span > 92:
                start = end - timedelta(days=91)
                span = 92
        else:
            end = timezone.now().date()
            start = end - timedelta(days=days - 1)
            span = days

        base = self._base_queryset(source)

        leads_by_day = dict(
            base.filter(created_at__date__gte=start, created_at__date__lte=end)
            .annotate(d=TruncDate('created_at'))
            .values('d')
            .annotate(c=Count('id'))
            .values_list('d', 'c')
        )
        sales_by_day = dict(
            base.filter(status_id=WON_STATUS_ID,
                        closed_at__date__gte=start, closed_at__date__lte=end)
            .annotate(d=TruncDate('closed_at'))
            .values('d')
            .annotate(c=Count('id'))
            .values_list('d', 'c')
        )

        result = []
        for i in range(span):
            day = start + timedelta(days=i)
            leads_n = leads_by_day.get(day, 0)
            sales_n = sales_by_day.get(day, 0)
            result.append({
                'date': day.isoformat(),
                'leads': leads_n,
                'sales': sales_n,
                'conversion': round(sales_n / leads_n * 100, 1) if leads_n else 0,
            })
        return result

    def get_insights(self, source=None, period=None):
        funnel = {s['name']: s for s in self.get_sales_funnel(source, period)}
        conv = self.get_conversions(source, period)
        managers = self.get_by_manager(source=source, period=period)

        insights = []

        strong = max(funnel.values(), key=lambda s: s['pct']) if funnel else None
        if strong:
            insights.append({
                'type': 'good',
                'title': 'Asosiy kuchli zona',
                'text': f"{strong['name']} bosqichi — {strong['pct']}% ushlab qolish",
            })

        if conv:
            weakest = min(conv, key=lambda c: c['pct'])
            insights.append({
                'type': 'warn',
                'title': 'Asosiy muammo',
                'text': f"{weakest['label']} — atigi {weakest['pct']}%, e'tibor talab",
            })

        if managers:
            avg_conv = round(
                sum(m['conversion_rate'] for m in managers) / len(managers), 1
            )
            insights.append({
                'type': 'info',
                'title': 'Sotuvchi konversiyasi',
                'text': f"O'rtacha {avg_conv}% — yaxshilash imkoniyati bor",
            })

        summary = self.get_summary(source=source)
        if summary['lost_count']:
            insights.append({
                'type': 'idea',
                'title': 'Yashirin imkoniyat',
                'text': f"{summary['lost_count']} ta yutqazilgan lid — qayta jalb qiling",
            })

        insights.append({
            'type': 'tip',
            'title': 'Tavsiya',
            'text': "Ko'p kanalli (call + SMS + TG) follow-up joriy qiling",
        })
        return insights

