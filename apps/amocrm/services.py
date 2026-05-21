import logging
from datetime import datetime, timezone

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class AmoCRMService:
    """AmoCRM API bilan ishlash servisi."""

    BASE_URL = f"https://{settings.AMOCRM_DOMAIN}"
    TOKEN_CACHE_KEY = "amocrm_access_token"

    # -------------------------------------------------------------------------
    # Token boshqaruvi
    # -------------------------------------------------------------------------

    def get_token(self):
        """Access tokenni cache yoki DB dan olish, kerak bo'lsa yangilash."""
        token = cache.get(self.TOKEN_CACHE_KEY)
        if token:
            return token

        from .models import AmoCRMToken
        obj = AmoCRMToken.objects.first()
        if not obj:
            raise ValueError("AmoCRM token topilmadi! Avval OAuth orqali ulaning.")

        resp = requests.post(f"{self.BASE_URL}/oauth2/access_token", json={
            "client_id": settings.AMOCRM_CLIENT_ID,
            "client_secret": settings.AMOCRM_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": obj.refresh_token,
            "redirect_uri": settings.AMOCRM_REDIRECT_URI,
        })
        resp.raise_for_status()
        data = resp.json()

        token = data["access_token"]
        obj.access_token = token
        obj.refresh_token = data["refresh_token"]
        obj.expires_at = datetime.fromtimestamp(
            datetime.now(timezone.utc).timestamp() + data["expires_in"],
            tz=timezone.utc,
        )
        obj.save()

        cache.set(self.TOKEN_CACHE_KEY, token, timeout=data["expires_in"] - 60)
        logger.info("AmoCRM token yangilandi")
        return token

    def _headers(self):
        return {"Authorization": f"Bearer {self.get_token()}"}

    def _get(self, endpoint, params=None):
        """GET request wrapper with error handling."""
        url = f"{self.BASE_URL}{endpoint}"
        resp = requests.get(url, headers=self._headers(), params=params, timeout=30)
        resp.raise_for_status()
        # AmoCRM 204 No Content qaytaradi — ma'lumot bo'lmaganda
        if resp.status_code == 204 or not resp.text.strip():
            return {}
        return resp.json()

    # -------------------------------------------------------------------------
    # Ma'lumotlarni olish
    # -------------------------------------------------------------------------

    def get_leads(self, page=1, limit=250):
        """Leadlar ro'yxatini olish."""
        return self._get("/api/v4/leads", params={
            "page": page,
            "limit": limit,
            "with": "contacts,loss_reason",
        })

    def get_contacts(self, page=1, limit=250):
        """Kontaktlar ro'yxatini olish."""
        return self._get("/api/v4/contacts", params={
            "page": page,
            "limit": limit,
        })

    def get_pipelines(self):
        """Barcha pipelinelarni olish."""
        return self._get("/api/v4/leads/pipelines")

    def get_users(self):
        """AmoCRM foydalanuvchilarini olish."""
        return self._get("/api/v4/users")

    def get_lead_detail(self, lead_id):
        """Bitta leadning batafsil ma'lumotlarini olish."""
        return self._get(f"/api/v4/leads/{lead_id}", params={
            "with": "contacts,loss_reason,catalog_elements",
        })

    # -------------------------------------------------------------------------
    # OAuth
    # -------------------------------------------------------------------------

    def exchange_code(self, code):
        """OAuth authorization code ni token ga almashtirish."""
        payload = {
            "client_id": settings.AMOCRM_CLIENT_ID,
            "client_secret": settings.AMOCRM_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.AMOCRM_REDIRECT_URI,
        }
        logger.info(f"Token so'rash: domain={settings.AMOCRM_DOMAIN}, redirect_uri={settings.AMOCRM_REDIRECT_URI}")
        resp = requests.post(f"{self.BASE_URL}/oauth2/access_token", json=payload)

        if resp.status_code != 200:
            logger.error(f"AmoCRM token xatolik: {resp.status_code} — {resp.text}")
            raise ValueError(
                f"AmoCRM token olishda xatolik ({resp.status_code}): {resp.text}"
            )

        return resp.json()
