import logging
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote

import requests
from django.conf import settings

DEAL_SELECT = [
    "ID", "TITLE", "OPPORTUNITY", "CURRENCY_ID",
    "STAGE_ID", "CATEGORY_ID", "ASSIGNED_BY_ID",
    "DATE_CREATE", "DATE_MODIFY", "CLOSEDATE",
    "CLOSED", "CONTACT_ID", "COMPANY_ID",
]
CONTACT_SELECT = [
    "ID", "NAME", "LAST_NAME", "SECOND_NAME",
    "PHONE", "EMAIL", "COMPANY_TITLE",
    "ASSIGNED_BY_ID", "DATE_CREATE", "DATE_MODIFY",
]
LEAD_SELECT = [
    "ID", "TITLE", "NAME", "LAST_NAME",
    "OPPORTUNITY", "CURRENCY_ID", "STATUS_ID",
    "ASSIGNED_BY_ID", "DATE_CREATE", "DATE_MODIFY",
    "PHONE", "EMAIL", "SOURCE_ID",
]


def deal_stage_semantic(status_id: str) -> str:
    """Bitrix deal bosqichini won/lost/progress ga ajratadi.
    Bitrix konvensiyasi: WON / C{n}:WON = yutuq; LOSE/APOLOGY / C{n}:LOSE = yo'qotish."""
    tail = (status_id or "").split(":")[-1].upper()
    if tail == "WON":
        return "won"
    if tail in ("LOSE", "APOLOGY"):
        return "lost"
    return "progress"


