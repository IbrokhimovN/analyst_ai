import json
import logging

from apps.analytics.services import AnalyticsService

from .langchain_setup import get_llm

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 8

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
    from langchain_core.tools import Tool

    svc = AnalyticsService()

    def _summary(_input: str = '') -> str:
        return json.dumps(svc.get_summary(source=source, period=period),
                          ensure_ascii=False)

    def _managers(_input: str = '') -> str:
        return json.dumps(svc.get_by_manager(source=source, period=period),
                          ensure_ascii=False)

    def _funnel(_input: str = '') -> str:
        return json.dumps({
            'funnel': svc.get_sales_funnel(source, period),
            'conversions': svc.get_conversions(source, period),
        }, ensure_ascii=False)

    def _loss(_input: str = '') -> str:
        return json.dumps(svc.get_loss_reasons(source=source, period=period),
                          ensure_ascii=False)

    def _conversions(_input: str = '') -> str:
        return json.dumps(svc.get_conversions(source, period),
                          ensure_ascii=False)

    def _daily(_input: str = '') -> str:
        return json.dumps(svc.get_daily_dynamics(source=source),
                          ensure_ascii=False)

    def _followup(_input: str = '') -> str:
        managers = svc.get_by_manager(source=source, period=period)
        rows = [m for m in managers if m.get('lost')][:10] or managers[:10]
        return json.dumps(rows, ensure_ascii=False)

    def _best_days(_input: str = '') -> str:
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

