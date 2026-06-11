import json
import logging

from apps.analytics.services import AnalyticsService

from .langchain_setup import get_llm

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 8

_SYSTEM_PROMPT = """Siz savdo bo'limining professional AI tahlilchisisiz.
Sizga `get_analytics(view=...)` tool'i berilgan — kerakli kesimni `view`
orqali oling (summary, managers, funnel, loss, comparison, change_drivers
va h.k.). Avval kerakli kesimlarni yig'ing, keyin tahlil qiling.
Trend va sabab uchun `view='comparison'` va `view='change_drivers'` dan
ham foydalaning (faqat hozirgi holat emas, o'zgarishni ham ko'rsating).

Tahlil natijasi quyidagilarni o'z ichiga olishi shart:
1. Umumiy holat — qisqa baho (va oldingi davrga nisbatan o'zgarish).
2. Zaif menejer(lar) — kim past konversiya yoki kam sotuv ko'rsatyapti.
3. Voronkaning zaif bosqichi — qayerda eng ko'p mijoz yo'qolyapti.
4. Yutqazish sabablari — agar ma'lumot bo'lsa.
5. Aniq tavsiyalar — 3-5 ta amaliy qadam.

DOMEN BILIMI: Bitrix manbasida tushum (narx) ko'pincha 0 — bu xato emas,
tizim lead oqimi va konversiyani yuritadi. Bitrix uchun tushumga urg'u
bermang; leadlar soni, konversiya, sotuvlar soniga e'tibor bering.

SIFAT: faqat tool raqamlarini ishlating (o'ylab topmang); javobdan oldin
mantiqni tekshiring (sotuv+yutqazish ≤ jami lead, foiz 0–100); namuna kichik
bo'lsa buni ochiq ayting.

Javobni o'zbek tilida, Markdown formatda, sarlavhalar bilan bering."""

_ANALYTICS_VIEWS = (
    'summary', 'managers', 'funnel', 'conversions', 'daily', 'loss',
    'followup', 'best_days', 'comparison', 'forecast', 'change_drivers',
    'sales_cycle', 'stuck_deals', 'source_compare', 'pipelines',
)

def _analytics_data(view, source=None, period=None):
    """view nomidan tegishli AnalyticsService chaqiruvini bajaradi."""
    svc = AnalyticsService()
    if view == 'summary':
        return svc.get_summary(source=source, period=period)
    if view == 'managers':
        return svc.get_by_manager(source=source, period=period)
    if view == 'funnel':
        return {'funnel': svc.get_sales_funnel(source, period),
                'conversions': svc.get_conversions(source, period)}
    if view == 'conversions':
        return svc.get_conversions(source, period)
    if view == 'daily':
        return svc.get_daily_dynamics(source=source)
    if view == 'loss':
        return svc.get_loss_reasons(source=source, period=period)
    if view == 'followup':
        managers = svc.get_by_manager(source=source, period=period)
        return [m for m in managers if m.get('lost')][:10] or managers[:10]
    if view == 'best_days':
        return svc.get_best_days(source=source, period=period)
    if view == 'comparison':
        return svc.compare_periods(source=source, period=period)
    if view == 'forecast':
        return svc.forecast(source=source)
    if view == 'change_drivers':
        return svc.explain_change(source=source, period=period)
    if view == 'sales_cycle':
        return svc.get_sales_cycle(source=source, period=period)
    if view == 'stuck_deals':
        return svc.get_stuck_deals(source=source, days_idle=14)
    if view == 'source_compare':
        return svc.get_source_compare(period=period)
    if view == 'pipelines':
        return svc.get_pipeline_breakdown(source=source, period=period)
    return {'error': f'noma\'lum view: {view}'}

_ANALYTICS_VIEW_DOC = (
    'Qaysi kesim kerakligini tanlang (bittadan, kerak bo\'lsa bir nechta marta '
    'chaqiring):\n'
    '• summary — umumiy KPI (jami/yangi lidlar, sotuv/yutqazish, konversiya, tushum, o\'rtacha chek).\n'
    '• managers — har menejer statistikasi (lidlar, call, sotuv, konversiya, tushum); kim past/yuqori.\n'
    '• funnel — voronka bosqichlari (Lid→Call→Conversation→Sotuv) va konversiyalar; zaif bosqich.\n'
    '• conversions — asosiy konversiya nisbatlari (Call→Convo, Convo→Sale, Lid→Sale).\n'
    '• daily — kunlik dinamika (har kun lid/sotuv/konversiya).\n'
    '• loss — yutqazish sabablari va soni.\n'
    '• followup — menejerlar kesimida qoldirilgan/yutqazgan lidlar.\n'
    '• best_days — hafta kunlari bo\'yicha samaradorlik.\n'
    '• comparison — joriy davr vs xuddi shu uzunlikdagi OLDINGI davr (farq + foiz). "o\'tgan oyga nisbatan", "o\'sdimi/tushdimi".\n'
    '• forecast — oy oxirigacha proyeksiya va kunlik temp. "oy oxirida qancha", "rejaga yetamizmi".\n'
    '• change_drivers — o\'zgarishga eng ko\'p hissa qo\'shgan menejerlar. "nega tushdi/o\'sdi", "kim sababchi".\n'
    '• sales_cycle — o\'rtacha sotuv sikli (necha kunda yopiladi): o\'rtacha/median/min/max.\n'
    '• stuck_deals — 14 kun harakatsiz ochiq lidlar (follow-up). "qotib qolgan", "tashlab qo\'yilgan".\n'
    '• source_compare — AmoCRM vs Bitrix yonma-yon.\n'
    '• pipelines — har pipeline (category) kesimi: leadlar, sotuv, yutqazish, konversiya.'
)

