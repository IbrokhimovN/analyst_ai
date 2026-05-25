# 🏗️ Analyst AI — Loyiha Arxitekturasi

Bu hujjat butun loyihani **eng oddiy tilda** tushuntiradi — har bir papka, har bir muhim fayl, va har bir kutubxona nima ish qiladi.

---

## 🧒 Eng avval — bu loyiha umuman nima?

Tasavvur qiling, sizning kompaniyangizda **savdo bo'limi** bor. Mijozlar bilan ishlovchi sotuvchilarni **menejer** deyishadi. Ular har kuni mijozlarni yozib boradi, ular bilan gaplashadi, sotuv qiladi. Ularning ish jarayoni **CRM** (Customer Relationship Management) tizimida saqlanadi — bizning loyihada bu **AmoCRM** yoki **Bitrix24**.

**Bizning loyiha — bu kompaniya rahbari uchun "ko'zoynak":**
- AmoCRM'dan ma'lumotlarni o'qib oladi
- Yaxshi chiroyli sahifa (dashboard) qilib ko'rsatadi
- Chart va graflarni chizadi
- Pastda **AI yordamchi** bor — gaplashish, savol berish, "menejerlarni grafik qilib ko'rsat" deyish mumkin
- AI hatto dashboard'ni ham boshqaradi — "loss kartasini yashir" deysiz, yashiradi

---

## 📁 Loyiha tuzilishi (umumiy)

```
/var/www/analyst_ai/
├── apps/              ← Bizning Django "ilovalar" (har biri alohida vazifa)
│   ├── ai_analyst/    ← 🤖 AI yordamchi — Claude, RAG, Agent
│   ├── amocrm/        ← 📞 AmoCRM bilan bog'lanish
│   ├── analytics/     ← 📊 Statistika hisoblash
│   ├── api/           ← 🔌 REST API — frontend'ga ma'lumot uzatish
│   ├── crm/           ← 🔄 CRM "adapter" — AmoCRM va Bitrix bir xil ishlasin uchun
│   └── dashboard/     ← 🖥️ HTML sahifalar (kelib ko'rinadigan qism)
├── config/            ← ⚙️ Django sozlamalari (settings.py va shu kabilar)
├── static/            ← 🎨 CSS va JavaScript fayllar
├── templates/         ← 🧱 HTML shablonlar
├── media/             ← 📂 Foydalanuvchi yuklagan fayllar (PDF, Excel)
├── manage.py          ← Django boshqaruv skripti
├── requirements.txt   ← Qaysi Python paketlar kerakligi
├── .env               ← Maxfiy sozlamalar (parol, API kalit)
└── docker-compose.yml ← Docker konfiguratsiya
```

---

## 🎯 Asosiy texnologiyalar (eng muhimlari)

### Backend (server tarafi)
| Texnologiya | Vazifasi | Qaerda |
|---|---|---|
| **Django 5.0.6** | Asosiy web framework — sahifalar, URL'lar, baza | Hamma yerda |
| **Django REST Framework** | Frontend'ga JSON ma'lumot beradigan API | `apps/api/` |
| **PostgreSQL** | Ma'lumotlar bazasi (lid, mijoz, statistika) | `psycopg2-binary` orqali |
| **Redis** | Tez kesh + Celery uchun navbat | Celery va cache uchun |
| **Celery** | Fonda ishlaydigan vazifalar (sinxronlash) | `apps/amocrm/tasks.py` |
| **Channels** | WebSocket — real vaqt aloqasi | `apps/ai_analyst/consumers.py` |
| **LangChain** | AI bilan ishlash uchun "qatlam" | `apps/ai_analyst/` |
| **Anthropic Claude** | AI miyya — savol-javob beradi | API key bilan |
| **FAISS** | Vektor ombor — hujjat bo'laklarini saqlash | RAG uchun |

### Frontend (brauzer tarafi)
| Texnologiya | Vazifasi | Qaerda |
|---|---|---|
| **Vanilla JavaScript** | Brauzer mantiqi (React/Vue ishlatilmaydi) | `static/js/` |
| **Chart.js + 4 plugin** | Grafik chizish (43 turdagi chart) | `static/js/chart_render.js` |
| **Marked.js** | Markdown matnni HTML qilish | AI javoblari uchun |
| **Shadow DOM** | AI chat widget'ni boshqa CSS'dan izolatsiya | `ai_chat_widget.js` |
| **Web Speech API** | Brauzer mikrofonidan ovoz tinglash | Voice chat |

---

