"""
AmoCRM Adapter — AmoCRM v4 API orqali CRUD va ma'lumot olish.

Bu adapter faqat CRM bilan aloqa qiladi.
Token boshqaruvi apps.amocrm.services.AmoCRMService dan olinadi.
"""
import logging

import requests
from django.conf import settings
from django.core.cache import cache

from ..base import BaseCRMAdapter

logger = logging.getLogger(__name__)


class AmoCRMAdapter(BaseCRMAdapter):
    """AmoCRM v4 API adapter."""

    BASE_URL = f"https://{settings.AMOCRM_DOMAIN}"

    # -------------------------------------------------------------------------
    # Token boshqaruvi
    # -------------------------------------------------------------------------

    def _get_token(self):
        """Access tokenni cache yoki DB dan olish."""
        token = cache.get("amocrm_token")
        if token:
            return token

        from apps.amocrm.models import AmoCRMToken
        obj = AmoCRMToken.objects.first()
        if not obj:
            raise ValueError("AmoCRM token topilmadi! Avval OAuth orqali ulaning.")

        resp = requests.post(f"{self.BASE_URL}/oauth2/access_token", json={
            "client_id":     settings.AMOCRM_CLIENT_ID,
            "client_secret": settings.AMOCRM_CLIENT_SECRET,
            "grant_type":    "refresh_token",
            "refresh_token": obj.refresh_token,
            "redirect_uri":  settings.AMOCRM_REDIRECT_URI,
        })
        resp.raise_for_status()
        data = resp.json()

        obj.access_token = data["access_token"]
        obj.refresh_token = data["refresh_token"]
        obj.save()

        cache.set("amocrm_token", data["access_token"], timeout=82800)
        return data["access_token"]

    def _headers(self):
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": "application/json",
        }

    def _get(self, endpoint, params=None):
        """GET request wrapper."""
        url = f"{self.BASE_URL}{endpoint}"
        resp = requests.get(url, headers=self._headers(), params=params, timeout=30)
        resp.raise_for_status()
        if resp.status_code == 204 or not resp.text.strip():
            return {}
        return resp.json()

    # -------------------------------------------------------------------------
    # Lead CRUD
    # -------------------------------------------------------------------------

    def create_lead(self, data: dict) -> dict:
        r = requests.post(
            f"{self.BASE_URL}/api/v4/leads",
            headers=self._headers(), json=[data],
        )
        r.raise_for_status()
        leads = r.json().get("_embedded", {}).get("leads", [])
        return {"crm_id": leads[0]["id"], "raw": leads[0]} if leads else {}

    def update_lead(self, crm_id: int, data: dict) -> dict:
        r = requests.patch(
            f"{self.BASE_URL}/api/v4/leads/{crm_id}",
            headers=self._headers(), json=data,
        )
        r.raise_for_status()
        return r.json()

    def delete_lead(self, crm_id: int) -> bool:
        r = requests.delete(
            f"{self.BASE_URL}/api/v4/leads/{crm_id}",
            headers=self._headers(),
        )
        return r.status_code == 204

    # -------------------------------------------------------------------------
    # Contact CRUD
    # -------------------------------------------------------------------------

    def create_contact(self, data: dict) -> dict:
        r = requests.post(
            f"{self.BASE_URL}/api/v4/contacts",
            headers=self._headers(), json=[data],
        )
        r.raise_for_status()
        items = r.json().get("_embedded", {}).get("contacts", [])
        return {"crm_id": items[0]["id"], "raw": items[0]} if items else {}

    def update_contact(self, crm_id: int, data: dict) -> dict:
        r = requests.patch(
            f"{self.BASE_URL}/api/v4/contacts/{crm_id}",
            headers=self._headers(), json=data,
        )
        r.raise_for_status()
        return r.json()

    def delete_contact(self, crm_id: int) -> bool:
        r = requests.delete(
            f"{self.BASE_URL}/api/v4/contacts/{crm_id}",
            headers=self._headers(),
        )
        return r.status_code == 204

    # -------------------------------------------------------------------------
    # Data fetching (sync uchun)
    # -------------------------------------------------------------------------

    def get_leads(self, page: int = 1, limit: int = 250) -> dict:
        data = self._get("/api/v4/leads", params={
            "page": page, "limit": limit,
            "with": "contacts,loss_reason",
        })
        items = data.get("_embedded", {}).get("leads", [])
        return {
            "items": items,
            "total": len(items),
            "has_more": len(items) >= limit,
        }

    def get_contacts(self, page: int = 1, limit: int = 250) -> dict:
        data = self._get("/api/v4/contacts", params={
            "page": page, "limit": limit,
        })
        items = data.get("_embedded", {}).get("contacts", [])
        return {
            "items": items,
            "total": len(items),
            "has_more": len(items) >= limit,
        }

    def get_pipelines(self) -> list:
        data = self._get("/api/v4/leads/pipelines")
        pipelines = data.get("_embedded", {}).get("pipelines", [])
        result = []
        for p in pipelines:
            statuses = []
            for s in p.get("_embedded", {}).get("statuses", []):
                statuses.append({
                    "id": s["id"],
                    "name": s.get("name", ""),
                    "sort": s.get("sort", 0),
                    "color": s.get("color", ""),
                })
            result.append({
                "id": p["id"],
                "name": p.get("name", ""),
                "sort": p.get("sort", 0),
                "is_main": p.get("is_main", False),
                "statuses": statuses,
                "raw": p,
            })
        return result

    def get_users(self) -> list:
        data = self._get("/api/v4/users")
        users = data.get("_embedded", {}).get("users", [])
        return [
            {"id": u["id"], "name": u.get("name", ""), "email": u.get("email", "")}
            for u in users
        ]
