"""Agent — savdo dashboard ma'lumotlarini avtomatik tahlil qiluvchi.

LangChain **AgentExecutor** ishlatiladi. Agentga to'rtta maxsus *tool*
beriladi — har biri ``AnalyticsService`` orqali dashboard ma'lumotlarini
(lidlar, calllar, konversiya, sotuv, voronka, yutqazish sabablari)
qaytaradi. Claude bu tool'larni o'zi chaqirib, ma'lumotni ko'rib chiqadi
va xulosa beradi: qaysi menejer past ishlayapti, voronkaning qaysi
bosqichi zaif, nima qilish kerak.

Asosiy kirish nuqtasi — :func:`run_agent_analysis`.
"""
import json
import logging

from apps.analytics.services import AnalyticsService

from .langchain_setup import get_llm

logger = logging.getLogger(__name__)

# Agentni cheksiz tsikldan saqlash uchun tool chaqiruvlari chegarasi.
MAX_ITERATIONS = 8

# Agentning vazifasi va xulqi.
_SYSTEM_PROMPT = """Siz savdo bo'limining professional AI tahlilchisisiz.
Sizga dashboard ma'lumotlarini qaytaruvchi tool'lar berilgan. Avval
kerakli tool'larni chaqirib ma'lumotlarni yig'ing, keyin tahlil qiling.

Tahlil natijasi quyidagilarni o'z ichiga olishi shart:
1. Umumiy holat — qisqa baho.
2. Zaif menejer(lar) — kim past konversiya yoki kam sotuv ko'rsatyapti.
3. Voronkaning zaif bosqichi — qayerda eng ko'p mijoz yo'qolyapti.
4. Yutqazish sabablari — agar ma'lumot bo'lsa.
5. Aniq tavsiyalar — 3-5 ta amaliy qadam.

Javobni o'zbek tilida, Markdown formatda, sarlavhalar bilan bering."""


def _build_tools(source=None, period=None):
    """Agent uchun dashboard ma'lumotlarini qaytaruvchi tool'lar ro'yxati.

    Har bir tool ``AnalyticsService`` natijasini JSON matn sifatida
    qaytaradi. ``source`` (amocrm/bitrix/None) va ``period`` (day/week/
    month/None) closure orqali biriktiriladi.
    """
    from langchain_core.tools import Tool

    svc = AnalyticsService()

    def _summary(_input: str = '') -> str:
        """Umumiy ko'rsatkichlar."""
        return json.dumps(svc.get_summary(source=source, period=period),
                          ensure_ascii=False)

    def _managers(_input: str = '') -> str:
        """Menejerlar kesimida statistika."""
        return json.dumps(svc.get_by_manager(source=source, period=period),
                          ensure_ascii=False)

    def _funnel(_input: str = '') -> str:
        """Voronka bosqichlari va konversiyalar."""
        return json.dumps({
            'funnel': svc.get_sales_funnel(source, period),
            'conversions': svc.get_conversions(source, period),
        }, ensure_ascii=False)

    def _loss(_input: str = '') -> str:
        """Yutqazish sabablari."""
        return json.dumps(svc.get_loss_reasons(source=source, period=period),
                          ensure_ascii=False)

    def _conversions(_input: str = '') -> str:
        """Asosiy konversiya nisbatlari (rings)."""
        return json.dumps(svc.get_conversions(source, period),
                          ensure_ascii=False)

    def _daily(_input: str = '') -> str:
        """Kunlik dinamika (lid/sotuv/konversiya kun bo'yicha)."""
        return json.dumps(svc.get_daily_dynamics(source=source),
                          ensure_ascii=False)

    def _followup(_input: str = '') -> str:
        """Follow-up — qoldirilgan lidlar (menejer kesimida)."""
        managers = svc.get_by_manager(source=source, period=period)
        rows = [m for m in managers if m.get('lost')][:10] or managers[:10]
        return json.dumps(rows, ensure_ascii=False)

    def _best_days(_input: str = '') -> str:
        """Eng samarali hafta kunlari."""
        return json.dumps(svc.get_best_days(source=source, period=period),
                          ensure_ascii=False)

    return [
        Tool(
            name='dashboard_summary',
            func=_summary,
            description=(
                'Umumiy savdo ko\'rsatkichlari: jami lidlar, yangi lidlar, '
                'yutilgan/yutqazilgan bitimlar, konversiya foizi, umumiy tushum, '
                'o\'rtacha chek. Argumentsiz chaqiriladi.'
            ),
        ),
        Tool(
            name='manager_performance',
            func=_managers,
            description=(
                'Har bir menejer bo\'yicha statistika: lidlar soni, calllar, '
                'conversationlar, sotuvlar, konversiya foizi, tushum. '
                'Qaysi menejer past ishlayotganini aniqlash uchun. Argumentsiz.'
            ),
        ),
        Tool(
            name='sales_funnel',
            func=_funnel,
            description=(
                'Sotuv voronkasi bosqichlari (Lid → Call → Conversation → Sotuv) '
                'va ular orasidagi konversiyalar. Voronkaning zaif bosqichini '
                'aniqlash uchun. Argumentsiz chaqiriladi.'
            ),
        ),
        Tool(
            name='loss_reasons',
            func=_loss,
            description=(
                'Bitimlarni yutqazish sabablari va ularning soni. '
                'Argumentsiz chaqiriladi.'
            ),
        ),
        Tool(
            name='conversions_data',
            func=_conversions,
            description=(
                'Asosiy konversiya nisbatlari: Call→Conversation, '
                'Conversation→Sale, Lid→Sale. Argumentsiz chaqiriladi.'
            ),
        ),
        Tool(
            name='daily_dynamics',
            func=_daily,
            description=(
                'Kunlik dinamika — har kun bo\'yicha lidlar, sotuvlar va '
                'konversiya foizi. Argumentsiz chaqiriladi.'
            ),
        ),
        Tool(
            name='followup_data',
            func=_followup,
            description=(
                'Follow-up — menejerlar bo\'yicha qoldirilgan/yutqazgan va '
                'qayta yopilgan bitimlar. Argumentsiz chaqiriladi.'
            ),
        ),
        Tool(
            name='best_days_data',
            func=_best_days,
            description=(
                'Hafta kunlari bo\'yicha eng samarali kunlar. Argumentsiz.'
            ),
        ),
    ]