## 📦 Endi har bir `apps/` ilovani batafsil

---

### 🤖 `apps/ai_analyst/` — AI yordamchining "miyyasi"

Bu eng katta va eng murakkab papka. Bu yerda AI Claude bilan ishlash, hujjatlardan o'qish, suhbat tarixini saqlash — hammasi shu yerda.

**Asosiy fayllar:**

| Fayl | Nima qiladi |
|---|---|
| **`langchain_setup.py`** | Claude AI'ni "yoqadi" — LLM va embedding modelni tayyorlaydi. Bu zavod direktori — boshqalar shu yerdan tayyor AI obyektini olishadi. |
| **`agent.py`** | **Agent** — AI'ga "asboblar" (tools) beradi. AI o'zi qaror qiladi: "menejerlar haqida bilish kerakmi? Unda `_managers_tool` ni chaqiraman". Foydalanuvchi "Loss kartasini yashir" desa — `dashboard_command` tool'ini chaqiradi. Jami **2 ta StructuredTool**: `make_chart` (grafik chizish) va `dashboard_command` (dashboard boshqarish). |
| **`rag.py`** | **RAG** — *Retrieval-Augmented Generation*. PDF/Excel yuklab qo'ysangiz, AI shu hujjatlardan ma'lumot olib javob beradi. Avval hujjatni bo'laklarga ajratadi → embedding (raqamli vektor) qiladi → FAISS'ga saqlaydi → savolda kerakli bo'lakni topadi → Claude'ga uzatadi. |
| **`memory.py`** | Suhbat tarixi. Har bir menejer uchun alohida — "siz oxirgi marta nima so'ragan edingiz" eslab qoladi. `ConversationBufferWindowMemory` — oxirgi N ta savol-javob. |
| **`loaders.py`** | Fayl o'qish — PDF (`pypdf`), Excel/CSV (`pandas`). Faylni matn bo'laklariga ajratadi. |
| **`models.py`** | Baza jadvallari: `KnowledgeDocument` (yuklangan fayllar) va `ChatMessage` (har bir savol-javob). |
| **`services.py`** | Eski oddiy AI service — Claude'ni to'g'ridan-to'g'ri chaqirish (LangChain'siz). Ba'zi joylarda hali ishlatilmoqda. |
| **`prompts.py`** | AI'ga qaratilgan "ko'rsatma matnlari" (system prompts) — "siz savdo tahlilchisisiz" kabi. |
| **`consumers.py`** | WebSocket — chat real vaqtda streaming bo'lishi uchun. |
| **`routing.py`** | Channels'ning WebSocket URL'lari. |

**Kutubxonalar:**
- `langchain` + `langchain-anthropic` + `langchain-community` — AI bilan ishlash uchun asosiy
- `anthropic` — to'g'ridan-to'g'ri Claude API (LangChain'siz `services.py`'da)
- `faiss-cpu` — vektor ombor (RAG uchun)
- `fastembed` — matnni vektorga aylantiruvchi tezkor model
- `pypdf` — PDF o'qish
- `pandas` + `openpyxl` — Excel o'qish
- `langchain-text-splitters` — matnni bo'laklarga ajratish

---

### 📞 `apps/amocrm/` — AmoCRM bilan bog'lanish

AmoCRM bizning asosiy CRM. Bu papka uning bilan gaplashadi: OAuth orqali bog'lanadi, har 15 daqiqada yangi ma'lumotlarni tortib oladi.

**Asosiy fayllar:**