_CHAT_SYSTEM_PROMPT = """Siz savdo dashboardining proaktiv AI yordamchisisiz.
Sizga real PostgreSQL bazaga to'liq ulangan tool'lar berilgan. Foydalanuvchi
nima so'rasa, siz tool'lar orqali aniq ma'lumot olib, BAJARISHGA harakat
qilasiz — savol o'rniga harakat.

══════════════════════════════════════════════════════════════════════════
ASOSIY QOIDALAR (qat'iy)
══════════════════════════════════════════════════════════════════════════
1. **HECH QACHON foydalanuvchidan raqam, statistika, ma'lumot SO'RAMANG.**
   Barcha ma'lumot tool'lar orqali mavjud. "Sizda bormi?", "ma'lumot bering"
   deb so'rash QAT'IY taqiqlangan.

2. **"Men qila olmayman" deyish taqiqlangan.** Agar to'g'ridan-to'g'ri tool
   topa olmasangiz, eng yaqin tool'ni chaqiring va xulosa qiling.

3. **Avval tool, keyin javob.** Statistik savolga avval kerakli tool'larni
   chaqiring, natijani o'qing, keyin javob yozing.

4. **Javob o'zbek tilida, qisqa va aniq.** Markdown ishlating: sarlavhalar,
   bullet, **qalin** raqamlar. Iloji boricha jadval ishlating.

5. **Aniq raqamlar majburiy.** Tool natijasidagi sonlarni so'zsiz ayting:
   "Konversiya: **23.4%**, jami lidlar: **1 240**, sotuvlar: **290**".

══════════════════════════════════════════════════════════════════════════
MA'LUMOT TOOL'LARI (qachon chaqirish)
══════════════════════════════════════════════════════════════════════════
• `dashboard_summary` — umumiy ko'rsatkichlar (lidlar, sotuv, tushum, KPI).
   Savollar: "umumiy holat", "qanday natijalar", "kpi", "tushum qancha".

• `manager_performance` — menejerlar reytingi (kim qancha sotgan).
   Savollar: "eng yaxshi menejer", "kim past ishlayapti", "menejer X qancha".

• `sales_funnel` — Lid→Call→Conversation→Sotuv bosqichlari va konversiyalar.
   Savollar: "voronka", "qaysi bosqichda mijoz yo'qoladi", "tushish foizi".

• `conversions_data` — asosiy konversiya nisbatlari.
   Savollar: "konversiya foizi", "call→sale", "lid→sale nisbati".

• `daily_dynamics` — kun bo'yicha lid/sotuv/konversiya dinamikasi.
   Savollar: "kunlik tendensiya", "oxirgi 7 kun", "qaysi kun yaxshi edi".

• `loss_reasons` — bitimlarni yutqazish sabablari (sotib olmadi).
   Savollar: "nega sotib olmaganlar", "sabablari", "qaytarish ko'rsatkichlari".

• `followup_data` — qoldirilgan/yutqazgan lidlar, menejer kesimida.
   Savollar: "kim follow-up qilmagan", "qoldirilgan mijozlar".

• `best_days_data` — hafta kunlari bo'yicha samaradorlik.
   Savollar: "qaysi kuni yaxshi sotamiz", "dushanba/juma qanday".

══════════════════════════════════════════════════════════════════════════
HARAKAT TOOL'LARI (dashboard'ni boshqarish — chatda grafik chizish YOQ)
══════════════════════════════════════════════════════════════════════════
**MUHIM:** Grafik/chart/diagramma so'rovi har doim **dashboard'ga** boradi,
chatga emas. Buning uchun `dashboard_command(action='add_custom_card', ...)`
ishlatiladi.

• `dashboard_command` — asosiy dashboard'ni boshqaradi. Foydalanuvchi
   "kartani yashir/ko'rsat", "voronka kartasini olib tashla", "managers
   kartasini pie qil", "dashboard'da X kartani qo'sh" desa shuni chaqiring.

   Parametrlar:
     - `action` — quyidagilardan biri:
        * `show_card` / `hide_card` — bitta kartani ko'rsatish/yashirish.
        * `set_card_view` — mavjud karta ko'rinishini o'zgartirish (jadval/
          grafik turi va metrikani almashtirish).
        * `add_custom_card` — dashboard ostiga **yangi** maxsus karta qo'shish
          (foydalanuvchi xohlagan tur va metrika bilan).
        * `remove_custom_card` — bitta maxsus kartani o'chirish (card kaliti).
        * `remove_all_custom` — foydalanuvchi qo'shgan barcha maxsus kartalarni
          o'chirish.
        * `show_all_cards` — yashirilgan asosiy kartalarning **hammasini**
          qaytarish.
        * `hide_all_cards` — asosiy kartalarning hammasini yashirish (tahrir/
          tozalash uchun).
        * `refresh_dashboard` — dashboard'ni yangilash.
        * `open_ai_panel` — kartaning AI tahlil panelini ochish.
     - `card` — karta kaliti (yuqoridagi 8 ta dan biri).
     - `view_type` — **43 ta canonical tur** mavjud (har biri haqiqatan
       chiziladi):
       • **Bar oilasi (9)**: barChart, columnChart, groupedBar, stackedBar,
         horizontalBar, horizontalStackedBar, percentBar, rangeBar, bulletChart.
       • **Line/Area oilasi (14)**: lineChart, areaChart, stackedArea,
         streamGraph, stepChart, bumpChart, sparkline, smoothLine,
         straightLine, dashedLine, multiLine, pointLine, smoothArea,
         percentArea.
       • **Pie/Radial (11)**: pieChart, doughnutChart, halfPie, halfDoughnut,
         semicircleDoughnut, gaugeChart, polarArea, nightingaleRose,
         waffleChart, sunburst, marimekko.
       • **Distribution (5)**: histogram, boxPlot, violinPlot, dotPlot,
         densityChart.
       • **Scatter/Correlation (7)**: scatterPlot, bubbleChart,
         connectedScatter, jitterScatter, bubbleHeatmap, heatmap,
         correlationMatrix.
       • **Radar/Spider (4)**: radarChart, spiderChart, filledRadar, multiRadar.
       • **Geo (4)**: choroplethMap, bubbleMap, flowMap, geoHeatmap.
       • **Flow/Hierarchy (5)**: sankeyDiagram, funnelChart, waterfallChart,
         ganttChart, treemap.
       • **Network (3)**: networkGraph, chordDiagram, arcDiagram.
       • **Display/KPI (5)**: kpiCard, metricTile, progressBar, table,
         numberCards.
     - `metric` — asosiy sonli maydon (managers uchun 'revenue'/'won'/'calls',
       funnel uchun 'count'/'pct' va h.k.).
     - `metrics` — bir nechta birga ko'rsatish kerak bo'lsa massiv.
     - `sort_by`, `sort_dir`, `limit`, `title` — boshqa parametrlar.

   Misollar:
   • "Loss kartasini yashir" →
     `dashboard_command(action='hide_card', card='loss')`.
   • "Menejerlar kartasini doughnut qil" →
     `dashboard_command(action='set_card_view', card='managers',
     view_type='doughnut', metric='revenue', limit=5)`.
   • "Menejerlarni pie chart qil" / "menejerlarni pie chartda ko'rsat" →
     `dashboard_command(action='add_custom_card', card='managers',
     view_type='pieChart', metric='revenue', limit=10,
     title='Menejerlar ulushi')`.
   • "Kunlik sotuv va lidlarni bar chart qil" →
     `dashboard_command(action='add_custom_card', card='daily',
     view_type='barChart', metric='leads',
     metrics=['leads', 'sales'], title='Kunlik dinamika')`.
   • "Hamma kartalarni tozala" →
     `dashboard_command(action='remove_all_custom')`.
   • "Barcha kartalarni qaytar" →
     `dashboard_command(action='show_all_cards')`.

══════════════════════════════════════════════════════════════════════════
XULOSA STILI
══════════════════════════════════════════════════════════════════════════
• Statistika savoliga: 1-2 jumla xulosa + jadval/ro'yxat + tavsiya.
• Grafik/chart/diagramma so'rasa: `dashboard_command(action='add_custom_card')`
  ni chaqiring, javobda QISQA tasdiq yozing ("✅ Karta dashboard'ga qo'shildi.").
  Chatda grafik chizish YOQ — har doim dashboard'ga qo'yiladi.
• Dashboard buyrug'iga: `dashboard_command` ni chaqiring, tasdiqlang
  ("Loss kartasi yashirildi.").
• Salom-alik yoki bog'liq bo'lmagan savolga: tool chaqirmasdan qisqa javob.
"""