def chat_with_agent(question: str, manager_id: int = 0,
                    source=None, period=None) -> dict:
    """Erkin suhbat — AgentExecutor + DB tool'lar + suhbat memory.

    Widget va `/ai-chat/` sahifasi shu funksiyani chaqiradi. Foydalanuvchi
    konversiya, sotuv, menejerlar haqida savol berganda agent avval mos
    tool'larni chaqirib real ma'lumotni o'qiydi, keyin javob beradi —
    foydalanuvchidan raqam so'ramaydi.

    Args:
        question: foydalanuvchi savoli.
        manager_id: suhbat egasi IDsi (umumiy uchun 0).
        source: CRM filtri — ``'amocrm'`` | ``'bitrix'`` | ``None``.
        period: davr filtri — ``'day'`` | ``'week'`` | ``'month'`` | ``None``.

    Returns:
        ``{'answer': str, 'sources': list[str], 'used_rag': bool, 'steps': list[str]}``.
    """
    from langchain.agents import AgentExecutor, create_tool_calling_agent
    from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

    from . import memory as memory_mod

    question = (question or '').strip()
    if not question:
        return {'answer': 'Savol bo\'sh.', 'sources': [],
                'used_rag': False, 'steps': []}

    tools = _build_tools(source, period)

    chat_system = (
        'Siz savdo dashboardining AI yordamchisisiz. Sizga real bazaga ulangan '
        'tool\'lar berilgan: dashboard_summary, manager_performance, sales_funnel, '
        'conversions_data, daily_dynamics, loss_reasons, followup_data, '
        'best_days_data. '
        '\n\nMUHIM QOIDALAR:\n'
        '1. Foydalanuvchidan HECH QACHON raqam, statistika yoki ma\'lumot SO\'RAMANG. '
        'Barcha ma\'lumot tool\'lar orqali mavjud — kerakli tool\'ni chaqiring va '
        'real DB qiymatlaridan javob bering.\n'
        '2. "Konversiya", "sotuv", "menejer", "voronka", "kunlik dinamika", '
        '"yutqazish sabablari" kabi savollarga mos tool\'ni chaqiring.\n'
        '3. Tool\'dan kelgan natijani aniq raqamlar bilan ko\'rsating '
        '(masalan: "Konversiya: 23.4%, jami lidlar: 1240, sotuvlar: 290").\n'
        '4. Javob o\'zbek tilida, qisqa va aniq. Markdown ishlatish mumkin.\n'
        '5. Agar savol tizim ma\'lumotlariga taalluqli bo\'lmasa (umumiy salom-'
        'alik, savdo maslahati va h.k.) — tool chaqirmasdan javob bering.'
    )

    mem = memory_mod.build_memory(manager_id,
                                  input_key='input', output_key='output')
    history_msgs = mem.chat_memory.messages

    prompt = ChatPromptTemplate.from_messages([
        ('system', chat_system),
        MessagesPlaceholder('history'),
        ('human', '{input}'),
        MessagesPlaceholder('agent_scratchpad'),
    ])

    agent = create_tool_calling_agent(get_llm(temperature=0.3), tools, prompt)
    executor = AgentExecutor(
        agent=agent, tools=tools, max_iterations=MAX_ITERATIONS,
        handle_parsing_errors=True, return_intermediate_steps=True,
        verbose=False,
    )

    result = executor.invoke({'input': question, 'history': history_msgs})

    output = result['output']
    if isinstance(output, list):
        output = '\n'.join(
            b.get('text', '') if isinstance(b, dict) else str(b)
            for b in output
        )

    steps = [getattr(a, 'tool', 'tool')
             for a, _ in result.get('intermediate_steps', [])]

    # Suhbat tarixini bazaga yozamiz.
    try:
        memory_mod.save_turn(manager_id, question, output)
    except Exception as exc:  # noqa: BLE001
        logger.warning('Memory save xato: %s', exc)

    logger.info('Chat agent: manager=%s, tools=%s', manager_id, steps)
    return {'answer': output, 'sources': [],
            'used_rag': False, 'steps': steps}


