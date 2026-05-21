import logging
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum, Count, Avg, Q, F
from django.utils import timezone

from apps.amocrm.models import Lead, Pipeline, PipelineStatus

logger = logging.getLogger(__name__)

# AmoCRM yutilgan/yutqazilgan status ID lari (standart)
WON_STATUS_ID = 142  # Muvaffaqiyatli yakunlangan
LOST_STATUS_ID = 143  # Yutqazilgan


class AnalyticsService:
    """Sotuv tahlillari va statistika hisoblash servisi.

    Barcha methodlar ixtiyoriy `source` parametrini qabul qiladi:
      - None  → barcha CRM lardan
      - 'amocrm' → faqat AmoCRM
      - 'bitrix' → faqat Bitrix24
    """

    def _base_queryset(self, source=None):
        """Asosiy queryset — source filter bilan."""
        qs = Lead.objects.all()
        if source:
            qs = qs.filter(source=source)
        return qs

    def get_summary(self, days=30, source=None):
        """Umumiy statistikani olish."""
        start_date = timezone.now() - timedelta(days=days)
        leads = self._base_queryset(source)
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
        """Sotuv funnel (voronka) ma'lumotlarini olish."""
        leads = self._base_queryset(source)
        if pipeline_id:
            leads = leads.filter(pipeline_id=pipeline_id)

        # Pipeline statuslari bo'yicha guruhlamoq
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

    def get_by_manager(self, days=30, source=None):
        """Menejer bo'yicha statistika."""
        start_date = timezone.now() - timedelta(days=days)

        from apps.amocrm.models import User as AmoCRMUser

        managers = AmoCRMUser.objects.all()
        result = []

        for manager in managers:
            manager_leads = self._base_queryset(source).filter(
                responsible_user_id=manager.amocrm_id
            )
            recent_leads = manager_leads.filter(created_at__gte=start_date)

            total = manager_leads.count()
            won = manager_leads.filter(status_id=WON_STATUS_ID).count()
            lost = manager_leads.filter(status_id=LOST_STATUS_ID).count()
            revenue = manager_leads.filter(
                status_id=WON_STATUS_ID
            ).aggregate(total=Sum('price'))['total'] or 0

            conversion = 0
            closed = won + lost
            if closed > 0:
                conversion = (won / closed) * 100

            result.append({
                'manager_id': manager.amocrm_id,
                'manager_name': manager.name,
                'total_leads': total,
                'recent_leads': recent_leads.count(),
                'won': won,
                'lost': lost,
                'revenue': float(revenue),
                'conversion_rate': round(conversion, 1),
            })

        # Revenue bo'yicha tartiblash
        result.sort(key=lambda x: x['revenue'], reverse=True)
        return result

    def get_leads_trend(self, days=30, source=None):
        """Kunlik lead dinamikasi."""
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
        """Kunlik tushum dinamikasi."""
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

    def get_top_managers(self, limit=5, source=None):
        """Eng yaxshi menejerlar (tushum bo'yicha)."""
        managers = self.get_by_manager(source=source)
        return managers[:limit]