_VOICE_MODE_SUFFIX = """

══════════════════════════════════════════════════════════════════════════
OVOZLI REJIM (foydalanuvchi mikrofondan so'radi) — QAT'IY QOIDALAR
══════════════════════════════════════════════════════════════════════════

1. **`make_chart` ni HECH QACHON CHAQIRMANG.** Bu rejimda chatda grafik
   chizish QAT'IY taqiqlangan. Agar foydalanuvchi "grafik qil", "chart qil",
   "bar chart qil", "pie qil", "diagramma ko'rsat" desa — siz har doim
   `dashboard_command` ni `action='add_custom_card'` bilan chaqiring va
   grafikni DASHBOARD'ga qo'ying, chatga emas.

2. **Faqat `dashboard_command` ishlatasiz.** Grafik so'rovi → dashboard'ga
   qo'shing. Karta o'zgartirish → `set_card_view` yoki `add_custom_card`.
   Yashirish/ko'rsatish → `hide_card`/`show_card`.

3. **Javob MAKSIMAL QISQA — 1-2 jumla, faqat tasdiq matni.**
   • Hech qanday markdown jadval, ro'yxat, sarlavha YOQ.
   • Statistika, raqamlar ro'yxati, tahlil YOQ.
   • Emoji-li uzun ro'yxatlar YOQ.

4. **Tasdiq matnlari misollari:**
   • Grafik so'rovi: "✅ Karta dashboard'ga qo'shildi."
   • O'zgarish: "✅ Voronka kartasi pie chartga aylantirildi."
   • Yashirish: "✅ Loss kartasi yashirildi."

5. **Ma'lumot so'rovida** (savol-javob, grafik so'ralmagan) — faqat asosiy
   raqamni bir jumlada ayting. Misol: "Bugungi tushum 12 million so'm."
   Jadval, ro'yxat YOQ.
"""