def run_agent_analysis(source=None, period=None) -> dict:
    """Dashboard ma'lumotlarini AgentExecutor orqali avtomatik tahlil qiladi.

    Args:
        source: CRM manbasi filtri — ``'amocrm'``, ``'bitrix'`` yoki ``None``
            (barchasi).
        period: davr filtri — ``'day'`` | ``'week'`` | ``'month'`` | ``None``.

    Returns:
        ``{'analysis': str, 'steps': list[str]}`` — tahlil matni va agent
        chaqirgan tool'lar ro'yxati.
    """
    from langchain.agents import AgentExecutor, create_tool_calling_agent
    from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

    tools = _build_tools(source, period)

    prompt = ChatPromptTemplate.from_messages([
        ('system', _SYSTEM_PROMPT),
        ('human', '{input}'),
        MessagesPlaceholder('agent_scratchpad'),
    ])

    agent = create_tool_calling_agent(get_llm(temperature=0.2), tools, prompt)
    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        max_iterations=MAX_ITERATIONS,
        handle_parsing_errors=True,
        return_intermediate_steps=True,
        verbose=False,
    )

    task = (
        'Savdo dashboard ma\'lumotlarini to\'liq tahlil qil. Barcha kerakli '
        'tool\'lardan foydalanib, zaif menejerlar va voronkaning zaif bosqichini '
        'aniqla hamda aniq tavsiyalar ber.'
    )

    result = executor.invoke({'input': task})

    # Claude javobi matn yoki kontent bloklari ro'yxati bo'lishi mumkin —
    # ikkala holatni ham bitta matnga keltiramiz.
    output = result['output']
    if isinstance(output, list):
        output = '\n'.join(
            block.get('text', '') if isinstance(block, dict) else str(block)
            for block in output
        )

    # Agent qaysi tool'larni chaqirganini yig'amiz (shaffoflik uchun).
    steps = []
    for action, _observation in result.get('intermediate_steps', []):
        steps.append(getattr(action, 'tool', 'tool'))

    logger.info('Agent tahlili tugadi: %s tool chaqirildi', len(steps))
    return {'analysis': output, 'steps': steps}


