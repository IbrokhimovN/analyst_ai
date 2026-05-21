# AmoCRM AI Dashboard — Setup qo'llanmasi

## Loyiha haqida

AmoCRM va Bitrix24 ma'lumotlarini Django orqali tortib, AI (Claude) yordamida tahlil qiladigan va HTML/CSS/JS dashboard orqali ko'rsatadigan to'liq tizim. Adapter pattern yordamida har ikki CRM bir xil interfeys orqali boshqariladi.

**Texnologiyalar:**
- Backend: Django 5 + Django REST Framework + Celery
- Database: PostgreSQL + Redis
- Frontend: HTML / CSS / Vanilla JS + Chart.js
- AI: Anthropic Claude API
- Realtime: Django Channels (WebSocket)
- CRM: AmoCRM v4 API + Bitrix24 REST API (Adapter pattern)

---

## Loyiha tuzilmasi

```
amocrm_dashboard/
├── backend/
│   ├── config/
│   │   ├── settings/
│   │   │   ├── base.py
│   │   │   ├── local.py
│   │   │   └── production.py
│   │   ├── urls.py
│   │   ├── asgi.py
│   │   └── wsgi.py
│   ├── apps/
│   │   ├── crm/                        # Unified CRM adapter layer (Adapter pattern)
│   │   │   ├── __init__.py
│   │   │   ├── base.py                 # BaseCRMAdapter — abstract interfeys
│   │   │   ├── factory.py              # get_crm_adapter() — sozlamadan adapter tanlash
│   │   │   └── adapters/
│   │   │       ├── __init__.py
│   │   │       ├── amocrm.py           # AmoCRMAdapter (create/update/delete)
│   │   │       └── bitrix.py           # Bitrix24Adapter (crm.deal.add/update/delete)
│   │   ├── amocrm/                     # AmoCRM — sync va OAuth
│   │   │   ├── management/
│   │   │   │   └── commands/
│   │   │   │       └── sync_amocrm.py  # python manage.py sync_amocrm
│   │   │   ├── models.py               # AmoCRMToken, Lead, Contact, Pipeline
│   │   │   ├── services.py             # Faqat GET (sync uchun), token yangilash
│   │   │   ├── tasks.py                # Celery: sync_leads, sync_contacts
│   │   │   ├── views.py                # OAuth: /amocrm/auth/, /amocrm/callback/
│   │   │   ├── urls.py
│   │   │   ├── admin.py
│   │   │   └── webhooks.py
│   │   ├── analytics/                  # Tahlil
│   │   │   ├── models.py
│   │   │   ├── services.py
│   │   │   ├── serializers.py
│   │   │   └── admin.py
│   │   ├── ai_analyst/                 # Claude AI integratsiya
│   │   │   ├── services.py
│   │   │   ├── prompts.py
│   │   │   └── consumers.py            # WebSocket consumer
│   │   ├── api/                        # REST API
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── urls.py
│   │   │       ├── views/
│   │   │       │   ├── __init__.py
│   │   │       │   ├── leads.py        # CRUD → get_crm_adapter() orqali
│   │   │       │   ├── contacts.py     # CRUD → get_crm_adapter() orqali
│   │   │       │   ├── analytics.py
│   │   │       │   └── ai.py
│   │   │       └── serializers/
│   │   │           ├── __init__.py
│   │   │           └── leads.py
│   │   └── dashboard/                  # Template views
│   │       ├── views.py
│   │       └── urls.py
│   ├── templates/
│   │   ├── base.html
│   │   └── dashboard/
│   │       ├── index.html
│   │       ├── leads.html
│   │       ├── analytics.html
│   │       └── ai_chat.html
│   ├── static/
│   │   ├── css/
│   │   │   └── dashboard.css
│   │   └── js/
│   │       ├── api.js                  # Fetch wrapper + JWT
│   │       ├── charts.js               # Chart.js graflar
│   │       ├── ai_chat.js              # WebSocket AI chat
│   │       └── dashboard.js
│   └── manage.py
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── .env.example
└── requirements.txt
```