def chat_with_agent(question: str, manager_id: int = 0,
                    source=None, period=None, is_voice: bool = False) -> dict:
    from langchain.agents import AgentExecutor, create_tool_calling_agent
    from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain_core.tools import StructuredTool
    from pydantic import BaseModel, Field
    from typing import List, Optional

    from . import memory as memory_mod

    question = (question or '').strip()
    if not question:
        return {'answer': 'Savol bo\'sh.', 'sources': [],
                'used_rag': False, 'steps': [],
                'charts': [], 'commands': []}

    chart_specs = []
    commands = []

    base_tools = _build_tools(source, period)

    def _make_chart_tool(card='', view_type='bar', metric='', metrics=None,
                         sort_by='', sort_dir='desc', limit=0, title='') -> str:
        if card not in _CARD_FIELDS:
            return (f'Xato: noma\'lum karta "{card}". Quyidagilardan tanlang: '
                    f'{", ".join(_CARD_FIELDS.keys())}.')
        spec, err = _build_chat_chart_spec(
            card=card, view_type=view_type, metric=metric,
            metrics=metrics or [], sort_by=sort_by, sort_dir=sort_dir,
            limit=int(limit or 0), title=title,
            source=source, period=period,
        )
        if err:
            return f'Xato: {err}'
        chart_specs.append(spec)
        return (f'Grafik tayyorlandi: card={card}, type={view_type}, '
                f'rows={len(spec.get("labels", []))}. Foydalanuvchiga '
                'qisqa sharh yozing — grafik javob ostida ko\'rinadi.')

    def _dashboard_command_tool(action='', card='', view_type='bar',
                                 metric='', metrics=None, sort_by='',
                                 sort_dir='desc', limit=0, title='') -> str:
        action = (action or '').strip()
        valid_actions = {
            'show_card', 'hide_card', 'set_card_view',
            'refresh_dashboard', 'open_ai_panel',
            'show_all_cards', 'hide_all_cards',
            'add_custom_card', 'remove_custom_card', 'remove_all_custom',
        }
        if action not in valid_actions:
            return (f'Xato: action "{action}" noma\'lum. '
                    f'Mavjud: {", ".join(sorted(valid_actions))}.')

        no_card_actions = {'refresh_dashboard', 'show_all_cards',
                            'hide_all_cards', 'remove_all_custom'}
        if action not in no_card_actions and card not in _CARD_FIELDS:
            return (f'Xato: noma\'lum karta "{card}". '
                    f'Mavjud: {", ".join(_CARD_FIELDS.keys())}.')

        cmd = {'action': action, 'card': card}
        if action in ('set_card_view', 'add_custom_card'):
            spec, err = _build_chat_chart_spec(
                card=card, view_type=view_type, metric=metric,
                metrics=metrics or [], sort_by=sort_by, sort_dir=sort_dir,
                limit=int(limit or 0), title=title,
                source=source, period=period,
            )
            if err:
                return f'Xato: {err}'
            cmd['spec'] = spec
        commands.append(cmd)
        return f'Buyruq dashboard\'ga yuborildi: {action} (card={card}).'

    class _MakeChartArgs(BaseModel):
        card: str = Field(description=(
            'Karta kaliti: funnel|managers|loss|finance|conversions|daily|'
            'followup|best_days.'))
        view_type: str = Field(default='bar', description=(
            'Grafik turi: bar|line|area|pie|doughnut|horizontalBar|stacked|table.'))
        metric: str = Field(default='', description=(
            'Asosiy sonli maydon (kartaga mos).'))
        metrics: Optional[List[str]] = Field(default=None, description=(
            'Bir nechta sonli maydon (bar/line/area/stacked uchun).'))
        sort_by: str = Field(default='', description='Saralash maydoni.')
        sort_dir: str = Field(default='desc', description='asc yoki desc.')
        limit: int = Field(default=0, description='Nechta element (0 — barchasi).')
        title: str = Field(default='', description='Grafik sarlavhasi.')

    class _DashCmdArgs(BaseModel):
        action: str = Field(description=(
            'Buyruq: show_card | hide_card | set_card_view | refresh_dashboard'
            ' | open_ai_panel | show_all_cards | hide_all_cards | '
            'add_custom_card | remove_custom_card | remove_all_custom.'))
        card: str = Field(default='', description=(
            'Karta kaliti (show_all_cards/hide_all_cards/refresh_dashboard/'
            'remove_all_custom uchun bo\'sh; add_custom_card/set_card_view '
            'va boshqalar uchun majburiy).'))
        view_type: str = Field(default='bar', description='set_card_view uchun.')
        metric: str = Field(default='', description='set_card_view uchun.')
        metrics: Optional[List[str]] = Field(default=None,
                                              description='set_card_view uchun.')
        sort_by: str = Field(default='', description='set_card_view uchun.')
        sort_dir: str = Field(default='desc', description='set_card_view uchun.')
        limit: int = Field(default=0, description='set_card_view uchun.')
        title: str = Field(default='', description='set_card_view uchun.')

    extra_tools = [
        StructuredTool.from_function(
            func=_dashboard_command_tool,
            name='dashboard_command',
            description=(
                'Asosiy dashboard\'ni boshqaradi: kartani ko\'rsatish/yashirish, '
                'ko\'rinishini o\'zgartirish, yangilash, yangi karta qo\'shish. '
                'Grafik/chart so\'rovlari uchun action=add_custom_card ishlatiladi.'
            ),
            args_schema=_DashCmdArgs,
        ),
    ]

    tools = base_tools + extra_tools

    mem = memory_mod.build_memory(manager_id,
                                  input_key='input', output_key='output')
    history_msgs = mem.chat_memory.messages

    system_prompt = _CHAT_SYSTEM_PROMPT + (_VOICE_MODE_SUFFIX if is_voice else '')
    prompt = ChatPromptTemplate.from_messages([
        ('system', system_prompt),
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

    try:
        memory_mod.save_turn(manager_id, question, output)
    except Exception as exc:
        logger.warning('Memory save xato: %s', exc)

    logger.info('Chat agent: manager=%s, tools=%s, charts=%d, commands=%d',
                manager_id, steps, len(chart_specs), len(commands))
    return {'answer': output, 'sources': [], 'used_rag': False,
            'steps': steps, 'charts': chart_specs, 'commands': commands}

_METRIC_LABELS = {
    'count': 'Soni', 'pct': 'Foiz, %', 'revenue': 'Tushum', 'won': 'Sotuv',
    'calls': 'Call', 'conversations': 'Conversation', 'total_leads': 'Lidlar',
    'conversion_rate': 'Konversiya, %', 'convo_rate': 'Convo, %',
    'sale_rate': 'Sale, %', 'lead_to_sale': 'Lid->Sale, %', 'value': 'Qiymat',
    'num': 'Soni', 'den': 'Umumiy', 'leads': 'Lid', 'sales': 'Sotuv',
    'conversion': 'Konversiya, %', 'lost': 'Yutqazgan',
    'total_revenue': 'Tushum', 'avg_deal': "O'rtacha chek",
    'lead_value': '1 lid qiymati', 'sale_value': '1 sale qiymati',
}

def _chart_rows(card, source=None, period=None):
    svc = AnalyticsService()
    if card == 'funnel':
        return svc.get_sales_funnel(source, period) or []
    if card == 'managers':
        return svc.get_by_manager(source=source, period=period) or []
    if card == 'loss':
        return svc.get_loss_reasons(source=source, period=period) or []
    if card == 'conversions':
        return svc.get_conversions(source, period) or []
    if card == 'daily':
        return svc.get_daily_dynamics(source=source) or []
    if card == 'followup':
        managers = svc.get_by_manager(source=source, period=period) or []
        rows = [m for m in managers if m.get('lost')][:10] or managers[:10]
        return rows
    if card == 'best_days':
        return svc.get_best_days(source=source, period=period) or []
    if card == 'finance':
        f = svc.get_finance(source=source, period=period) or {}
        common = {
            'total_revenue': float(f.get('total_revenue') or 0),
            'avg_deal': float(f.get('avg_deal') or 0),
            'lead_value': float(f.get('lead_value') or 0),
            'sale_value': float(f.get('sale_value') or 0),
        }
        return [
            {'_label': 'Umumiy tushum', 'value': common['total_revenue'], **common},
            {'_label': "O'rtacha chek", 'value': common['avg_deal'], **common},
            {'_label': '1 lid qiymati', 'value': common['lead_value'], **common},
            {'_label': '1 sale qiymati', 'value': common['sale_value'], **common},
        ]
    return []

def _build_chat_chart_spec(card, view_type, metric, metrics, sort_by,
                            sort_dir, limit, title, source, period):
    meta = _CARD_FIELDS.get(card)
    if not meta:
        return None, f'noma\'lum karta {card}'

    allowed_views = set(meta['views'])
    if view_type not in allowed_views:
        view_type = 'bar' if 'bar' in allowed_views else next(iter(allowed_views))

    numeric_fields = meta['numeric']
    if metric not in numeric_fields:
        metric = numeric_fields[0]

    metrics = [m for m in (metrics or []) if m in numeric_fields]
    if not metrics:
        metrics = [metric]

    rows = _chart_rows(card, source=source, period=period)
    if not rows:
        return None, 'ma\'lumot bo\'sh (bazada ushbu karta uchun yozuv yo\'q)'

    if sort_by and sort_by in numeric_fields:
        reverse = (sort_dir or 'desc').lower() != 'asc'
        rows = sorted(rows, key=lambda r: float(r.get(sort_by) or 0),
                      reverse=reverse)

    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 0
    if limit > 0:
        rows = rows[:limit]

    cat_key = meta.get('category')
    if card == 'finance':
        labels = [r.get('_label', '') for r in rows]
    elif cat_key:
        labels = [str(r.get(cat_key, '')) for r in rows]
    else:
        labels = [str(i + 1) for i in range(len(rows))]

    datasets = []
    for m in metrics:
        datasets.append({
            'label': _METRIC_LABELS.get(m, m),
            'metric': m,
            'data': [float(r.get(m) or 0) for r in rows],
        })

    return {
        'card': card,
        'card_label': meta['label'],
        'viewType': view_type,
        'metric': metric,
        'metrics': metrics,
        'labels': labels,
        'datasets': datasets,
        'title': (title or '').strip() or meta['label'],
        'sortBy': sort_by if sort_by in numeric_fields else '',
        'sortDir': 'asc' if (sort_dir or '').lower() == 'asc' else 'desc',
        'limit': limit,
    }, ''

def run_agent_analysis(source=None, period=None) -> dict:
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

    output = result['output']
    if isinstance(output, list):
        output = '\n'.join(
            block.get('text', '') if isinstance(block, dict) else str(block)
            for block in output
        )

    steps = []
    for action, _observation in result.get('intermediate_steps', []):
        steps.append(getattr(action, 'tool', 'tool'))

    logger.info('Agent tahlili tugadi: %s tool chaqirildi', len(steps))
    return {'analysis': output, 'steps': steps}

_VIEWS_FULL = [
    'barChart', 'columnChart', 'groupedBar', 'stackedBar',
    'horizontalBar', 'horizontalStackedBar', 'percentBar', 'rangeBar',
    'bulletChart',
    'lineChart', 'areaChart', 'stackedArea', 'streamGraph',
    'stepChart', 'bumpChart', 'sparkline',
    'smoothLine', 'straightLine', 'dashedLine', 'multiLine', 'pointLine',
    'smoothArea', 'percentArea', 'gradientArea',
    'pieChart', 'doughnutChart', 'halfPie', 'halfDoughnut',
    'semicircleDoughnut', 'gaugeChart', 'polarArea', 'nightingaleRose',
    'waffleChart', 'sunburst', 'marimekko',
    'histogram', 'boxPlot', 'violinPlot', 'dotPlot', 'densityChart',
    'scatterPlot', 'bubbleChart', 'connectedScatter', 'jitterScatter',
    'bubbleHeatmap', 'heatmap', 'correlationMatrix',
    'radarChart', 'spiderChart', 'filledRadar', 'multiRadar',
    'choroplethMap', 'bubbleMap', 'flowMap', 'geoHeatmap',
    'sankeyDiagram', 'funnelChart', 'waterfallChart', 'ganttChart',
    'treemap',
    'networkGraph', 'chordDiagram', 'arcDiagram',
    'kpiCard', 'metricTile', 'progressBar', 'table', 'numberCards',
    'barLine', 'areaBar', 'dualAxisBar', 'comboMultiAxis',
    'bar', 'line', 'area', 'pie', 'doughnut', 'radar', 'spiderWeb',
    'scatter', 'bubble', 'gauge', 'stacked', 'columnBar', 'stepBar',
    'waterfallBar', 'splineLine', 'steppedLine', 'kpi', 'gantt',
    'sankey',
]

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

CARD_KEYS = tuple(_CARD_FIELDS.keys())

def _card_data(card, source=None, period=None):
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
    from langchain.agents import AgentExecutor, create_tool_calling_agent
    from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

    meta = _CARD_FIELDS.get(card)
    if not meta:
        raise ValueError(f'Noma\'lum karta: {card}')

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

def _view_spec_schema(meta):
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
    meta = _CARD_FIELDS.get(card)
    if not meta:
        raise ValueError(f'Noma\'lum karta: {card}')

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
    if not isinstance(spec, dict):
        spec = dict(spec)
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