| Fayl | Nima qiladi |
|---|---|
| **`models.py`** | Baza jadvallari — `Lead` (lid/sotuv), `Contact` (mijoz), `Pipeline` (sotuv yo'nalishi), `PipelineStatus` (bosqichlar), `User` (menejerlar), `AmoCRMToken` (kirish kaliti). |
| **`services.py`** | `AmoCRMService` — AmoCRM API bilan gaplashish (token olish, yangilash, so'rovlar yuborish). |
| **`sync.py`** | Sinxronlash mantiqi — AmoCRM'dan ma'lumot tortib bazaga yozish. **Yagona joy** — qo'lda ham, Celery ham shu funksiyalarni chaqiradi. |
| **`tasks.py`** | Celery vazifalari — `sync_pipelines`, `sync_users`, `sync_leads`. Har 15 daqiqada avtomatik ishlaydi. |
| **`views.py`** | OAuth callback ko'rinishi — AmoCRM'dan qaytgan kalitni qabul qilish. |
| **`urls.py`** | `/amocrm/oauth/callback/` kabi URL'lar. |
| **`webhooks.py`** | AmoCRM yangi o'zgarish bo'lganida real vaqtda xabar yuboradi — shu yerda qabul qilinadi. |
| **`management/`** | `python manage.py sync_amocrm` kabi qo'lda buyruqlar. |

**Kutubxonalar:**
- `requests` — HTTP so'rovlar (AmoCRM API'ga)
- `celery` + `redis` — fon vazifalar

---

### 📊 `apps/analytics/` — Statistika hisoblash

AmoCRM ma'lumotlarini "xom" holda saqlaydi (lid, mijoz). Bu papka ulardan **mazmunli statistika** chiqaradi: bugun nechta lid keldi, sotuv summasi qancha, konversiya foizi qanday.

**Asosiy fayllar:**

| Fayl | Nima qiladi |
|---|---|
| **`services.py`** | `AnalyticsService` — barcha hisoblash mantiqi. Methodlar: `get_summary` (umumiy), `get_funnel` (voronka), `get_by_manager` (menejer bo'yicha), `get_leads_trend` (vaqt bo'yicha trend). Davr (kunlik/haftalik/oylik/range) qo'llab-quvvatlaydi. |
| **`models.py`** | `DailyStat` — kunlik kesh statistika. `WeeklyReport` — AI yozgan haftalik hisobot. |
| **`serializers.py`** | DRF serializerlar — statistikalarni JSON ga aylantirish. |

**Kutubxonalar:**
- `django.db.models` — `Sum`, `Count`, `Avg` agregatsiya
- `python-dateutil` — sana hisoblari

---

### 🔌 `apps/api/` — REST API (frontend bilan aloqa)

Frontend (brauzer) backend'dan ma'lumot olishi uchun **API endpoint'lar** kerak. Bu yerda hammasi.

**Tuzilishi:**

```
apps/api/v1/
├── urls.py              ← Barcha URL'lar
├── views/
│   ├── leads.py         ← Lid va kontakt CRUD
│   ├── analytics.py     ← Statistika endpointlar
│   ├── dashboard_data.py← Dashboard uchun barcha ma'lumot bir joyda
│   └── ai.py            ← AI chat, RAG yuklash, agent
└── serializers/         ← JSON formatga aylantirish
```

**Asosiy URL'lar:**

| URL | Vazifasi |
|---|---|
| `GET /api/v1/leads/` | Barcha lidlar ro'yxati |
| `GET /api/v1/analytics/summary/` | Umumiy statistika |
| `GET /api/v1/analytics/funnel/` | Sotuv voronkasi |
| `GET /api/v1/dashboard/data/` | Dashboard'ning butun ma'lumoti (AJAX uchun) |
| `POST /api/v1/ai/chat/` | AI chatga savol berish (kompleks oqim — RAG/Agent/Memory) |
| `POST /api/v1/ai/rag/upload/` | PDF/Excel yuklash |
| `GET /api/v1/ai/card/render/` | Bitta karta uchun ma'lumot |
| `POST /api/v1/ai/agent/analyze/` | Agent — chuqur tahlil qilish |
| `POST /api/v1/auth/token/` | JWT token olish |
| `GET /api/v1/docs/` | Swagger UI (API hujjatlari) |

**Kutubxonalar:**
- `djangorestframework` — API framework
- `djangorestframework-simplejwt` — JWT autentifikatsiya
- `django-cors-headers` — CORS sozlamalari
- `drf-spectacular` — Swagger/OpenAPI hujjatlar avto-yaratish
- `django-filter` — querystring filtrlash (`?status=won&period=week`)

---

### 🔄 `apps/crm/` — CRM Adapter (AmoCRM + Bitrix uchun bir interfeys)

Loyiha ham AmoCRM, ham Bitrix24'ni qo'llab-quvvatlaydi. Lekin har biri o'z API'sini ishlatadi. Bu papka — "adapter" pattern: ikkalasi uchun **bir xil** interfeys yaratadi.

**Asosiy fayllar:**

| Fayl | Nima qiladi |
|---|---|
| **`base.py`** | `BaseCRMAdapter` — abstract class (qoidalar to'plami). Hamma adapter shu metodlarni amalga oshirishi shart. |
| **`factory.py`** | `get_crm_adapter('amocrm')` — sozlamaga qarab kerakli adapterni tanlab beradi. Foydalanuvchi `BaseCRMAdapter` interfeysidan foydalanadi, ostidan qaysi CRM ishlayotganini bilmaydi. |
| **`adapters/amocrm.py`** | AmoCRMAdapter — AmoCRM uchun aniq amalga oshirilgan |
| **`adapters/bitrix.py`** | Bitrix24Adapter — Bitrix uchun |

**Foyda:** Kelajakda yana bir CRM (masalan, Salesforce) qo'shilsa — faqat yangi adapter yozish kifoya, qolgan kodga tegmaslik kerak.

---

### 🖥️ `apps/dashboard/` — HTML sahifalar (kelib ko'rinadigan qism)

Bu — foydalanuvchi brauzerda ochadigan HTML sahifalar. Juda yengil — asosiy ish JS tarafida.

**Asosiy fayllar:**

| Fayl | Nima qiladi |
|---|---|
| **`views.py`** | `DashboardView`, `LeadsView`, `AnalyticsView`, `AIChatView` — har bir sahifani render qiladi. Period (davr) tanlovini parsing qiladi. |
| **`urls.py`** | URL'lar: `/`, `/leads/`, `/contacts/`, `/analytics/`, `/ai-chat/`. |

**Templates:**

| Shablon | Nima qiladi |
|---|---|
| `base.html` | Asosiy "ramka" — header, footer, JS yuklash. Hamma sahifa shundan meros oladi. |
| `dashboard/index.html` | Bosh sahifa — kartalar, grafiklar |
| `dashboard/_dash_body.html` | Dashboard'ning ichki qismi (AJAX yangilash uchun alohida) |
| `dashboard/leads.html` | Lidlar ro'yxati |
| `dashboard/analytics.html` | Chuqur analitika sahifasi |
| `dashboard/ai_chat.html` | To'liq sahifali AI chat |

---

## 🎨 `static/js/` — JavaScript fayllar

| Fayl | Vazifasi | Qator |
|---|---|---|
| **`dashboard_dynamic.js`** | Dashboard'ning butun mantiqi — kartalar, grafiklar, davr filtrlash, AJAX yangilash, AI buyruqlarni qabul qilish (`dashboard:command` event). | ~1323 |
| **`chart_render.js`** | **Shared chart modul** — `window.AIChartRender`. 43 turdagi grafikni chizadi (bar, line, pie, sankey, treemap, funnel, sunburst, network, chord, va h.k.). Ham dashboard, ham AI chat ishlatadi. Inline styles — Shadow DOM ichida ham ishlaydi. | ~1195 |
| **`ai_chat_widget.js`** | Suzuvchi AI chat (pastdagi 💬 tugma). Shadow DOM ichida — CSS izolyatsiya. Mikrofon, voice xabarlar, transkript, AI javoblar. | ~955 |
| **`ai_chat.js`** | To'liq sahifali AI chat (`/ai-chat/` sahifa) | — |
| **`ai_lab.js`** | AI tajriba xonasi — har xil model sinash | — |
| **`charts.js`** | Eski chart kodi (asosan `chart_render.js` ishlatiladi endi) | — |
| **`api.js`** | API chaqirish yordamchi funksiyalari (`fetch`, CSRF) | — |
| **`dashboard.js`** | Eski dashboard kodi (legacy) | — |

**Kutubxonalar (CDN orqali):**
- `Chart.js 4.4.0` — asosiy chart kutubxona
- `chartjs-chart-treemap@2.3.1` — treemap
- `chartjs-chart-sankey@0.12.1` — sankey diagrammasi
- `chartjs-chart-matrix@2.0.1` — heatmap/correlation matrix
- `@sgratzl/chartjs-chart-boxplot@4.4.4` — boxplot va violin
- `marked.js` — markdown → HTML

---

## ⚙️ `config/` — Django sozlamalari

| Fayl | Nima qiladi |
|---|---|
| **`settings/base.py`** | Hammaga umumiy sozlamalar — INSTALLED_APPS, MIDDLEWARE, DATABASES, LANGCHAIN sozlamalari. |
| **`settings/local.py`** | Lokal/dev sozlamalari — DEBUG=True, sqlite/postgres |
| **`settings/production.py`** | Production sozlamalari — DEBUG=False, xavfsizlik |
| **`urls.py`** | Asosiy URL — `/admin/`, `/`, `/api/v1/`, `/amocrm/` |
| **`celery.py`** | Celery konfiguratsiyasi — Redis broker, Beat schedule |
| **`asgi.py`** / **`wsgi.py`** | Server kirish nuqtalari (ASGI Channels uchun, WSGI Gunicorn uchun) |

---

## 🔐 `.env` — maxfiy sozlamalar

```
SECRET_KEY=...
DB_PASSWORD=...
AMOCRM_CLIENT_ID=...
AMOCRM_CLIENT_SECRET=...
ANTHROPIC_API_KEY=...
```

⚠️ **Bu faylni hech qachon git'ga commit qilmang!** `.gitignore` da bor.

---

## 🐳 Docker — `Dockerfile` + `docker-compose.yml`

| Servis | Vazifasi |
|---|---|
| **web** | Django (gunicorn) |
| **db** | PostgreSQL |
| **redis** | Cache + Celery broker |
| **celery** | Fon ishchi (sinxronlash) |
| **celery-beat** | Vaqt bo'yicha vazifalar rejalashtirish |

---

## 🔄 Loyihaning umumiy oqimi (foydalanuvchi nuqtai nazaridan)

```
1. Foydalanuvchi brauzerda http://server/ ni ochadi
   ↓
2. Django dashboard/index.html ni render qiladi
   ↓
3. JS (dashboard_dynamic.js) AJAX bilan /api/v1/dashboard/data/ ga so'rov yuboradi
   ↓
4. API (apps/api) → AnalyticsService → AmoCRM bazadagi ma'lumotlarni hisoblaydi
   ↓
5. JSON qaytadi, JS chart_render.js bilan grafiklarni chizadi
   ↓
6. Foydalanuvchi 💬 AI tugmasini bosadi → ai_chat_widget.js panelini ochadi
   ↓
7. Savol yozadi (yoki 🎤 bilan aytadi)
   ↓
8. POST /api/v1/ai/chat/ → apps/ai_analyst/agent.py → Claude API
   ↓
9. Claude tool chaqiradi (kerak bo'lsa) → ma'lumot oladi → javob beradi
   ↓
10. Javob + chart + buyruq qaytadi → JS chartni chizadi, buyruqni dashboard'ga uzatadi
   ↓
11. Dashboard real vaqtda yangilanadi (masalan, "loss kartasi yashirildi")
```

---

## 🧩 Fon jarayonlar (foydalanuvchi ko'rmaydi)

```
Har 15 daqiqada:
  Celery Beat → sync_leads → AmoCRM API → bazaga yozish

Har soat:
  daily_stat hisoblash → DailyStat jadvali yangilanadi

Hujjat yuklanganda:
  loaders.py → matn bo'laklari → embedding → FAISS ombor
```

---

## 📚 Glossariy (atamalar lug'ati)

| Atama | Tushuntirish |
|---|---|
| **CRM** | Mijozlar bilan ishlash tizimi (AmoCRM, Bitrix) |
| **Lead (lid)** | Potentsial mijoz — kim biror narsani sotib olish niyatida |
| **Pipeline** | Sotuv yo'nalishi — bosqichlardan iborat (qiziqdi → ko'rsatdik → tashrif → sotildi) |
| **LLM** | Large Language Model — katta til modeli (Claude, GPT) |
| **RAG** | Retrieval-Augmented Generation — hujjatdan ma'lumot olib AI'ga uzatish |
| **Agent** | AI'ning "asboblardan foydalanish" qobiliyati — o'zi tool chaqiradi |
| **Tool** | Agent ishlatadigan funksiya (`get_managers`, `make_chart`) |
| **Embedding** | Matnni raqamli vektor qilish (FAISS uchun) |
| **FAISS** | Facebook AI Similarity Search — tez vektor qidirish kutubxonasi |
| **Shadow DOM** | Brauzer izolatsiya texnologiyasi — CSS oqib ketmasligi uchun |
| **WebSocket** | Brauzer ↔ server real vaqt aloqasi (Channels orqali) |
| **JWT** | JSON Web Token — autentifikatsiya kaliti |
| **Celery** | Fon vazifalarini bajarish (sinxronlash, hisoblash) |

---

## 🎓 Loyihaga kelgan yangi dasturchi nimadan boshlashi kerak?

1. **`config/settings/base.py`** — sozlamalarni ko'r
2. **`apps/amocrm/models.py`** — qanday ma'lumotlar bilan ishlaydi
3. **`apps/analytics/services.py`** — qanday statistika hisoblanadi
4. **`apps/api/v1/urls.py`** — qanday API endpoint'lar bor
5. **`apps/ai_analyst/agent.py`** — AI qanday ishlaydi
6. **`static/js/dashboard_dynamic.js`** — frontend qanday yangilanadi
7. **`static/js/chart_render.js`** — grafiklar qanday chiziladi

---

*Hujjat oxirgi yangilanish: 2026-05-25*