**Arxitektura qoidasi:** `apps/amocrm/services.py` faqat ma'lumot **olish** (GET/sync) uchun. **Yaratish, yangilash, o'chirish** esa `apps/crm/adapters/` orqali o'tadi. Bu ikki CRMni bir xil view kodidan boshqarish imkonini beradi.

---

## 1. Muhit tayyorlash

### Python virtual environment

```bash
python -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows

pip install --upgrade pip
```

### `requirements.txt`

```
django==5.0.6
djangorestframework==3.15.1
djangorestframework-simplejwt==5.3.1
django-cors-headers==4.3.1
django-environ==0.11.2
channels==4.1.0
channels-redis==4.2.0
celery==5.4.0
redis==5.0.4
psycopg2-binary==2.9.9
anthropic==0.29.0
requests==2.32.3
drf-spectacular==0.27.2          # Swagger docs
django-filter==24.2
gunicorn==22.0.0
```

```bash
pip install -r requirements.txt
```

---

## 2. `.env` fayli

```env
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# PostgreSQL
DB_NAME=amocrm_dashboard
DB_USER=postgres
DB_PASSWORD=yourpassword
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_URL=redis://localhost:6379/0

# AmoCRM
AMOCRM_DOMAIN=yourcompany.amocrm.ru
AMOCRM_CLIENT_ID=your-client-id
AMOCRM_CLIENT_SECRET=your-client-secret
AMOCRM_REDIRECT_URI=http://localhost:8000/amocrm/callback/

# Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-...

# Bitrix24
BITRIX_WEBHOOK_URL=https://yourcompany.bitrix24.ru/rest/1/webhooktoken/

# CRM sozlama: 'amocrm' yoki 'bitrix'
DEFAULT_CRM=amocrm

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

---

## 3. PostgreSQL va Redis o'rnatish

### PostgreSQL

```bash
# Ubuntu/Debian
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql

# Database yaratish
sudo -u postgres psql
CREATE DATABASE amocrm_dashboard;
CREATE USER postgres WITH PASSWORD 'yourpassword';
GRANT ALL PRIVILEGES ON DATABASE amocrm_dashboard TO postgres;
\q
```

### Redis

```bash
# Ubuntu/Debian
sudo apt install redis-server
sudo systemctl start redis
redis-cli ping   # PONG chiqsa tayyor
```

---

## 4. Django sozlash

### `config/settings/base.py` (asosiy qismlar)

```python
import environ
env = environ.Env()
environ.Env.read_env('.env')

SECRET_KEY = env('SECRET_KEY')
DEBUG = env.bool('DEBUG', default=False)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'channels',
    'drf_spectacular',
    'django_filters',
    # Local apps
    'apps.crm',          # Unified CRM adapter (AmoCRM + Bitrix24)
    'apps.amocrm',
    'apps.analytics',
    'apps.ai_analyst',
    'apps.dashboard',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST'),
        'PORT': env('DB_PORT'),
    }
}

# Redis / Cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': env('REDIS_URL'),
    }
}

# Channels (WebSocket)
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {'hosts': [env('REDIS_URL')]},
    }
}

# Celery
CELERY_BROKER_URL = env('CELERY_BROKER_URL')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND')
CELERY_BEAT_SCHEDULE = {
    'sync-amocrm-every-15min': {
        'task': 'apps.amocrm.tasks.sync_all',
        'schedule': 900,  # 15 daqiqa
    },
}

# DRF
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
}

