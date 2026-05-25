import logging

import anthropic
from django.conf import settings

from apps.analytics.services import AnalyticsService

logger = logging.getLogger(__name__)

_client = None

def get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client

def get_system_prompt(source=None):
    crm_name = "CRM (AmoCRM va Bitrix24)"
    if source == 'amocrm':
        crm_name = "AmoCRM"
    elif source == 'bitrix':
        crm_name = "Bitrix24"

    return f"""Siz {crm_name} sotuv ma'lumotlarini tahlil qiladigan professional biznes analitikisiz.
Quyidagi ma'lumotlar asosida aniq, qisqa va amaliy tavsiyalar bering.
Javobni o'zbek tilida yozing. Markdown formatlash ishlating.

Sizning vazifalaringiz:
1. Sotuv ko'rsatkichlarini tahlil qilish
2. Muammolarni aniqlash
3. Yaxshilash bo'yicha aniq tavsiyalar berish
4. Ma'lumotlarga asoslangan xulosalar chiqarish
"""

def get_context_data(source=None):
    service = AnalyticsService()
    summary = service.get_summary(source=source)
    top_managers = service.get_top_managers(source=source)

    return {
        **summary,
        'top_managers': top_managers,
    }

def analyze_data(question: str, context_data: dict = None, source: str = None) -> str:
    if context_data is None:
        context_data = get_context_data(source=source)
    else:
        if not source and 'source' in context_data:
            source = context_data['source']
            if source == 'all':
                source = None

    context = f"""
## Joriy ma'lumotlar:
- Jami leads: {context_data.get('total_leads', 0)}
- Yangi leads ({context_data.get('period_days', 30)} kun): {context_data.get('new_leads', 0)}
- Yutilgan: {context_data.get('won_count', 0)}
- Yutqazilgan: {context_data.get('lost_count', 0)}
- Konversiya: {context_data.get('conversion_rate', 0):.1f}%
- O'rtacha deal hajmi: {context_data.get('avg_deal_size', 0):,.0f} so'm
- Jami tushum: {context_data.get('total_revenue', 0):,.0f} so'm
- Bu oy tushumlari: {context_data.get('monthly_revenue', 0):,.0f} so'm
- Top menejerlar: {context_data.get('top_managers', [])}
    """

    try:
        message = get_client().messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            system=get_system_prompt(source),
            messages=[
                {"role": "user", "content": f"{context}\n\nSavol: {question}"}
            ],
        )
        return message.content[0].text
    except Exception as e:
        logger.error(f"AI tahlilida xatolik: {e}")
        return f"AI tahlilida xatolik yuz berdi: {str(e)}"

def generate_weekly_report(stats: dict = None, source: str = None) -> str:
    if stats is None:
        stats = get_context_data(source=source)
    else:
        if not source and 'source' in stats:
            source = stats['source']
            if source == 'all':
                source = None

    try:
        message = get_client().messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=get_system_prompt(source),
            messages=[
                {
                    "role": "user",
                    "content": f"Quyidagi haftalik statistika asosida batafsil hisobot yoz:\n{stats}"
                }
            ],
        )
        return message.content[0].text
    except Exception as e:
        logger.error(f"Haftalik hisobot generatsiyasida xatolik: {e}")
        return f"Hisobot generatsiyasida xatolik: {str(e)}"

def stream_analyze(question: str, context_data: dict = None, source: str = None):
    if context_data is None:
        context_data = get_context_data(source=source)
    else:
        if not source and 'source' in context_data:
            source = context_data['source']
            if source == 'all':
                source = None

    context = f"""
## Joriy ma'lumotlar:
- Jami leads: {context_data.get('total_leads', 0)}
- Konversiya: {context_data.get('conversion_rate', 0):.1f}%
- Jami tushum: {context_data.get('total_revenue', 0):,.0f} so'm
- Bu oy tushumlari: {context_data.get('monthly_revenue', 0):,.0f} so'm
    """

    try:
        with get_client().messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            system=get_system_prompt(source),
            messages=[
                {"role": "user", "content": f"{context}\n\nSavol: {question}"}
            ],
        ) as stream:
            for text in stream.text_stream:
                yield text
    except Exception as e:
        logger.error(f"AI streaming xatolik: {e}")
        yield f"Xatolik: {str(e)}"