def lead_status_semantic(semantics: str) -> str:
    """Bitrix lead statusining SEMANTICS belgisi (S/F) bo'yicha tasnif."""
    if semantics == "S":
        return "won"
    if semantics == "F":
        return "lost"
    return "progress"

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

    @staticmethod
    def _encode_params(params: dict) -> str:
        """Bitrix REST query stringini PHP uslubida tuzadi (select[0]=ID...)."""
        parts = []
        for key, val in params.items():
            if isinstance(val, (list, tuple)):
                for i, v in enumerate(val):
                    parts.append(f"{key}[{i}]={quote(str(v))}")
            elif isinstance(val, dict):
                for k, v in val.items():
                    parts.append(f"{key}[{k}]={quote(str(v))}")
            else:
                parts.append(f"{key}={quote(str(val))}")
        return "&".join(parts)

    def _batch(self, commands: dict, halt: int = 0, retries: int = 3) -> dict:
        """Bir HTTP so'rovda 50 tagacha komandani bajaradi (batch).
        Rate-limit (503/QUERY_LIMIT) bo'lsa kichik backoff bilan qayta uradi."""
        last_exc = None
        for attempt in range(retries):
            try:
                resp = requests.post(
                    f"{self.base_url}/batch",
                    json={"halt": halt, "cmd": commands},
                    timeout=120,
                )
                if resp.status_code == 503:
                    raise Exception("Bitrix24 rate limit (503)")
                resp.raise_for_status()
                data = resp.json()
                if data.get("error"):
                    desc = data.get("error_description", data["error"])
                    raise Exception(f"Bitrix24 batch: {desc}")
                return data.get("result", {})
            except Exception as exc:
                last_exc = exc
                time.sleep(0.5 * (attempt + 1))
        raise last_exc

    def _fetch_all_raw(self, method: str, select: list, workers: int = 6,
                       extra_filter: dict = None) -> list:
        """Barcha sahifalarni batch + parallel orqali tortadi.
        50 komanda = 2500 yozuv/batch; batchlar bir vaqtda yuboriladi.
        extra_filter berilsa (masalan {'>=DATE_MODIFY': '...'}) faqat shu yozuvlar tortiladi."""
        base_params = {"select": select, "order": {"ID": "ASC"}}
        if extra_filter:
            base_params["filter"] = extra_filter

        first = self._list_all(method, params=dict(base_params), page=1, limit=50)
        items = list(first["items"])
        total = first["total"] or len(items)

        if total <= 50:
            return items

        offsets = list(range(50, total, 50))
        # har bir guruh = bitta batch so'rov (50 tagacha offset)
        groups = [offsets[i:i + 50] for i in range(0, len(offsets), 50)]

        def run_group(chunk):
            cmd = {
                f"c{off}": f"{method}?{self._encode_params({**base_params, 'start': off})}"
                for off in chunk
            }
            res = self._batch(cmd)
            sub = (res.get("result") or {})
            out = []
            for off in chunk:
                out.extend(sub.get(f"c{off}") or [])
            return out

        with ThreadPoolExecutor(max_workers=workers) as ex:
            for group_items in ex.map(run_group, groups):
                items.extend(group_items)

        return items

    @staticmethod
    def _first_value(field) -> str:
        if isinstance(field, list) and field:
            return field[0].get("VALUE", "") or ""
        return ""

    @classmethod
    def _normalize_deal(cls, item: dict) -> dict:
        return {
            "id": int(item.get("ID", 0)),
            "name": item.get("TITLE", "") or "",
            "price": float(item.get("OPPORTUNITY", 0) or 0),
            "stage_id": item.get("STAGE_ID", "") or "",
            "pipeline_id": item.get("CATEGORY_ID", 0) or 0,
            "responsible_user_id": int(item.get("ASSIGNED_BY_ID", 0) or 0),
            "created_at": item.get("DATE_CREATE"),
            "updated_at": item.get("DATE_MODIFY"),
            "closed_at": item.get("CLOSEDATE"),
            "is_closed": item.get("CLOSED") == "Y",
            "contact_id": item.get("CONTACT_ID"),
            "company_id": item.get("COMPANY_ID"),
            "raw": item,
        }

    @classmethod
    def _normalize_contact(cls, item: dict) -> dict:
        full_name = " ".join(filter(None, [
            item.get("NAME", ""),
            item.get("LAST_NAME", ""),
        ])).strip()
        return {
            "id": int(item.get("ID", 0)),
            "name": full_name or f"Contact #{item.get('ID', '')}",
            "first_name": item.get("NAME", "") or "",
            "last_name": item.get("LAST_NAME", "") or "",
            "phone": cls._first_value(item.get("PHONE")),
            "email": cls._first_value(item.get("EMAIL")),
            "company": item.get("COMPANY_TITLE", "") or "",
            "responsible_user_id": int(item.get("ASSIGNED_BY_ID", 0) or 0),
            "created_at": item.get("DATE_CREATE"),
            "updated_at": item.get("DATE_MODIFY"),
            "raw": item,
        }

    @classmethod
    def _normalize_bitrix_lead(cls, item: dict) -> dict:
        return {
            "id": int(item.get("ID", 0)),
            "name": item.get("TITLE", "") or "",
            "first_name": item.get("NAME", "") or "",
            "last_name": item.get("LAST_NAME", "") or "",
            "price": float(item.get("OPPORTUNITY", 0) or 0),
            "status_id": item.get("STATUS_ID", "") or "",
            "responsible_user_id": int(item.get("ASSIGNED_BY_ID", 0) or 0),
            "phone": cls._first_value(item.get("PHONE")),
            "email": cls._first_value(item.get("EMAIL")),
            "source_id": item.get("SOURCE_ID", "") or "",
            "created_at": item.get("DATE_CREATE"),
            "updated_at": item.get("DATE_MODIFY"),
            "raw": item,
        }

    @staticmethod
    def _since_filter(since):
        return {">=DATE_MODIFY": since} if since else None

    def get_all_deals(self, since=None) -> list:
        raw = self._fetch_all_raw("crm.deal.list", DEAL_SELECT,
                                  extra_filter=self._since_filter(since))
        return [self._normalize_deal(x) for x in raw]

    def get_all_contacts(self, since=None) -> list:
        raw = self._fetch_all_raw("crm.contact.list", CONTACT_SELECT,
                                  extra_filter=self._since_filter(since))
        return [self._normalize_contact(x) for x in raw]

    def get_all_bitrix_leads(self, since=None) -> list:
        raw = self._fetch_all_raw("crm.lead.list", LEAD_SELECT,
                                  extra_filter=self._since_filter(since))
        return [self._normalize_bitrix_lead(x) for x in raw]

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
                        "semantic": deal_stage_semantic(s.get("STATUS_ID", "")),
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
                            "semantic": deal_stage_semantic(s.get("STATUS_ID", "")),
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
            users = []
            start = 0
            while True:
                resp = requests.post(
                    f"{self.base_url}/user.get",
                    json={"ACTIVE": True, "start": start},
                    timeout=30,
                )
                resp.raise_for_status()
                body = resp.json()
                data = body.get("result")
                if not isinstance(data, list) or not data:
                    break

                for u in data:
                    users.append({
                        "id": int(u.get("ID", 0)),
                        "name": " ".join(filter(None, [
                            u.get("NAME", ""),
                            u.get("LAST_NAME", ""),
                        ])).strip() or f"User #{u.get('ID', '')}",
                        "email": u.get("EMAIL", "") or "",
                    })

                nxt = body.get("next")
                if nxt is None:
                    break
                start = nxt

            return users
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
                    "semantic": lead_status_semantic(s.get("SEMANTICS")),
                }
                for s in data
            ]
        except Exception as e:
            logger.error(f"Bitrix24 lead statuslarini olishda xatolik: {e}")
            return []