# Swagger
SPECTACULAR_SETTINGS = {
    'TITLE': 'AmoCRM AI Dashboard API',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# AmoCRM
AMOCRM_DOMAIN = env('AMOCRM_DOMAIN')
AMOCRM_CLIENT_ID = env('AMOCRM_CLIENT_ID')
AMOCRM_CLIENT_SECRET = env('AMOCRM_CLIENT_SECRET')
AMOCRM_REDIRECT_URI = env('AMOCRM_REDIRECT_URI')

# Bitrix24
BITRIX_WEBHOOK_URL = env('BITRIX_WEBHOOK_URL', default='')

# Faol CRM: 'amocrm' yoki 'bitrix' — view lar shu sozlamaga qaraydi
DEFAULT_CRM = env('DEFAULT_CRM', default='amocrm')

# Anthropic
ANTHROPIC_API_KEY = env('ANTHROPIC_API_KEY')

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
```

---

## 5. CRM Adapter Layer

### `apps/crm/base.py` — Umumiy interfeys

```python
from abc import ABC, abstractmethod

class BaseCRMAdapter(ABC):

    @abstractmethod
    def create_lead(self, data: dict) -> dict: ...

    @abstractmethod
    def update_lead(self, crm_id: int, data: dict) -> dict: ...

    @abstractmethod
    def delete_lead(self, crm_id: int) -> bool: ...

    @abstractmethod
    def create_contact(self, data: dict) -> dict: ...

    @abstractmethod
    def update_contact(self, crm_id: int, data: dict) -> dict: ...

    @abstractmethod
    def delete_contact(self, crm_id: int) -> bool: ...
```

### `apps/crm/factory.py` — Adapter tanlash

```python
from django.conf import settings
from .adapters.amocrm import AmoCRMAdapter
from .adapters.bitrix import Bitrix24Adapter

def get_crm_adapter(source: str = None):
    s = source or settings.DEFAULT_CRM
    if s == 'amocrm':
        return AmoCRMAdapter()
    elif s == 'bitrix':
        return Bitrix24Adapter()
    raise ValueError(f"Noma'lum CRM: {s}")
```

### `apps/crm/adapters/amocrm.py` — AmoCRM adapteri

```python
import requests
from django.conf import settings
from django.core.cache import cache
from ..base import BaseCRMAdapter

class AmoCRMAdapter(BaseCRMAdapter):
    BASE_URL = f"https://{settings.AMOCRM_DOMAIN}"

    def _get_token(self):
        token = cache.get("amocrm_token")
        if token:
            return token
        from apps.amocrm.models import AmoCRMToken
        obj = AmoCRMToken.objects.first()
        resp = requests.post(f"{self.BASE_URL}/oauth2/access_token", json={
            "client_id":     settings.AMOCRM_CLIENT_ID,
            "client_secret": settings.AMOCRM_CLIENT_SECRET,
            "grant_type":    "refresh_token",
            "refresh_token": obj.refresh_token,
            "redirect_uri":  settings.AMOCRM_REDIRECT_URI,
        })
        data = resp.json()
        obj.access_token = data["access_token"]
        obj.refresh_token = data["refresh_token"]
        obj.save()
        cache.set("amocrm_token", data["access_token"], timeout=82800)
        return data["access_token"]

    def _h(self):
        return {"Authorization": f"Bearer {self._get_token()}",
                "Content-Type": "application/json"}

    def create_lead(self, data: dict) -> dict:
        r = requests.post(f"{self.BASE_URL}/api/v4/leads",
                          headers=self._h(), json=[data])
        r.raise_for_status()
        leads = r.json().get("_embedded", {}).get("leads", [])
        return {"crm_id": leads[0]["id"], "raw": leads[0]} if leads else {}

    def update_lead(self, crm_id: int, data: dict) -> dict:
        r = requests.patch(f"{self.BASE_URL}/api/v4/leads/{crm_id}",
                           headers=self._h(), json=data)
        r.raise_for_status()
        return r.json()

    def delete_lead(self, crm_id: int) -> bool:
        r = requests.delete(f"{self.BASE_URL}/api/v4/leads/{crm_id}",
                            headers=self._h())
        return r.status_code == 204

    def create_contact(self, data: dict) -> dict:
        r = requests.post(f"{self.BASE_URL}/api/v4/contacts",
                          headers=self._h(), json=[data])
        r.raise_for_status()
        items = r.json().get("_embedded", {}).get("contacts", [])
        return {"crm_id": items[0]["id"], "raw": items[0]} if items else {}

    def update_contact(self, crm_id: int, data: dict) -> dict:
        r = requests.patch(f"{self.BASE_URL}/api/v4/contacts/{crm_id}",
                           headers=self._h(), json=data)
        r.raise_for_status()
        return r.json()

    def delete_contact(self, crm_id: int) -> bool:
        r = requests.delete(f"{self.BASE_URL}/api/v4/contacts/{crm_id}",
                            headers=self._h())
        return r.status_code == 204
```

### `apps/crm/adapters/bitrix.py` — Bitrix24 adapteri

```python
import requests
from django.conf import settings
from ..base import BaseCRMAdapter

class Bitrix24Adapter(BaseCRMAdapter):
    """
    Bitrix24 REST API webhook orqali ishlaydi.
    BITRIX_WEBHOOK_URL = "https://yourcompany.bitrix24.ru/rest/1/token/"
    """

    @property
    def base(self):
        return settings.BITRIX_WEBHOOK_URL.rstrip("/")

    def _call(self, method: str, params: dict) -> dict:
        r = requests.post(f"{self.base}/{method}/", json=params)
        r.raise_for_status()
        data = r.json()
        if "error" in data:
            raise Exception(f"Bitrix24: {data.get('error_description', data['error'])}")
        return data.get("result", {})

    def create_lead(self, data: dict) -> dict:
        fields = {
            "TITLE":       data.get("name", "Yangi deal"),
            "OPPORTUNITY": str(data.get("price", 0)),
            "CURRENCY_ID": "UZS",
            "CATEGORY_ID": data.get("pipeline_id", 0),
            "STAGE_ID":    data.get("stage_id", "NEW"),
        }
        result = self._call("crm.deal.add", {"fields": fields})
        return {"crm_id": result, "raw": {"id": result}}

    def update_lead(self, crm_id: int, data: dict) -> dict:
        fields = {}
        if "name"     in data: fields["TITLE"]       = data["name"]
        if "price"    in data: fields["OPPORTUNITY"]  = str(data["price"])
        if "stage_id" in data: fields["STAGE_ID"]     = data["stage_id"]
        self._call("crm.deal.update", {"id": crm_id, "fields": fields})
        return {"id": crm_id}

    def delete_lead(self, crm_id: int) -> bool:
        self._call("crm.deal.delete", {"id": crm_id})
        return True

    def create_contact(self, data: dict) -> dict:
        parts = data.get("name", "").split(" ", 1)
        fields = {
            "NAME":      parts[0],
            "LAST_NAME": parts[1] if len(parts) > 1 else "",
            "PHONE":     [{"VALUE": data.get("phone", ""), "VALUE_TYPE": "WORK"}],
            "EMAIL":     [{"VALUE": data.get("email", ""), "VALUE_TYPE": "WORK"}],
        }
        result = self._call("crm.contact.add", {"fields": fields})
        return {"crm_id": result, "raw": {"id": result}}

    def update_contact(self, crm_id: int, data: dict) -> dict:
        fields = {}
        if "name" in data:
            parts = data["name"].split(" ", 1)
            fields["NAME"]      = parts[0]
            fields["LAST_NAME"] = parts[1] if len(parts) > 1 else ""
        if "phone" in data: fields["PHONE"] = [{"VALUE": data["phone"], "VALUE_TYPE": "WORK"}]
        if "email" in data: fields["EMAIL"] = [{"VALUE": data["email"], "VALUE_TYPE": "WORK"}]
        self._call("crm.contact.update", {"id": crm_id, "fields": fields})
        return {"id": crm_id}

    def delete_contact(self, crm_id: int) -> bool:
        self._call("crm.contact.delete", {"id": crm_id})
        return True
```

### View da adapter ishlatish (`apps/api/v1/views/leads.py`)

```python
from apps.crm.factory import get_crm_adapter

class LeadListCreateView(generics.ListCreateAPIView):
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        source = request.data.get("source", settings.DEFAULT_CRM)
        adapter = get_crm_adapter(source)

        try:
            result = adapter.create_lead(serializer.validated_data)
        except Exception as e:
            return Response({"error": str(e)}, status=502)

        lead = serializer.save(amocrm_id=result["crm_id"], source=source, is_synced=True)
        return Response(LeadSerializer(lead).data, status=201)
```

---

## 6. AmoCRM integratsiya (sync)

### `apps/amocrm/services.py`

```python
import requests
from django.conf import settings
from django.core.cache import cache

class AmoCRMService:
    BASE_URL = f"https://{settings.AMOCRM_DOMAIN}"
    TOKEN_CACHE_KEY = "amocrm_access_token"

    def get_token(self):
        token = cache.get(self.TOKEN_CACHE_KEY)
        if not token:
            # DB dan refresh token olib yangilash
            from .models import AmoCRMToken
            obj = AmoCRMToken.objects.first()
            resp = requests.post(f"{self.BASE_URL}/oauth2/access_token", json={
                "client_id": settings.AMOCRM_CLIENT_ID,
                "client_secret": settings.AMOCRM_CLIENT_SECRET,
                "grant_type": "refresh_token",
                "refresh_token": obj.refresh_token,
                "redirect_uri": settings.AMOCRM_REDIRECT_URI,
            })
            data = resp.json()
            token = data["access_token"]
            obj.refresh_token = data["refresh_token"]
            obj.save()
            cache.set(self.TOKEN_CACHE_KEY, token, timeout=data["expires_in"] - 60)
        return token

    def _headers(self):
        return {"Authorization": f"Bearer {self.get_token()}"}

    def get_leads(self, page=1, limit=250):
        resp = requests.get(
            f"{self.BASE_URL}/api/v4/leads",
            headers=self._headers(),
            params={"page": page, "limit": limit, "with": "contacts,loss_reason"},
        )
        return resp.json()

    def get_contacts(self, page=1, limit=250):
        resp = requests.get(
            f"{self.BASE_URL}/api/v4/contacts",
            headers=self._headers(),
            params={"page": page, "limit": limit},
        )
        return resp.json()

    def get_pipelines(self):
        resp = requests.get(f"{self.BASE_URL}/api/v4/leads/pipelines", headers=self._headers())
        return resp.json()
```

### `apps/amocrm/tasks.py`

```python
from celery import shared_task
from .services import AmoCRMService
from .models import Lead, Contact

@shared_task
def sync_leads():
    service = AmoCRMService()
    page = 1
    while True:
        data = service.get_leads(page=page)
        items = data.get("_embedded", {}).get("leads", [])
        if not items:
            break
        for item in items:
            Lead.objects.update_or_create(
                amocrm_id=item["id"],
                defaults={
                    "name": item["name"],
                    "price": item.get("price", 0),
                    "status_id": item.get("status_id"),
                    "pipeline_id": item.get("pipeline_id"),
                    "created_at": item.get("created_at"),
                    "updated_at": item.get("updated_at"),
                    "raw_data": item,
                }
            )
        page += 1

@shared_task
def sync_all():
    sync_leads.delay()
    # sync_contacts.delay()
    # sync_deals.delay()
```

---

## 7. AI Analyst

### `apps/ai_analyst/services.py`

```python
import anthropic
from django.conf import settings
from apps.analytics.services import AnalyticsService

client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """
Siz AmoCRM sotuv ma'lumotlarini tahlil qiladigan professional biznes analitikisiz.
Quyidagi ma'lumotlar asosida aniq, qisqa va amaliy tavsiyalar bering.
Javobni o'zbek tilida yozing. Markdown formatlash ishlating.
"""

def analyze_data(question: str, context_data: dict) -> str:
    """Foydalanuvchi savolini ma'lumotlar bilan birga Claude ga yuborish."""
    context = f"""
## Joriy ma'lumotlar:
- Jami leads: {context_data.get('total_leads', 0)}
- Konversiya: {context_data.get('conversion_rate', 0):.1f}%
- O'rtacha deal hajmi: {context_data.get('avg_deal_size', 0):,.0f} so'm
- Bu oy tushumlari: {context_data.get('monthly_revenue', 0):,.0f} so'm
- Top menejerlar: {context_data.get('top_managers', [])}
    """
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"{context}\n\nSavol: {question}"}],
    )
    return message.content[0].text