def _build_tools(source=None, period=None):
    from langchain_core.tools import StructuredTool
    from pydantic import BaseModel, Field

    def _get_analytics(view: str = 'summary') -> str:
        v = (view or '').strip().lower()
        if v not in _ANALYTICS_VIEWS:
            return (f'Xato: noma\'lum view "{view}". Mavjud: '
                    f'{", ".join(_ANALYTICS_VIEWS)}.')
        return json.dumps(_analytics_data(v, source, period),
                          ensure_ascii=False)

    class _AnalyticsArgs(BaseModel):
        view: str = Field(default='summary', description=_ANALYTICS_VIEW_DOC)

    return [
        StructuredTool.from_function(
            func=_get_analytics,
            name='get_analytics',
            description=(
                'Dashboard analitik ma\'lumotlarini qaytaradi. `view` parametri '
                'orqali kerakli kesimni tanlang (summary, managers, funnel, '
                'comparison, forecast, stuck_deals va h.k.). Bir nechta kesim '
                'kerak bo\'lsa tool\'ni har biri uchun alohida chaqiring.'
            ),
            args_schema=_AnalyticsArgs,
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

4. ⛔ **HARAKAT TOOL'INI CHAQIRMASDAN "Bajarildi/Yashirildi/Qo'shildi/
   O'zgartirildi" DEB YOZISH QAT'IY TAQIQLANGAN.** Agar foydalanuvchi
   "yashir", "ko'rsat", "qo'sh", "o'chir", "yarat", "yasa", "qil",
   "o'zgartir", "almashtir", "tozala", "qaytar", "chiqar" so'zlarini
   ishlatsa — siz AVVAL `dashboard_command` tool'ini chaqirasiz, undan
   keyin javob yozasiz. Tool chaqiruvi muvaffaqiyatli natija qaytarmaguncha
   "bajarildi" deb yozmang. Agar tool xato qaytarsa — xato matnini
   foydalanuvchiga aniq aytib bering, "bajarildi" demang.

5. **Ko'plik harakat so'rovida — har bir element uchun alohida tool
   chaqiruvi.** "Hamma kartalarni X qil" desa, 8 ta `dashboard_command`
   chaqiruvini ketma-ket bajaring (yoki `add_all_default_charts` action'ni
   bir marta chaqiring). "Bo'ldi" deb to'xtab matn yozmang — tool'larni
   to'liq bajaring.

4. **Javob o'zbek tilida, qisqa va aniq.** Markdown ishlating: sarlavhalar,
   bullet, **qalin** raqamlar. Iloji boricha jadval ishlating.

5. **Aniq raqamlar majburiy.** Tool natijasidagi sonlarni so'zsiz ayting:
   "Konversiya: **23.4%**, jami lidlar: **1 240**, sotuvlar: **290**".

══════════════════════════════════════════════════════════════════════════
MA'LUMOT TOOL'LARI (qachon chaqirish)
══════════════════════════════════════════════════════════════════════════
Asosiy tool — `get_analytics(view=...)`. Kerakli kesimni `view` orqali oling.
Bir nechta kesim kerak bo'lsa har biri uchun alohida chaqiring. view qiymatlari:

• summary — umumiy KPI (lidlar, sotuv, tushum). "umumiy holat", "kpi", "tushum".
• managers — menejerlar reytingi. "eng yaxshi/past menejer", "menejer X qancha".
• funnel — Lid→Call→Conversation→Sotuv bosqichlari. "voronka", "qayerda yo'qoladi".
• conversions — konversiya nisbatlari. "call→sale", "lid→sale".
• daily — kunlik dinamika. "kunlik tendensiya", "oxirgi 7 kun".
• loss — yutqazish sabablari. "nega sotib olmaganlar", "sabablari".
• followup — qoldirilgan/yutqazgan lidlar (menejer kesimida).
• best_days — hafta kunlari samaradorligi. "qaysi kuni yaxshi".
• comparison — joriy vs oldingi davr (farq+foiz). "o'tgan oyga nisbatan", "o'sdimi".
• forecast — oy oxirigacha proyeksiya. "oy oxirida qancha", "rejaga yetamizmi".
• change_drivers — o'zgarishga hissa qo'shgan menejerlar. "nega tushdi", "kim sababchi".
• sales_cycle — o'rtacha sotuv sikli. "qancha kunda sotamiz", "sotuv tezligi".
• stuck_deals — 14 kun harakatsiz ochiq lidlar. "qotib qolgan", "tashlab qo'yilgan".
• source_compare — AmoCRM vs Bitrix. "qaysi manba yaxshi".
• pipelines — har pipeline (category) kesimi. "qaysi voronka yaxshi".

Alohida tool'lar:
• `manager_detail` — BITTA menejer chuqur profili (ism yoki ID bilan).
   Savollar: "Aziza qanday ishlayapti", "falonchi haqida batafsil".
• `query_leads` — erkin filtrlangan lid ro'yxati (status/menejer/sana/narx).
   Savollar: "Azizning ochiq lidlari", "may oyida yutqazilganlar".

══════════════════════════════════════════════════════════════════════════
DOMEN BILIMI (muhim — xato xulosadan saqlaydi)
══════════════════════════════════════════════════════════════════════════
• **Bitrix manbasida TUSHUM (revenue/narx) ko'pincha 0** — operatorlar pul
  summasini kiritmaydi, tizim lead oqimi va konversiyani yuritadi. Shuning
  uchun Bitrix uchun "tushum 0" — bu xato yoki yomon natija EMAS. Bitrix
  bo'yicha tushumga urg'u bermang; leadlar soni, konversiya va sotuvlar
  soniga e'tibor bering. AmoCRM'da tushum ishonchli.
• Bitrix menejerlari `User` jadvalida ism bilan; ID'si "#100xxxx" ko'rinsa
  — bu ishdan bo'shagan/sinxronlanmagan xodim, ismsiz ko'rsating.

══════════════════════════════════════════════════════════════════════════
SIFAT QOIDALARI (javobdan oldin)
══════════════════════════════════════════════════════════════════════════
1. **O'z-o'zini tekshir:** raqamlar mantiqan mosmi? (sotuv + yutqazish ≤ jami
   lead; foizlar 0–100 oralig'ida; tushum manfiy emas). Mos kelmasa qayta
   tool chaqir yoki ehtiyotkor yoz.
2. **Ma'lumot yetarliligini ayt:** namuna kichik bo'lsa ("atigi 12 lead")
   yoki davr juda qisqa bo'lsa — buni ochiq ayting, soxta ishonch bermang.
3. **Faqat tool raqamlarini ishlating** — hech qachon raqam o'ylab topmang.
4. **Auditoriyaga moslang:** so'rov yuqori darajali bo'lsa (rahbar, "umumiy
   holat") — qisqa xulosa + 2-3 asosiy raqam + tavsiya. Tafsilot so'ralsa
   (menejer nomi, "batafsil") — to'liq jadval va breakdown bering.

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
     - `view_type` — 43 ta canonical tur mavjud. Eng ko'p ishlatiladigani:
       barChart, columnChart, horizontalBar, stackedBar, lineChart, areaChart,
       stackedArea, pieChart, doughnutChart, polarArea, gaugeChart, radarChart,
       scatterPlot, bubbleChart, heatmap, histogram, funnelChart, sankeyDiagram,
       waterfallChart, treemap, kpiCard, table. (Boshqa variantlar ham bor —
       bar/line/area/pie/radar/scatter/geo/flow oilalari; noto'g'ri nom bersangiz
       tizim mos turga tushiradi.)
     - `metric` — asosiy sonli maydon (managers uchun 'revenue'/'won'/'calls',
       funnel uchun 'count'/'pct' va h.k.).
     - `metrics` — bir nechta birga ko'rsatish kerak bo'lsa massiv.
     - `sort_by`, `sort_dir`, `limit`, `title` — boshqa parametrlar.

   **MUHIM — `add_custom_card` vs `set_card_view` farqi:**

   • `add_custom_card` — foydalanuvchi YANGI karta qo'shishni so'raganda.
     Belgilar: "yangi", "qo'sh", "yarat", "boshqa", "yana", "ko'rsat", "qil",
     "chiqar", "chiqarib ber", "yasab ber", "yasa", "yetishmayotgan",
     "yo'q kartalarni", "ko'rinmagan", "qo'shimcha", "qo'shimchalar".
     Misol so'rovlar:
     - "yangi karta yarat — bar chart bilan"
     - "boshqa pie chart qo'sh"
     - "menejerlarni pie chartda ko'rsat"
     - "kunlik sotuvlarni bar chart qil"
     - "yetishmayotgan chartlarni yasab ber"
     - "hamma kartalarni grafik ko'rinishda chiqarib ber"

   • `set_card_view` — foydalanuvchi MAVJUD kartani o'zgartirishni so'raganda
     va FAQAT BITTA aniq karta nomi tilga olinganda.
     Belgilar: "shu", "buni", "uni", "kartani", "o'zgartir", "almashtir",
     "qayta", "endi", "hozir". Misol so'rovlar:
     - "shu kartani line chartga o'zgartir"
     - "buni pie qil"
     - "endi shu kartani bar qil"
     - "menejerlar kartasini doughnut qil"

   ⚠️ **Shubha bo'lsa — `add_custom_card` ni tanlang.** Asl kartani
   buzmaslik xavfsizroq. `set_card_view` faqat foydalanuvchi aniq "shu",
   "buni", "kartani o'zgartir" desa va FAQAT BITTA karta haqida gapirsa.

   ⚠️ **"Hammasi", "barchasi", "har biri", "yetishmayotgan", "yo'q" so'zlari
   bilan ko'plik so'rov bo'lsa — `add_all_default_charts` action'ni
   ishlating** (8 ta default karta uchun avtomatik chart qo'shadi).

   Misollar:
   • "Loss kartasini yashir" →
     `dashboard_command(action='hide_card', card='loss')`.
   • "Menejerlar kartasini doughnut qil" (mavjud kartani o'zgartir) →
     `dashboard_command(action='set_card_view', card='managers',
     view_type='doughnut', metric='revenue', limit=5)`.
   • "Yangi karta — menejerlarni pie chartda ko'rsat" →
     `dashboard_command(action='add_custom_card', card='managers',
     view_type='pieChart', metric='revenue', limit=10,
     title='Menejerlar ulushi')`.
   • "Shu kartani line chartga o'zgartir" →
     `dashboard_command(action='set_card_view', card='daily',
     view_type='lineChart', metric='sales')`.
   • "Kunlik sotuv va lidlarni bar chart qil" (yangi karta) →
     `dashboard_command(action='add_custom_card', card='daily',
     view_type='barChart', metric='leads',
     metrics=['leads', 'sales'], title='Kunlik dinamika')`.
   • "Yetishmayotgan chartlarni hammasini yasab ber" / "Hamma kartalarni
     grafik ko'rinishda chiqar" →
     `dashboard_command(action='add_all_default_charts')`.
   • "Hamma kartalarni tozala" →
     `dashboard_command(action='remove_all_custom')`.
   • "Barcha kartalarni qaytar" →
     `dashboard_command(action='show_all_cards')`.

   **FILTER (period/source) BOSHQARUVI**

   `set_period` — dashboard vaqt oralig'ini o'zgartiradi. Parametrlar:
     - `period` — `day | week | month | all` (yoki bo'sh, `all` deb hisoblanadi)
     - YOKI `date_from` + `date_to` — `YYYY-MM-DD` formatida oraliq

   **Sana parsing qoidalari** (BUGUNGI SANA system prompt boshida ko'rsatilgan):
     - "haftalik" / "shu hafta" → `period='week'`
     - "oylik" / "shu oy" / "bu oy" → `period='month'`
     - "kunlik" / "bugungi" / "bugun" → `period='day'`
     - "barcha vaqt" / "hammasi" / "filter bekor" → `period='all'`
     - "1-30 may" → `date_from='YYYY-05-01', date_to='YYYY-05-30'`
       (YYYY — bugungi yil; agar may o'tib ketgan bo'lsa va kontekstdan o'tgan
       yil aniq bo'lsa, o'tgan yilni ishlating)
     - "iyul oyi" → `date_from='YYYY-07-01', date_to='YYYY-07-31'`
     - "2026 yil 5 fevral" → `date_from='2026-02-05', date_to='2026-02-05'`
     - "oxirgi 3 oy" → `date_from=<bugungi sanadan 90 kun oldin>,
       date_to=<bugun>`

   `set_source` — dashboard CRM manbai filtri:
     - `source_value='amocrm'` — faqat AmoCRM lidlari
     - `source_value='bitrix'` — faqat Bitrix lidlari
     - `source_value='all'` yoki bo'sh — barcha manbalar

   Misollar:
   • "Haftalik statistikalarni ko'rsat" →
     `dashboard_command(action='set_period', period='week')`.
   • "Oylik dinamikani chiqar" →
     `dashboard_command(action='set_period', period='month')`.
   • "1-30 maydagi statistikalarni ko'rsat" →
     `dashboard_command(action='set_period',
     date_from='YYYY-05-01', date_to='YYYY-05-30')`.
   • "Faqat AmoCRM ma'lumotlarini ko'rsat" →
     `dashboard_command(action='set_source', source_value='amocrm')`.
   • "Filterlarni bekor qil" →
     `dashboard_command(action='set_period', period='all')`.

   ⚠️ Filter o'zgargandan keyin dashboard avtomatik yangilanadi. Foydalanuvchi
   yangi davr uchun aniq tahlil so'rasa — qisqa tasdiq yozing
   ("✅ Filter haftalikga o'rnatildi"), aniq raqamlarni qaytadan tool orqali
   olishingiz shart emas (bu eski period bo'yicha bo'lardi).

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
                    source=None, period=None, is_voice: bool = False,
                    callbacks=None) -> dict:
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
                                 sort_dir='desc', limit=0, title='',
                                 period='', date_from='', date_to='',
                                 source_value='') -> str:
        action = (action or '').strip()
        valid_actions = {
            'show_card', 'hide_card', 'set_card_view',
            'refresh_dashboard', 'open_ai_panel',
            'show_all_cards', 'hide_all_cards',
            'add_custom_card', 'remove_custom_card', 'remove_all_custom',
            'add_all_default_charts',
            'set_period', 'set_source',
        }
        if action not in valid_actions:
            return (f'Xato: action "{action}" noma\'lum. '
                    f'Mavjud: {", ".join(sorted(valid_actions))}.')

        if action == 'set_period':
            period_val, err = _normalize_period(period, date_from, date_to)
            if err:
                return f'Xato: {err}'
            commands.append({'action': 'set_period',
                             'period': period_val})
            return (f'Dashboard filter o\'rnatildi: period={period_val}. '
                    'Dashboard avtomatik yangilanadi.')

        if action == 'set_source':
            allowed = {'', 'amocrm', 'bitrix'}
            sv = (source_value or '').strip().lower()
            if sv == 'all':
                sv = ''
            if sv not in allowed:
                return (f'Xato: source "{source_value}" noto\'g\'ri. '
                        f'Mavjud: amocrm, bitrix, all (yoki bo\'sh).')
            commands.append({'action': 'set_source', 'source': sv})
            return (f'Dashboard manbai o\'rnatildi: source="{sv or "all"}". '
                    'Dashboard avtomatik yangilanadi.')

        if action == 'add_all_default_charts':
            added_keys = []
            skipped = []
            for c_key in _DEFAULT_CHART_PRESETS:
                preset = _DEFAULT_CHART_PRESETS[c_key]
                spec, err = _build_chat_chart_spec(
                    card=c_key,
                    view_type=preset['view_type'],
                    metric=preset['metric'],
                    metrics=list(preset['metrics']),
                    sort_by=preset.get('sort_by', ''),
                    sort_dir=preset.get('sort_dir', 'desc'),
                    limit=int(preset.get('limit', 0)),
                    title=preset.get('title', ''),
                    source=source, period=period,
                )
                if err:
                    logger.warning('add_all_default_charts skip %s: %s',
                                   c_key, err)
                    skipped.append(f'{c_key} ({err})')
                    continue
                commands.append({'action': 'add_custom_card',
                                 'card': c_key, 'spec': spec})
                added_keys.append(c_key)
            msg = (f'Dashboard\'ga {len(added_keys)} ta default chart '
                   f'qo\'shildi: {", ".join(added_keys) or "—"}.')
            if skipped:
                msg += f' O\'tkazib yuborildi: {"; ".join(skipped)}.'
            return msg

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
            'add_custom_card | remove_custom_card | remove_all_custom | '
            'add_all_default_charts | set_period | set_source.'))
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
        period: str = Field(default='', description=(
            'set_period uchun: day | week | month | all (yoki bo\'sh).'))
        date_from: str = Field(default='', description=(
            'set_period uchun oraliq boshlanishi (YYYY-MM-DD).'))
        date_to: str = Field(default='', description=(
            'set_period uchun oraliq tugashi (YYYY-MM-DD).'))
        source_value: str = Field(default='', description=(
            'set_source uchun: amocrm | bitrix | all (yoki bo\'sh).'))

    detail_svc = AnalyticsService()

    def _resolve_manager(text):
        """Ism yoki ID matnidan menejer amocrm_id ni topadi."""
        from apps.amocrm.models import User as AmoCRMUser
        t = (text or '').strip()
        if not t:
            return None
        if t.lstrip('#').isdigit():
            return int(t.lstrip('#'))
        match = (AmoCRMUser.objects.filter(name__icontains=t)
                 .values_list('amocrm_id', flat=True).first())
        return match

    def _manager_detail_tool(manager: str = '') -> str:
        mid = _resolve_manager(manager)
        if mid is None:
            return (f'Xato: "{manager}" menejer topilmadi. To\'liq ism yoki ID '
                    'bering, yoki get_analytics(view=\'managers\') bilan ro\'yxatni oling.')
        return json.dumps(
            detail_svc.get_manager_detail(mid, source=source, period=period),
            ensure_ascii=False)

    def _query_leads_tool(status: str = '', manager: str = '',
                          date_from: str = '', date_to: str = '',
                          min_price: float = 0, limit: int = 20) -> str:
        mid = _resolve_manager(manager) if manager else None
        if manager and mid is None:
            return f'Xato: "{manager}" menejer topilmadi.'
        return json.dumps(detail_svc.query_leads(
            source=source, manager_id=mid,
            status=(status or '').strip().lower() or None,
            date_from=date_from or None, date_to=date_to or None,
            min_price=min_price or None, limit=limit,
        ), ensure_ascii=False)

    class _ManagerDetailArgs(BaseModel):
        manager: str = Field(description=(
            'Menejer to\'liq ismi (masalan "Aziza Xayitova") yoki ID raqami.'))

    class _QueryLeadsArgs(BaseModel):
        status: str = Field(default='', description=(
            'Filtr: won (sotilgan) | lost (yutqazilgan) | open (ochiq) '
            'yoki bo\'sh (hammasi).'))
        manager: str = Field(default='', description=(
            'Menejer ismi yoki ID (ixtiyoriy).'))
        date_from: str = Field(default='', description='YYYY-MM-DD (ixtiyoriy).')
        date_to: str = Field(default='', description='YYYY-MM-DD (ixtiyoriy).')
        min_price: float = Field(default=0, description=(
            'Minimal narx filtri (ixtiyoriy).'))
        limit: int = Field(default=20, description=(
            'Qaytariladigan qatorlar soni (maks 100).'))

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
        StructuredTool.from_function(
            func=_manager_detail_tool,
            name='manager_detail',
            description=(
                'BITTA menejerning chuqur profili: KPI, kunlik trend va '
                'yutqazish sabablari. "Aziza qanday ishlayapti", "falonchi '
                'menejer haqida batafsil" savollari uchun. manager = ism yoki ID.'
            ),
            args_schema=_ManagerDetailArgs,
        ),
        StructuredTool.from_function(
            func=_query_leads_tool,
            name='query_leads',
            description=(
                'Erkin filtrlangan lid ro\'yxati: status/menejer/sana/narx '
                'bo\'yicha. Tayyor tool qamramagan aniq savollar uchun, masalan '
                '"Azizning ochiq lidlari", "may oyidagi yutqazilgan bitimlar".'
            ),
            args_schema=_QueryLeadsArgs,
        ),
    ]

    tools = base_tools + extra_tools

    mem = memory_mod.build_memory(manager_id,
                                  input_key='input', output_key='output')
    history_msgs = list(mem.chat_memory.messages)

    # Uzoq xotira: oyna tashqarisidagi eski suhbat xulosasini old qo'shamiz
    try:
        from langchain_core.messages import SystemMessage
        preface = memory_mod.build_summary_preface(manager_id)
        if preface:
            history_msgs = [SystemMessage(content=(
                'Oldingi suhbat xulosasi (kontekst uchun): ' + preface
            ))] + history_msgs
    except Exception as exc:
        logger.warning('Summary preface ulanmadi: %s', exc)

    from datetime import date
    today = date.today()
    weekday_uz = ['Dushanba', 'Seshanba', 'Chorshanba', 'Payshanba',
                  'Juma', 'Shanba', 'Yakshanba'][today.weekday()]
    month_uz = ['', 'Yanvar', 'Fevral', 'Mart', 'Aprel', 'May', 'Iyun',
                'Iyul', 'Avgust', 'Sentyabr', 'Oktyabr', 'Noyabr',
                'Dekabr'][today.month]
    date_header = (
        f'\n══════════════════════════════════════════════════════════════════════════\n'
        f'BUGUNGI SANA: {today.isoformat()} ({weekday_uz}, '
        f'{today.day}-{month_uz} {today.year}-yil).\n'
        f'Joriy yil: {today.year}. Joriy oy: {today.month} ({month_uz}).\n'
        f'Sana parsingda shu yilni ishlating, agar foydalanuvchi aniq '
        f'boshqa yilni aytmasa.\n'
        f'══════════════════════════════════════════════════════════════════════════\n'
    )
    system_prompt = (_CHAT_SYSTEM_PROMPT + date_header +
                     (_VOICE_MODE_SUFFIX if is_voice else ''))
    # Anthropic prompt caching: ulkan (~280 qatorli) system prompt'ni keshlaymiz,
    # shunda agent loop'ning har iteratsiyasida u qayta o'qilmaydi (tezroq + arzon).
    from langchain_core.messages import SystemMessage
    system_msg = SystemMessage(content=[{
        'type': 'text',
        'text': system_prompt,
        'cache_control': {'type': 'ephemeral'},
    }])
    prompt = ChatPromptTemplate.from_messages([
        system_msg,
        MessagesPlaceholder('history'),
        ('human', '{input}'),
        MessagesPlaceholder('agent_scratchpad'),
    ])

    # temperature=0 — raqamli/tool ishida deterministik va ishonchli javob.
    # callbacks berilsa (SSE stream) — streaming LLM ishlatamiz, shunda yakuniy
    # javob token-token oqib chiqadi (on_llm_new_token).
    llm = get_llm(temperature=0, streaming=bool(callbacks))
    agent = create_tool_calling_agent(llm, tools, prompt)
    executor = AgentExecutor(
        agent=agent, tools=tools, max_iterations=MAX_ITERATIONS,
        handle_parsing_errors=True, return_intermediate_steps=True,
        verbose=False,
    )

    invoke_cfg = {'callbacks': callbacks} if callbacks else None
    result = executor.invoke({'input': question, 'history': history_msgs},
                             config=invoke_cfg)

    output = result['output']
    if isinstance(output, list):
        output = '\n'.join(
            b.get('text', '') if isinstance(b, dict) else str(b)
            for b in output
        )

    steps = [getattr(a, 'tool', 'tool')
             for a, _ in result.get('intermediate_steps', [])]

    if _is_command_intent(question) and not commands:
        logger.warning(
            'Chat agent: foydalanuvchi harakat so\'radi lekin '
            'dashboard_command chaqirilmadi. Retry qilinmoqda. q=%r',
            question[:120])
        retry_prompt = (
            f'{question}\n\n'
            '[TIZIM ESLATMASI: Oldingi javobingizda dashboard_command '
            'tool\'ini chaqirmadingiz. Bu so\'rov harakat talab qiladi. '
            'Endi tool\'ni chaqiring va to\'g\'ri bajarishga harakat qiling.]'
        )
        try:
            result2 = executor.invoke({'input': retry_prompt,
                                        'history': history_msgs})
            output2 = result2['output']
            if isinstance(output2, list):
                output2 = '\n'.join(
                    b.get('text', '') if isinstance(b, dict) else str(b)
                    for b in output2
                )
            steps2 = [getattr(a, 'tool', 'tool')
                      for a, _ in result2.get('intermediate_steps', [])]
            steps = steps + steps2
            if commands:
                output = output2 or output
        except Exception as exc:
            logger.warning('Retry xato: %s', exc)

    message_id = None
    try:
        message_id = memory_mod.save_turn(manager_id, question, output)
    except Exception as exc:
        logger.warning('Memory save xato: %s', exc)

    logger.info('Chat agent: manager=%s, tools=%s, charts=%d, commands=%d',
                manager_id, steps, len(chart_specs), len(commands))
    return {'answer': output, 'sources': [], 'used_rag': False,
            'steps': steps, 'charts': chart_specs, 'commands': commands,
            'message_id': message_id}

_ACTION_TRIGGERS = (
    'yashir', 'ko\'rsat', 'qo\'sh', 'o\'chir', 'yarat', 'yasa', 'yasab',
    'qil ', 'qilib', 'qiling', 'o\'zgartir', 'almashtir', 'tozala',
    'qaytar', 'chiqar', 'chiqarib', 'yetishmayotgan', 'olib tashla',
    'pie qil', 'bar qil', 'line qil', 'doughnut qil', 'jadval qil',
    'grafik qil', 'chart qil',
    'haftalik', 'oylik', 'kunlik', 'oraliq', 'maydagi', 'iyundagi',
    'iyuldagi', 'fevraldagi', 'martdagi', 'apreldagi', 'avgustdagi',
    'sentyabrdagi', 'oktyabrdagi', 'noyabrdagi', 'dekabrdagi',
    'yanvardagi', 'amocrm', 'bitrix', 'filter', 'oraliq qil',
    'shu hafta', 'shu oy', 'bugun', 'kechagi',
)

def _is_action_intent(text: str) -> bool:
    if not text:
        return False
    low = text.lower()
    return any(trigger in low for trigger in _ACTION_TRIGGERS)

# Retry uchun TOR ro'yxat: faqat dashboard'ni o'zgartiruvchi (chart/karta/filter)
# so'rovlar. Umumiy analitika fe'llari ("ko'rsat", "chiqar", "amocrm", "bitrix"...)
# bu yerda YO'Q — chunki ular oddiy statistika savollarida ham uchraydi va butun
# agentni keraksiz 2-marta ishlatib, javobni 2x sekinlashtirardi.
_COMMAND_RETRY_TRIGGERS = (
    # grafik / karta chizish
    'grafik', 'chart', 'diagramma', 'chiz',
    'pie qil', 'bar qil', 'line qil', 'doughnut qil', 'jadval qil',
    'grafik qil', 'chart qil', 'pie chart', 'bar chart', 'line chart',
    'karta qo\'sh', 'kartani', 'kartalarni', 'karta yarat', 'karta yasa',
    'yetishmayotgan', 'olib tashla', 'kartani yashir', 'kartani ko\'rsat',
    # filter (set_period / set_source)
    'haftalik', 'oylik', 'kunlik', 'oraliq', 'filter',
    'maydagi', 'iyundagi', 'iyuldagi', 'fevraldagi', 'martdagi',
    'apreldagi', 'avgustdagi', 'sentyabrdagi', 'oktyabrdagi',
    'noyabrdagi', 'dekabrdagi', 'yanvardagi',
    'shu hafta', 'shu oy',
)

def _is_command_intent(text: str) -> bool:
    """Faqat dashboard buyrug'i (chart/karta/filter) talab qiluvchi so'rovmi.

    Bu retry qarori uchun ishlatiladi — umumiy analitika savollarini
    qamramaydi, shu sabab keraksiz ikkilamchi agent run bo'lmaydi.
    """
    if not text:
        return False
    low = text.lower()
    return any(trigger in low for trigger in _COMMAND_RETRY_TRIGGERS)

_PERIOD_KEYWORDS = {
    'all': 'all', 'barcha': 'all', 'hammasi': 'all', 'jami': 'all',
    'day': 'day', 'kun': 'day', 'kunlik': 'day', 'bugun': 'day',
    'week': 'week', 'hafta': 'week', 'haftalik': 'week',
    'month': 'month', 'oy': 'month', 'oylik': 'month',
}

def _normalize_period(period_raw, date_from, date_to):
    """
    Returns (canonical_period, error_or_None).
    Canonical formats: 'all' (cleared) | 'day' | 'week' | 'month'
                     | 'range:YYYY-MM-DD:YYYY-MM-DD'
    """
    import re
    from datetime import datetime

    p = (period_raw or '').strip().lower()
    df = (date_from or '').strip()
    dt = (date_to or '').strip()

    if df and dt:
        iso_re = re.compile(r'^\d{4}-\d{2}-\d{2}$')
        if not iso_re.match(df) or not iso_re.match(dt):
            return None, ('date_from/date_to formatda emas. '
                          'YYYY-MM-DD bo\'lishi kerak.')
        try:
            d1 = datetime.strptime(df, '%Y-%m-%d').date()
            d2 = datetime.strptime(dt, '%Y-%m-%d').date()
        except ValueError as exc:
            return None, f'sana xato: {exc}'
        if d1 > d2:
            d1, d2 = d2, d1
        return f'range:{d1.isoformat()}:{d2.isoformat()}', None

    if p.startswith('range:'):
        parts = p.split(':')
        if len(parts) == 3:
            return _normalize_period('', parts[1], parts[2])
        return None, 'range formati: range:YYYY-MM-DD:YYYY-MM-DD'

    canonical = _PERIOD_KEYWORDS.get(p)
    if canonical:
        return canonical, None

    if not p and not df and not dt:
        return 'all', None

    return None, (f'period "{period_raw}" tushunarsiz. '
                  'Mavjud: day, week, month, all yoki '
                  'date_from + date_to (YYYY-MM-DD).')

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

    agent = create_tool_calling_agent(get_llm(temperature=0), tools, prompt)
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

_DEFAULT_CHART_PRESETS = {
    'funnel': {
        'view_type': 'funnelChart', 'metric': 'count',
        'metrics': ['count'], 'sort_by': '', 'sort_dir': 'desc',
        'limit': 0, 'title': 'Savdo voronkasi — grafik',
    },
    'managers': {
        'view_type': 'barChart', 'metric': 'revenue',
        'metrics': ['revenue', 'won'], 'sort_by': 'revenue', 'sort_dir': 'desc',
        'limit': 10, 'title': 'Menejerlar reytingi — grafik',
    },
    'conversions': {
        'view_type': 'doughnutChart', 'metric': 'pct',
        'metrics': ['pct'], 'sort_by': '', 'sort_dir': 'desc',
        'limit': 0, 'title': 'Asosiy konversiyalar — grafik',
    },
    'daily': {
        'view_type': 'lineChart', 'metric': 'sales',
        'metrics': ['leads', 'sales'], 'sort_by': '', 'sort_dir': 'asc',
        'limit': 0, 'title': 'Kunlik dinamika — grafik',
    },
    'loss': {
        'view_type': 'horizontalBar', 'metric': 'count',
        'metrics': ['count'], 'sort_by': 'count', 'sort_dir': 'desc',
        'limit': 10, 'title': 'Yutqazish sabablari — grafik',
    },
    'finance': {
        'view_type': 'barChart', 'metric': 'value',
        'metrics': ['value'], 'sort_by': '', 'sort_dir': 'desc',
        'limit': 0, 'title': "Moliy ko'rsatkichlar — grafik",
    },
    'followup': {
        'view_type': 'barChart', 'metric': 'lost',
        'metrics': ['lost', 'won'], 'sort_by': 'lost', 'sort_dir': 'desc',
        'limit': 10, 'title': 'Qoldirilgan lidlar — grafik',
    },
    'best_days': {
        'view_type': 'barChart', 'metric': 'won',
        'metrics': ['leads', 'won'], 'sort_by': '', 'sort_dir': 'desc',
        'limit': 0, 'title': 'Eng yaxshi kunlar — grafik',
    },
}

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
    meta = _CARD_FIELDS.get(card)
    if not meta:
        raise ValueError(f'Noma\'lum karta: {card}')

    # Ma'lumotni kod orqali to'g'ridan-to'g'ri olamiz — agent tool tanlashi
    # shart emas. Bu tezroq (bitta LLM chaqiruvi) va ishonchliroq (deterministik
    # ma'lumot), 'finance' kartasini ham qamraydi.
    data = _card_data(card, source=source, period=period)

    system_text = (
        f'Siz savdo bo\'limining AI tahlilchisisiz. Quyida "{meta["label"]}" '
        'kartasi ma\'lumoti (JSON) berilgan. Faqat shu raqamlardan foydalanib '
        'QISQA tahlil bering: 1) holatga baho, 2) asosiy muammo yoki kuchli '
        'tomon, 3) 2-3 ta aniq amaliy tavsiya. Javob o\'zbek tilida, Markdown '
        'formatda, 130 so\'zdan oshmasin.\n\nMA\'LUMOT:\n'
        + json.dumps(data, ensure_ascii=False)
    )

    output = get_llm(temperature=0).invoke(system_text).content
    if isinstance(output, list):
        output = '\n'.join(
            b.get('text', '') if isinstance(b, dict) else str(b)
            for b in output
        )
    logger.info('Karta tahlili tugadi: card=%s (tool-siz)', card)
    return {'analysis': output, 'steps': [card]}

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