# =============================================================================
# Har-karta AI — bitta dashboard kartasini tahlil qilish va ko'rinishini
# foydalanuvchi istagiga moslab o'zgartirish (dinamik dashboard uchun).
# =============================================================================

# Barcha kartalarda ruxsat etiladigan grafik turlari (multi-metric ham
# ishlaydi). Frontend `drawSpecChart` shularning hammasini chizadi.
_VIEWS_FULL = [
    'table', 'bar', 'line', 'area', 'pie', 'doughnut',
    'horizontalBar', 'stacked',
]

# Har bir dashboard kartasining "metama'lumoti". AI shu asosda qaysi
# sonli ko'rsatkich va qaysi ko'rinish (chart turi) mumkinligini biladi —
# bu uni xato/xavfli qiymat qaytarishdan saqlaydi.
_CARD_FIELDS = {
    'funnel': {
        'label': 'Savdo voronkasi',
        'numeric': ['count', 'pct'],
        'category': 'name',
        'views': _VIEWS_FULL,
        'tool': 'sales_funnel',
    },
    'managers': {
        'label': 'Menejerlar reytingi',
        'numeric': ['revenue', 'won', 'calls', 'conversations', 'total_leads',
                    'conversion_rate', 'convo_rate', 'sale_rate', 'lead_to_sale'],
        'category': 'manager_name',
        'views': _VIEWS_FULL,
        'tool': 'manager_performance',
    },
    'loss': {
        'label': 'Sotib olmadi (sabablar)',
        'numeric': ['count'],
        'category': 'reason',
        'views': _VIEWS_FULL,
        'tool': 'loss_reasons',
    },
    'finance': {
        'label': "Moliy ko'rsatkichlar",
        'numeric': ['total_revenue', 'avg_deal', 'lead_value', 'sale_value'],
        'category': None,
        'views': _VIEWS_FULL + ['kpi'],
        'tool': 'dashboard_summary',
    },
    'conversions': {
        'label': 'Asosiy konversiyalar',
        'numeric': ['pct', 'num', 'den'],
        'category': 'label',
        'views': _VIEWS_FULL,
        'tool': 'conversions_data',
    },
    'daily': {
        'label': 'Kunlik dinamika',
        'numeric': ['leads', 'sales', 'conversion'],
        'category': 'date',
        'views': _VIEWS_FULL,
        'tool': 'daily_dynamics',
    },
    'followup': {
        'label': 'Qoldirilganlar (Follow-up)',
        'numeric': ['lost', 'won', 'conversion_rate'],
        'category': 'manager_name',
        'views': _VIEWS_FULL,
        'tool': 'followup_data',
    },
    'best_days': {
        'label': 'Eng yaxshi kunlar',
        'numeric': ['leads', 'won', 'conversion'],
        'category': 'day',
        'views': _VIEWS_FULL,
        'tool': 'best_days_data',
    },
}

# Tashqi modullar tekshiruvi uchun — ruxsat etilgan karta kalitlari.
CARD_KEYS = tuple(_CARD_FIELDS.keys())


def _card_data(card, source=None, period=None):
    """Bitta karta uchun ``AnalyticsService`` xom ma'lumotini qaytaradi."""
    svc = AnalyticsService()
    if card == 'funnel':
        return {
            'funnel': svc.get_sales_funnel(source, period),
            'conversions': svc.get_conversions(source, period),
        }
    if card == 'managers':
        return svc.get_by_manager(source=source, period=period)
    if card == 'loss':
        return svc.get_loss_reasons(source=source, period=period)
    if card == 'finance':
        return svc.get_finance(source=source, period=period)
    if card == 'conversions':
        return svc.get_conversions(source, period)
    if card == 'daily':
        return svc.get_daily_dynamics(source=source)
    if card == 'followup':
        managers = svc.get_by_manager(source=source, period=period)
        return [m for m in managers if m.get('lost')][:10] or managers[:10]
    if card == 'best_days':
        return svc.get_best_days(source=source, period=period)
    raise ValueError(f'Noma\'lum karta: {card}')