def generate_weekly_report(stats: dict) -> str:
    """Haftalik avtomatik hisobot generatsiya."""
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Quyidagi haftalik statistika asosida batafsil hisobot yoz: {stats}"}],
    )
    return message.content[0].text
```

---

## 8. REST API — `/api/v1/`

### `apps/api/v1/urls.py`

```python
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('leads/',        include('apps.api.v1.views.leads')),
    path('contacts/',     include('apps.api.v1.views.contacts')),
    path('analytics/',    include('apps.api.v1.views.analytics')),
    path('ai/',           include('apps.api.v1.views.ai')),
    # Auth
    path('auth/token/',   TokenObtainPairView.as_view()),
    path('auth/refresh/', TokenRefreshView.as_view()),
    # Docs
    path('schema/',       SpectacularAPIView.as_view(), name='schema'),
    path('docs/',         SpectacularSwaggerView.as_view(url_name='schema')),
]
```

### Asosiy endpointlar

| Method | Endpoint | Tavsif |
|--------|----------|--------|
| GET | `/api/v1/leads/` | Leadlar ro'yxati (filter, pagination) |
| GET | `/api/v1/leads/{id}/` | Bitta lead |
| GET | `/api/v1/analytics/summary/` | Umumiy statistika |
| GET | `/api/v1/analytics/funnel/` | Sotuv funnel |
| GET | `/api/v1/analytics/by-manager/` | Menejer bo'yicha |
| POST | `/api/v1/ai/chat/` | AI ga savol yuborish |
| GET | `/api/v1/ai/report/weekly/` | Haftalik AI hisobot |
| POST | `/api/v1/auth/token/` | JWT olish |

---

## 9. Template views

### `apps/dashboard/views.py`

```python
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from apps.analytics.services import AnalyticsService

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["stats"] = AnalyticsService().get_summary()
        return ctx

