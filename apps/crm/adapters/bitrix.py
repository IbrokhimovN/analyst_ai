import logging

import requests
from django.conf import settings

from ..base import BaseCRMAdapter

logger = logging.getLogger(__name__)

class Bitrix24Adapter(BaseCRMAdapter):

    @property
    def base_url(self):
        return settings.BITRIX_WEBHOOK_URL.rstrip("/")

    def _call(self, method: str, params: dict = None) -> dict:
        url = f"{self.base_url}/{method}"
        try:
            resp = requests.post(url, json=params or {}, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            if "error" in data:
                error_desc = data.get("error_description", data["error"])
                logger.error(f"Bitrix24 API xatolik: {method} — {error_desc}")
                raise Exception(f"Bitrix24: {error_desc}")

            return data.get("result", data)

        except requests.exceptions.RequestException as e:
            logger.error(f"Bitrix24 so'rov xatolik: {method} — {e}")
            raise

    def _list_all(self, method: str, params: dict = None,
                  page: int = 1, limit: int = 50) -> dict:
        request_params = params or {}
        request_params["start"] = (page - 1) * limit
        request_params.setdefault("order", {"ID": "DESC"})

        resp = requests.post(
            f"{self.base_url}/{method}",
            json=request_params,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        if "error" in data:
            error_desc = data.get("error_description", data["error"])
            raise Exception(f"Bitrix24: {error_desc}")

        items = data.get("result", [])
        total = data.get("total", len(items))
        next_start = data.get("next")

        return {
            "items": items,
            "total": total,
            "has_more": next_start is not None,
        }

    def create_lead(self, data: dict) -> dict:
        fields = {
            "TITLE":       data.get("name", "Yangi deal"),
            "OPPORTUNITY": str(data.get("price", 0)),
            "CURRENCY_ID": data.get("currency", "UZS"),
            "CATEGORY_ID": data.get("pipeline_id", 0),
            "STAGE_ID":    data.get("stage_id", "NEW"),
        }
        if data.get("responsible_user_id"):
            fields["ASSIGNED_BY_ID"] = data["responsible_user_id"]

        result = self._call("crm.deal.add", {"fields": fields})
        return {"crm_id": result, "raw": {"id": result, **fields}}

    def update_lead(self, crm_id: int, data: dict) -> dict:
        fields = {}
        if "name"     in data: fields["TITLE"]       = data["name"]
        if "price"    in data: fields["OPPORTUNITY"]  = str(data["price"])
        if "stage_id" in data: fields["STAGE_ID"]     = data["stage_id"]
        if "responsible_user_id" in data:
            fields["ASSIGNED_BY_ID"] = data["responsible_user_id"]

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
        }
        if data.get("phone"):
            fields["PHONE"] = [{"VALUE": data["phone"], "VALUE_TYPE": "WORK"}]
        if data.get("email"):
            fields["EMAIL"] = [{"VALUE": data["email"], "VALUE_TYPE": "WORK"}]
        if data.get("company"):
            fields["COMPANY_TITLE"] = data["company"]
        if data.get("responsible_user_id"):
            fields["ASSIGNED_BY_ID"] = data["responsible_user_id"]

        result = self._call("crm.contact.add", {"fields": fields})
        return {"crm_id": result, "raw": {"id": result, **fields}}

    def update_contact(self, crm_id: int, data: dict) -> dict:
        fields = {}
        if "name" in data:
            parts = data["name"].split(" ", 1)
            fields["NAME"]      = parts[0]
            fields["LAST_NAME"] = parts[1] if len(parts) > 1 else ""
        if "phone" in data:
            fields["PHONE"] = [{"VALUE": data["phone"], "VALUE_TYPE": "WORK"}]
        if "email" in data:
            fields["EMAIL"] = [{"VALUE": data["email"], "VALUE_TYPE": "WORK"}]

        self._call("crm.contact.update", {"id": crm_id, "fields": fields})
        return {"id": crm_id}

    def delete_contact(self, crm_id: int) -> bool:
        self._call("crm.contact.delete", {"id": crm_id})
        return True

    def get_leads(self, page: int = 1, limit: int = 50) -> dict:
        data = self._list_all("crm.deal.list", params={
            "select": [
                "ID", "TITLE", "OPPORTUNITY", "CURRENCY_ID",
                "STAGE_ID", "CATEGORY_ID", "ASSIGNED_BY_ID",
                "DATE_CREATE", "DATE_MODIFY", "CLOSEDATE",
                "CLOSED", "CONTACT_ID", "COMPANY_ID",
            ],
        }, page=page, limit=limit)

        normalized = []
        for item in data["items"]:
            normalized.append({
                "id": int(item.get("ID", 0)),
                "name": item.get("TITLE", ""),
                "price": float(item.get("OPPORTUNITY", 0) or 0),
                "stage_id": item.get("STAGE_ID", ""),
                "pipeline_id": item.get("CATEGORY_ID", 0),
                "responsible_user_id": int(item.get("ASSIGNED_BY_ID", 0) or 0),
                "created_at": item.get("DATE_CREATE"),
                "updated_at": item.get("DATE_MODIFY"),
                "closed_at": item.get("CLOSEDATE"),
                "is_closed": item.get("CLOSED") == "Y",
                "contact_id": item.get("CONTACT_ID"),
                "company_id": item.get("COMPANY_ID"),
                "raw": item,
            })

        return {
            "items": normalized,
            "total": data["total"],
            "has_more": data["has_more"],
        }

    def get_bitrix_leads(self, page: int = 1, limit: int = 50) -> dict:
        data = self._list_all("crm.lead.list", params={
            "select": [
                "ID", "TITLE", "NAME", "LAST_NAME",
                "OPPORTUNITY", "CURRENCY_ID", "STATUS_ID",
                "ASSIGNED_BY_ID", "DATE_CREATE", "DATE_MODIFY",
                "PHONE", "EMAIL", "SOURCE_ID",
            ],
        }, page=page, limit=limit)

        normalized = []
        for item in data["items"]:
            phone = ""
            email = ""
            if item.get("PHONE"):
                phones = item["PHONE"]
                if isinstance(phones, list) and phones:
                    phone = phones[0].get("VALUE", "")
            if item.get("EMAIL"):
                emails = item["EMAIL"]
                if isinstance(emails, list) and emails:
                    email = emails[0].get("VALUE", "")

            normalized.append({
                "id": int(item.get("ID", 0)),
                "name": item.get("TITLE", ""),
                "first_name": item.get("NAME", ""),
                "last_name": item.get("LAST_NAME", ""),
                "price": float(item.get("OPPORTUNITY", 0) or 0),
                "status_id": item.get("STATUS_ID", ""),
                "responsible_user_id": int(item.get("ASSIGNED_BY_ID", 0) or 0),
                "phone": phone,
                "email": email,
                "source_id": item.get("SOURCE_ID", ""),
                "created_at": item.get("DATE_CREATE"),
                "updated_at": item.get("DATE_MODIFY"),
                "raw": item,
            })

        return {
            "items": normalized,
            "total": data["total"],
            "has_more": data["has_more"],
        }

    def get_contacts(self, page: int = 1, limit: int = 50) -> dict:
        data = self._list_all("crm.contact.list", params={
            "select": [
                "ID", "NAME", "LAST_NAME", "SECOND_NAME",
                "PHONE", "EMAIL", "COMPANY_TITLE",
                "ASSIGNED_BY_ID", "DATE_CREATE", "DATE_MODIFY",
            ],
        }, page=page, limit=limit)

        normalized = []
        for item in data["items"]:
            phone = ""
            email = ""
            if item.get("PHONE"):
                phones = item["PHONE"]
                if isinstance(phones, list) and phones:
                    phone = phones[0].get("VALUE", "")
            if item.get("EMAIL"):
                emails = item["EMAIL"]
                if isinstance(emails, list) and emails:
                    email = emails[0].get("VALUE", "")

            full_name = " ".join(filter(None, [
                item.get("NAME", ""),
                item.get("LAST_NAME", ""),
            ])).strip()

            normalized.append({
                "id": int(item.get("ID", 0)),
                "name": full_name or f"Contact #{item.get('ID', '')}",
                "first_name": item.get("NAME", ""),
                "last_name": item.get("LAST_NAME", ""),
                "phone": phone,
                "email": email,
                "company": item.get("COMPANY_TITLE", ""),
                "responsible_user_id": int(item.get("ASSIGNED_BY_ID", 0) or 0),
                "created_at": item.get("DATE_CREATE"),
                "updated_at": item.get("DATE_MODIFY"),
                "raw": item,
            })

        return {
            "items": normalized,
            "total": data["total"],
            "has_more": data["has_more"],
        }

    def get_pipelines(self) -> list:
        categories = self._call("crm.dealcategory.list")
        if not isinstance(categories, list):
            categories = []

        result = []

        try:
            default_statuses = self._call("crm.dealcategory.stage.list", {
                "id": 0,
            })
            if isinstance(default_statuses, list):
                statuses = [
                    {
                        "id": s.get("STATUS_ID", ""),
                        "name": s.get("NAME", ""),
                        "sort": int(s.get("SORT", 0)),
                        "color": s.get("COLOR", ""),
                    }
                    for s in default_statuses
                ]
            else:
                statuses = []
        except Exception:
            statuses = []

        result.append({
            "id": 0,
            "name": "Umumiy",
            "sort": 0,
            "is_main": True,
            "statuses": statuses,
            "raw": {},
        })

        for cat in categories:
            cat_id = cat.get("ID", 0)
            try:
                cat_statuses = self._call("crm.dealcategory.stage.list", {
                    "id": cat_id,
                })
                if isinstance(cat_statuses, list):
                    statuses = [
                        {
                            "id": s.get("STATUS_ID", ""),
                            "name": s.get("NAME", ""),
                            "sort": int(s.get("SORT", 0)),
                            "color": s.get("COLOR", ""),
                        }
                        for s in cat_statuses
                    ]
                else:
                    statuses = []
            except Exception:
                statuses = []

            result.append({
                "id": int(cat_id),
                "name": cat.get("NAME", f"Category {cat_id}"),
                "sort": int(cat.get("SORT", 0)),
                "is_main": False,
                "statuses": statuses,
                "raw": cat,
            })

        return result

    def get_users(self) -> list:
        try:
            data = self._call("user.get", {
                "ACTIVE": True,
            })
            if not isinstance(data, list):
                return []

            return [
                {
                    "id": int(u.get("ID", 0)),
                    "name": " ".join(filter(None, [
                        u.get("NAME", ""),
                        u.get("LAST_NAME", ""),
                    ])).strip(),
                    "email": u.get("EMAIL", ""),
                }
                for u in data
            ]
        except Exception as e:
            logger.error(f"Bitrix24 foydalanuvchilarni olishda xatolik: {e}")
            return []

    def create_bitrix_lead(self, data: dict) -> dict:
        fields = {
            "TITLE": data.get("name", "Yangi lead"),
        }
        if data.get("phone"):
            fields["PHONE"] = [{"VALUE": data["phone"], "VALUE_TYPE": "WORK"}]
        if data.get("email"):
            fields["EMAIL"] = [{"VALUE": data["email"], "VALUE_TYPE": "WORK"}]
        if data.get("price"):
            fields["OPPORTUNITY"] = str(data["price"])
        if data.get("responsible_user_id"):
            fields["ASSIGNED_BY_ID"] = data["responsible_user_id"]
        if data.get("source_id"):
            fields["SOURCE_ID"] = data["source_id"]

        result = self._call("crm.lead.add", {"fields": fields})
        return {"crm_id": result, "raw": {"id": result, **fields}}

    def get_lead_statuses(self) -> list:
        try:
            data = self._call("crm.status.list", {
                "filter": {"ENTITY_ID": "STATUS"},
            })
            if not isinstance(data, list):
                return []
            return [
                {
                    "id": s.get("STATUS_ID", ""),
                    "name": s.get("NAME", ""),
                    "sort": int(s.get("SORT", 0)),
                    "color": s.get("COLOR", ""),
                }
                for s in data
            ]
        except Exception as e:
            logger.error(f"Bitrix24 lead statuslarini olishda xatolik: {e}")
            return []