def run_card_analysis(card, source=None, period=None) -> dict:
    """Bitta dashboard kartasini LangChain AgentExecutor orqali tahlil qiladi.

    Global :func:`run_agent_analysis` dan farqi — agentga faqat shu
    kartaga tegishli bitta tool beriladi, natija qisqa va fokuslangan
    bo'ladi (karta ichida ko'rsatish uchun).

    Args:
        card: karta kaliti — ``funnel`` | ``managers`` | ``loss`` | ``finance``.
        source: CRM manbasi filtri.
        period: davr filtri — ``day`` | ``week`` | ``month`` | ``None``.

    Returns:
        ``{'analysis': str, 'steps': list[str]}``.
    """
    from langchain.agents import AgentExecutor, create_tool_calling_agent
    from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

    meta = _CARD_FIELDS.get(card)
    if not meta:
        raise ValueError(f'Noma\'lum karta: {card}')

    # Faqat shu kartaga tegishli tool(lar)ni qoldiramiz.
    all_tools = _build_tools(source, period)
    tools = [t for t in all_tools if t.name == meta['tool']] or all_tools

    system_text = (
        f'Siz savdo bo\'limining AI tahlilchisisiz. Sizga "{meta["label"]}" '
        'kartasi uchun tool berilgan. Avval tool\'ni chaqirib ma\'lumotni '
        'oling, keyin QISQA tahlil bering: 1) holatga baho, 2) asosiy '
        'muammo yoki kuchli tomon, 3) 2-3 ta aniq amaliy tavsiya. '
        'Javob o\'zbek tilida, Markdown formatda, 130 so\'zdan oshmasin.'
    )
    prompt = ChatPromptTemplate.from_messages([
        ('system', system_text),
        ('human', '{input}'),
        MessagesPlaceholder('agent_scratchpad'),
    ])

    agent = create_tool_calling_agent(get_llm(temperature=0.2), tools, prompt)
    executor = AgentExecutor(
        agent=agent, tools=tools, max_iterations=4,
        handle_parsing_errors=True, return_intermediate_steps=True,
        verbose=False,
    )
    result = executor.invoke({
        'input': f'"{meta["label"]}" kartasi ma\'lumotlarini tahlil qil.',
    })

    output = result['output']
    if isinstance(output, list):
        output = '\n'.join(
            b.get('text', '') if isinstance(b, dict) else str(b)
            for b in output
        )
    steps = [getattr(a, 'tool', 'tool')
             for a, _ in result.get('intermediate_steps', [])]
    logger.info('Karta tahlili tugadi: card=%s, %s tool', card, len(steps))
    return {'analysis': output, 'steps': steps}


# AI qaytaradigan view-spec JSON sxemasi shabloni. ``with_structured_output``
# modeldan aynan shu tuzilishni majburan talab qiladi — model erkin HTML
# emas, faqat oldindan belgilangan, xavfsiz parametrlarni to'ldiradi.
def _view_spec_schema(meta):
    """Karta metama'lumotidan view-spec JSON sxemasini quradi."""
    return {
        'title': 'CardViewSpec',
        'description': 'Dashboard kartasini ko\'rsatish konfiguratsiyasi.',
        'type': 'object',
        'properties': {
            'viewType': {
                'type': 'string', 'enum': meta['views'],
                'description': ('Karta qanday ko\'rinishda chizilsin. '
                                'bar/line/area/stacked — multi-metric, '
                                'pie/doughnut/horizontalBar — bitta metrik, '
                                'table — jadval, kpi — katta sonli kartalar.'),
            },
            'metric': {
                'type': 'string',
                'description': ('Asosiy sonli ko\'rsatkich (pie/doughnut va '
                                'saralash uchun ishlatiladi). Faqat shulardan '
                                'biri: ' + ', '.join(meta['numeric'])),
            },
            'metrics': {
                'type': 'array',
                'items': {'type': 'string', 'enum': meta['numeric']},
                'description': ('Bitta grafikda birga chiziladigan barcha '
                                'ko\'rsatkichlar (bar/line/area/stacked '
                                'uchun). Foydalanuvchi bir nechta '
                                'ko\'rsatkichni so\'rasa shu yerga yozing, '
                                'aks holda faqat "metric" ni takrorlang. '
                                'Faqat shulardan tanlang: '
                                + ', '.join(meta['numeric'])),
            },
            'sortBy': {
                'type': 'string',
                'description': ('Saralash maydoni — sonli maydonlardan biri '
                                'yoki bo\'sh satr (saralamaslik).'),
            },
            'sortDir': {
                'type': 'string', 'enum': ['asc', 'desc'],
                'description': 'Saralash yo\'nalishi: asc (o\'sish) yoki desc.',
            },
            'limit': {
                'type': 'integer',
                'description': 'Nechta element ko\'rsatilsin. 0 — barchasi.',
            },
            'title': {
                'type': 'string',
                'description': 'Karta uchun yangi qisqa sarlavha.',
            },
            'note': {
                'type': 'string',
                'description': 'O\'zbekcha bitta jumla — nima o\'zgartirildi.',
            },
        },
        'required': ['viewType', 'metric', 'metrics', 'sortBy', 'sortDir',
                     'limit', 'title', 'note'],
    }