class LeadsView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/leads.html"

class AnalyticsView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/analytics.html"

class AIChatView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/ai_chat.html"
```

### `config/urls.py`

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # Template pages
    path('', include('apps.dashboard.urls')),
    # REST API
    path('api/v1/', include('apps.api.v1.urls')),
    # AmoCRM OAuth callback
    path('amocrm/', include('apps.amocrm.urls')),
    # WebSocket (asgi orqali)
]
```

---

## 10. Frontend (JS) asosiy qismlar

### `static/js/api.js`

```javascript
const API = {
  baseUrl: '/api/v1',

  async request(path, options = {}) {
    const token = localStorage.getItem('access_token');
    const res = await fetch(this.baseUrl + path, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options.headers || {}),
      },
    });
    if (res.status === 401) { window.location.href = '/login/'; }
    return res.json();
  },

  get: (path) => API.request(path),
  post: (path, body) => API.request(path, { method: 'POST', body: JSON.stringify(body) }),
};
```

### `static/js/ai_chat.js` (WebSocket)

```javascript
class AIChatWidget {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.ws = null;
    this.connect();
  }

  connect() {
    this.ws = new WebSocket(`ws://${location.host}/ws/ai/`);
    this.ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      this.appendMessage('ai', data.message);
    };
  }

  sendMessage(text) {
    this.appendMessage('user', text);
    this.ws.send(JSON.stringify({ message: text }));
  }

  appendMessage(role, text) {
    const div = document.createElement('div');
    div.className = `chat-message ${role}`;
    div.innerHTML = marked.parse(text);   // markdown render
    this.container.appendChild(div);
    this.container.scrollTop = this.container.scrollHeight;
  }
}
```

---

## 11. Docker bilan ishga tushirish

### `docker-compose.yml`

```yaml
version: '3.9'
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: amocrm_dashboard
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: yourpassword
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

  web:
    build: .
    command: gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    env_file: .env
    depends_on: [db, redis]

  celery:
    build: .
    command: celery -A config worker -l info
    env_file: .env
    depends_on: [db, redis]

  celery-beat:
    build: .
    command: celery -A config beat -l info
    env_file: .env
    depends_on: [db, redis]

