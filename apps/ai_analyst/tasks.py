"""Avtomatik AI hisobotlar va metrik alertlar (Celery Beat)."""
import logging

from celery import shared_task

from apps.analytics.services import AnalyticsService

logger = logging.getLogger(__name__)

# Alert chegaralari (kerak bo'lsa sozlash mumkin)
CONVERSION_MIN = 18.0          # konversiya shu %dan tushsa — alert
LEADS_DROP_PCT = -25.0         # leadlar oldingi davrga nisbatan shuncha % tushsa
STUCK_DEALS_MAX = 50           # shu sondan ko'p qotgan lid bo'lsa — alert

# Hisobot/alert qaysi manbalar bo'yicha tuzilsin
_SOURCES = ['bitrix', 'amocrm']


def _safe_analysis(source, period):
    """run_agent_analysis ni xavfsiz chaqiradi (LLM xato bersa — fallback)."""
    from .agent import run_agent_analysis
    try:
        result = run_agent_analysis(source=source, period=period)
        return result.get('analysis') or ''
    except Exception as exc:
        logger.warning('AI hisobot tahlili xato (%s/%s): %s', source, period, exc)
        return ''


def _has_data(source):
    svc = AnalyticsService()
    return svc.get_summary(source=source)['total_leads'] > 0


@shared_task(name='apps.ai_analyst.tasks.generate_daily_report')
def generate_daily_report():
    from .models import GeneratedReport
    svc = AnalyticsService()
    created = 0
    for source in _SOURCES:
        if not _has_data(source):
            continue
        cmp = svc.compare_periods(source=source, period='day')
        content = _safe_analysis(source, 'day')
        if not content:
            d = cmp['current']
            content = (f"## Kunlik xulosa ({source})\n\n"
                       f"- Lidlar: **{d['leads']}**\n- Sotuvlar: **{d['won']}**\n"
                       f"- Konversiya: **{d['conversion_rate']}%**")
        GeneratedReport.objects.create(
            kind='daily', source=source,
            title=f"Kunlik hisobot — {source}",
            content=content, metrics=cmp,
        )
        created += 1
    logger.info('Kunlik AI hisobot: %s ta yaratildi', created)
    return created


@shared_task(name='apps.ai_analyst.tasks.generate_weekly_report')
def generate_weekly_report():
    from .models import GeneratedReport
    svc = AnalyticsService()
    created = 0
    for source in _SOURCES:
        if not _has_data(source):
            continue
        cmp = svc.compare_periods(source=source, period='week')
        content = _safe_analysis(source, 'week')
        if not content:
            d = cmp['current']
            content = (f"## Haftalik hisobot ({source})\n\n"
                       f"- Lidlar: **{d['leads']}**\n- Sotuvlar: **{d['won']}**\n"
                       f"- Konversiya: **{d['conversion_rate']}%**")
        report = GeneratedReport.objects.create(
            kind='weekly', source=source,
            title=f"Haftalik hisobot — {source}",
            content=content, metrics=cmp,
        )
        created += 1
        # Hisobotni RAG indeksiga qo'shamiz (kelajakda "o'tgan hafta nima edi")
        try:
            from . import report_rag
            report_rag.index_report(report)
        except Exception as exc:
            logger.warning('Hisobotni RAG ga indekslash xato: %s', exc)
    logger.info('Haftalik AI hisobot: %s ta yaratildi', created)
    return created


@shared_task(name='apps.ai_analyst.tasks.check_metric_alerts')
def check_metric_alerts():
    """Chegaralarni tekshiradi va buzilsa MetricAlert yaratadi."""
    from .models import MetricAlert
    svc = AnalyticsService()
    created = 0

    for source in _SOURCES:
        if not _has_data(source):
            continue

        summary = svc.get_summary(source=source, period='week')
        conv = summary['conversion_rate']
        if conv and conv < CONVERSION_MIN:
            if _alert_fresh(MetricAlert, 'conversion_rate', source):
                MetricAlert.objects.create(
                    metric='conversion_rate', source=source,
                    severity='warning', value=conv, threshold=CONVERSION_MIN,
                    message=(f"{source}: haftalik konversiya {conv}% — "
                             f"chegaradan ({CONVERSION_MIN}%) past."))
                created += 1

        cmp = svc.compare_periods(source=source, period='week')
        leads_delta = cmp['deltas']['leads']['pct']
        if leads_delta is not None and leads_delta <= LEADS_DROP_PCT:
            if _alert_fresh(MetricAlert, 'leads_drop', source):
                MetricAlert.objects.create(
                    metric='leads_drop', source=source,
                    severity='critical', value=leads_delta,
                    threshold=LEADS_DROP_PCT,
                    message=(f"{source}: leadlar oqimi o'tgan haftaga nisbatan "
                             f"{leads_delta}% tushdi."))
                created += 1

        stuck = svc.get_stuck_deals(source=source, days_idle=14)
        if stuck['total_stuck'] > STUCK_DEALS_MAX:
            if _alert_fresh(MetricAlert, 'stuck_deals', source):
                MetricAlert.objects.create(
                    metric='stuck_deals', source=source,
                    severity='info', value=stuck['total_stuck'],
                    threshold=STUCK_DEALS_MAX,
                    message=(f"{source}: {stuck['total_stuck']} ta lid 14 kundan "
                             f"beri harakatsiz — follow-up kerak."))
                created += 1

    logger.info('Metrik alert tekshiruvi: %s ta yangi alert', created)
    return created


def _alert_fresh(model, metric, source, hours=12):
    """So'nggi `hours` soatda shu metrik/manba uchun alert bo'lmaganini tekshiradi."""
    from datetime import timedelta
    from django.utils import timezone
    since = timezone.now() - timedelta(hours=hours)
    return not model.objects.filter(
        metric=metric, source=source, created_at__gte=since).exists()