def build_card_view_spec(card, instruction, source=None, period=None) -> dict:
    """Foydalanuvchi istagiga ko'ra kartaning ko'rinish konfiguratsiyasini qaytaradi.

    LangChain ``ChatAnthropic`` modeli ``with_structured_output`` bilan
    ishlatiladi — model erkin matn yoki HTML emas, qat'iy JSON sxemani
    qaytaradi. Bu xavfsiz: AI faqat oldindan belgilangan parametrlarni
    (chart turi, metrik, saralash, limit) to'ldiradi, frontend esa shu
    konfiguratsiya asosida kartani chizadi.

    Args:
        card: karta kaliti.
        instruction: foydalanuvchining erkin matnli istagi, masalan
            "pie chart qil" yoki "faqat top 3 menejerni ko'rsat".
        source, period: ma'lumot filtri (model namuna ko'rishi uchun).

    Returns:
        view-spec lug'ati: ``card``, ``viewType``, ``metric``, ``sortBy``,
        ``sortDir``, ``limit``, ``title``, ``note``.
    """
    meta = _CARD_FIELDS.get(card)
    if not meta:
        raise ValueError(f'Noma\'lum karta: {card}')

    # Modelga ma'lumot tuzilishini ko'rsatish uchun qisqa namuna.
    data = _card_data(card, source, period)
    sample = json.dumps(data, ensure_ascii=False)[:1400]

    structured = get_llm(temperature=0).with_structured_output(
        _view_spec_schema(meta)
    )

    message = (
        f'Karta nomi: "{meta["label"]}".\n'
        f'Mumkin ko\'rinish turlari: {", ".join(meta["views"])}.\n'
        f'Mavjud sonli maydonlar: {", ".join(meta["numeric"])}.\n'
        f'Ma\'lumot namunasi (JSON): {sample}\n\n'
        f'Foydalanuvchining istagi: "{instruction}"\n\n'
        'Shu istakka eng mos keladigan view-spec ni qaytar. Agar '
        'foydalanuvchi bir nechta ko\'rsatkichni (masalan "lid, sotuv, '
        'qo\'ng\'iroq ko\'rinsin") so\'rasa, ularning hammasini "metrics" '
        'massiviga yoz va viewType ni bar/line/area/stacked dan tanla — '
        'pie/doughnut faqat bitta ko\'rsatkich uchun mos. Agar istak '
        'noaniq bo\'lsa, ma\'lumotga eng mantiqiy ko\'rinishni tanla. '
        '"metric" va "sortBy" albatta ko\'rsatilgan sonli maydonlardan '
        'bo\'lishi shart; "metrics" bo\'sh bo\'lmasin (kamida [metric]).'
    )
    spec = structured.invoke(message)
    # with_structured_output natijasi dict yoki obyekt bo'lishi mumkin.
    if not isinstance(spec, dict):
        spec = dict(spec)
    # Xavfsiz fallback: metrics bo'sh bo'lsa, kamida asosiy metric ni qo'yamiz.
    metrics = spec.get('metrics') or []
    if not isinstance(metrics, list):
        metrics = []
    metrics = [m for m in metrics if m in meta['numeric']]
    if not metrics and spec.get('metric') in meta['numeric']:
        metrics = [spec['metric']]
    spec['metrics'] = metrics
    spec['card'] = card
    logger.info('View-spec yaratildi: card=%s, viewType=%s',
                card, spec.get('viewType'))
    return spec