volumes:
  pgdata:
```

---

## 12. Loyihani ishga tushirish (local)

```bash
# 1. Migratsiyalar
python manage.py makemigrations
python manage.py migrate

# 2. Superuser
python manage.py createsuperuser

# 3. Static fayllar
python manage.py collectstatic

# 4. Celery (alohida terminal)
celery -A config worker -l info
celery -A config beat -l info

# 5. Django server
python manage.py runserver

# 6. AmoCRM OAuth (bir marta)
# http://localhost:8000/amocrm/auth/ ga kirish va ruxsat berish

# 7. Dastlabki sync
python manage.py shell
>>> from apps.amocrm.tasks import sync_all
>>> sync_all()
```

---

## 13. AmoCRM OAuth sozlash

1. [AmoCRM Developer](https://www.amocrm.ru/developers/) sahifasiga kiring
2. Yangi integratsiya yarating
3. `Redirect URI` ni `http://localhost:8000/amocrm/callback/` qiling
4. `Client ID` va `Client Secret` ni `.env` ga qo'ying
5. `/amocrm/auth/` ga kiring va ruxsat bering — token avtomatik saqlanadi

---

## 14. Bitrix24 sozlash

1. Bitrix24 → **Ilovalar** → **Webhooks** → **Kiruvchi webhook** yarating
2. Ruxsatlar (Permissions): `CRM` ni belgilang
3. Olingan URL ni `.env` ga yozing:
   ```
   BITRIX_WEBHOOK_URL=https://yourcompany.bitrix24.ru/rest/1/abc123token/
   ```
4. `.env` da `DEFAULT_CRM=bitrix` yoki `DEFAULT_CRM=amocrm` qiling (har biri alohida ishlaydi)
5. Tekshirish:
   ```bash
   python manage.py shell
   >>> from apps.crm.factory import get_crm_adapter
   >>> a = get_crm_adapter('bitrix')
   >>> a.create_lead({"name": "Test deal", "price": 100000})
   ```

**Bitrix24 ma'lumotlarini sinxronlash:**

```bash
# Barcha entitylarni sinxronlash
python manage.py sync_bitrix

# Faqat deallarni
python manage.py sync_bitrix --deals

# Faqat kontaktlarni
python manage.py sync_bitrix --contacts

# Faqat Bitrix Leadlarni (dastlabki murojaatlar)
python manage.py sync_bitrix --leads

# Celery task orqali (asinxron)
python manage.py sync_bitrix --async
```

**Ikki CRM ni bir vaqtda ishlatish** — lead yaratilganda ham AmoCRM, ham Bitrix24 ga yuborish:

```python
from apps.crm.factory import get_crm_adapter

adapters = [get_crm_adapter('amocrm'), get_crm_adapter('bitrix')]
for adapter in adapters:
    adapter.create_lead(data)
```

**Dashboard da CRM source filter:**
- `?source=amocrm` — faqat AmoCRM ma'lumotlari
- `?source=bitrix` — faqat Bitrix24 ma'lumotlari
- `?` (parametrsiz) — barcha CRM lardan

**API da CRM source filter:**
```
GET /api/v1/leads/?source=amocrm
GET /api/v1/contacts/?source=bitrix
GET /api/v1/analytics/summary/?source=amocrm
```

---

## 15. Keyingi qadamlar

- Nginx + SSL sozlash (production uchun)
- Sentry xatoliklarni kuzatish
- Grafana + Prometheus monitoring
- Docker Swarm yoki Kubernetes deploy
- AmoCRM webhook endpointlarini real-time sync uchun ulash
- Bitrix24 Activity Stream integratsiyasi
- Bitrix24 Event webhooks (real-time sync)
- Dashboard da AmoCRM + Bitrix24 taqqoslama grafiklari