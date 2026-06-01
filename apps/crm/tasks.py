import logging
from datetime import datetime, timedelta, timezone as tz

from celery import shared_task
from dateutil import parser as dateparser
from django.db.models import Max
from django.utils import timezone

logger = logging.getLogger(__name__)

# Bitrix foydalanuvchi ID'lariga qo'shiladigan offset — AmoCRM userlari bilan
# to'qnashmasligi uchun (Lead.responsible_user_id va User.amocrm_id ikkalasida bir xil).
USER_ID_OFFSET = 1000000

# Incremental sync chegarasiga qancha overlap qo'shish (chegaradagi
# yozuvlarni o'tkazib yubormaslik uchun; upsert dublikatni yutadi).
_SYNC_OVERLAP = timedelta(minutes=5)


def _incremental_since(last_dt):
    """DB'dagi oxirgi updated_at'dan Bitrix filtri uchun sana qatori (yoki None)."""
    if not last_dt:
        return None
    return (last_dt - _SYNC_OVERLAP).isoformat()


def _parse_bitrix_date(date_str):
    if not date_str:
        return None
    # Tezkor yo'l: Bitrix ISO 8601 qaytaradi (2026-06-01T06:26:33+03:00).
    # fromisoformat C-darajada, dateutil.parse'dan ~20x tez.
    try:
        return datetime.fromisoformat(date_str)
    except (ValueError, TypeError):
        try:
            return dateparser.parse(date_str)
        except (ValueError, TypeError):
            return None


def _stable_hash(value) -> int:
    """Process-dan mustaqil barqaror hash (in-progress status_id uchun)."""
    import hashlib
    h = hashlib.md5(str(value or "").encode("utf-8")).hexdigest()
    return int(h[:8], 16) % 100000


def _status_id_for_semantic(semantic, key):
    """Bitrix bosqich semantikasini dashboard status_id'siga o'giradi.
    won -> 142, lost -> 143, qolgani -> barqaror hash."""
    from apps.analytics.services import WON_STATUS_ID, LOST_STATUS_ID
    if semantic == "won":
        return WON_STATUS_ID
    if semantic == "lost":
        return LOST_STATUS_ID
    return _stable_hash(key)


def _build_deal_stage_map(adapter):
    """{STAGE_ID: {'status_id', 'name', 'semantic'}} — barcha kategoriya bosqichlari."""
    stage_map = {}
    for cat in adapter.get_pipelines():
        for s in cat.get("statuses", []):
            sid = s.get("id", "")
            semantic = s.get("semantic", "progress")
            stage_map[sid] = {
                "status_id": _status_id_for_semantic(semantic, sid),
                "name": s.get("name", ""),
                "semantic": semantic,
            }
    return stage_map


def _resolve_deal_stage(stage_map, stage_id):
    """stage_map'da bo'lmasa STAGE_ID nomi bo'yicha (WON/LOSE) tasniflaydi."""
    if stage_id in stage_map:
        return stage_map[stage_id]
    from apps.crm.adapters.bitrix import deal_stage_semantic
    semantic = deal_stage_semantic(stage_id)
    return {
        "status_id": _status_id_for_semantic(semantic, stage_id),
        "name": "",
        "semantic": semantic,
    }


def _build_lead_status_map(adapter):
    """{STATUS_ID: {'status_id', 'name', 'semantic'}} — crm.lead statuslari (SEMANTICS)."""
    status_map = {}
    for s in adapter.get_lead_statuses():
        sid = s.get("id", "")
        semantic = s.get("semantic", "progress")
        status_map[sid] = {
            "status_id": _status_id_for_semantic(semantic, sid),
            "name": s.get("name", ""),
            "semantic": semantic,
        }
    return status_map


def _offset_user_id(raw):
    """Bitrix user ID'ni offset bilan (User.amocrm_id bilan mos kelishi uchun)."""
    raw = raw or 0
    return (USER_ID_OFFSET + raw) if raw else None


@shared_task(bind=True, max_retries=3)
def sync_bitrix_users(self):
    from apps.crm.adapters.bitrix import Bitrix24Adapter
    from apps.amocrm.models import User

    try:
        adapter = Bitrix24Adapter()
        users = adapter.get_users()

        objs = [
            User(
                amocrm_id=USER_ID_OFFSET + u["id"],
                name=u.get("name") or f"User #{u['id']}",
                email=u.get("email") or "",
                raw_data=u,
            )
            for u in users if u.get("id")
        ]

        if objs:
            User.objects.bulk_create(
                objs,
                update_conflicts=True,
                unique_fields=["amocrm_id"],
                update_fields=["name", "email", "raw_data"],
                batch_size=1000,
            )

        logger.info(f"Bitrix24: {len(objs)} foydalanuvchi sinxronlandi")
        return {"synced": len(objs)}

    except Exception as exc:
        logger.error(f"Bitrix24 foydalanuvchi sinxronlashda xatolik: {exc}")
        self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def sync_bitrix_deals(self, full=False):
    from apps.crm.adapters.bitrix import Bitrix24Adapter
    from apps.amocrm.models import Lead, Pipeline

    try:
        adapter = Bitrix24Adapter()
        stage_map = _build_deal_stage_map(adapter)
        pipelines_by_id = {
            p.amocrm_id: p
            for p in Pipeline.objects.filter(amocrm_id__gte=USER_ID_OFFSET)
        }

        since = None
        if not full:
            last = Lead.objects.filter(
                source="bitrix", amocrm_id__lt=2000000,
            ).aggregate(m=Max("updated_at"))["m"]
            since = _incremental_since(last)
        items = adapter.get_all_deals(since=since)

        objs = []
        for item in items:
            stage = _resolve_deal_stage(stage_map, item.get("stage_id"))
            cat_id = int(item.get("pipeline_id") or 0)
            objs.append(Lead(
                amocrm_id=1000000 + item["id"],
                source="bitrix",
                name=item.get("name") or "",
                price=item.get("price") or 0,
                status_id=stage["status_id"],
                pipeline_id=cat_id,
                pipeline_ref=pipelines_by_id.get(USER_ID_OFFSET + cat_id),
                responsible_user_id=_offset_user_id(item.get("responsible_user_id")),
                loss_reason=(stage["name"] if stage["semantic"] == "lost" else ""),
                created_at=_parse_bitrix_date(item.get("created_at")),
                updated_at=_parse_bitrix_date(item.get("updated_at")),
                closed_at=_parse_bitrix_date(item.get("closed_at")),
                raw_data=item.get("raw", item),
            ))

        Lead.objects.bulk_create(
            objs,
            update_conflicts=True,
            unique_fields=["amocrm_id"],
            update_fields=[
                "source", "name", "price", "status_id", "pipeline_id",
                "pipeline_ref", "responsible_user_id", "loss_reason",
                "created_at", "updated_at", "closed_at", "raw_data",
            ],
            batch_size=10000,
        )

        mode = "full" if full else "incremental"
        logger.info(f"Bitrix24: {len(objs)} deal sinxronlandi ({mode})")
        return {"synced": len(objs)}

    except Exception as exc:
        logger.error(f"Bitrix24 deal sinxronlashda xatolik: {exc}")
        self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def sync_bitrix_contacts(self, full=False):
    from apps.crm.adapters.bitrix import Bitrix24Adapter
    from apps.amocrm.models import Contact

    try:
        adapter = Bitrix24Adapter()
        since = None
        if not full:
            last = Contact.objects.filter(
                source="bitrix",
            ).aggregate(m=Max("updated_at"))["m"]
            since = _incremental_since(last)
        items = adapter.get_all_contacts(since=since)

        objs = [
            Contact(
                amocrm_id=1000000 + item["id"],
                source="bitrix",
                name=item.get("name") or "",
                first_name=item.get("first_name") or "",
                last_name=item.get("last_name") or "",
                phone=item.get("phone") or "",
                email=item.get("email") or "",
                company=item.get("company") or "",
                responsible_user_id=_offset_user_id(item.get("responsible_user_id")),
                created_at=_parse_bitrix_date(item.get("created_at")),
                updated_at=_parse_bitrix_date(item.get("updated_at")),
                raw_data=item.get("raw", item),
            )
            for item in items
        ]

        Contact.objects.bulk_create(
            objs,
            update_conflicts=True,
            unique_fields=["amocrm_id"],
            update_fields=[
                "source", "name", "first_name", "last_name", "phone",
                "email", "company", "responsible_user_id",
                "created_at", "updated_at", "raw_data",
            ],
            batch_size=10000,
        )

        mode = "full" if full else "incremental"
        logger.info(f"Bitrix24: {len(objs)} kontakt sinxronlandi ({mode})")
        return {"synced": len(objs)}

    except Exception as exc:
        logger.error(f"Bitrix24 kontakt sinxronlashda xatolik: {exc}")
        self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def sync_bitrix_leads(self, full=False):
    from apps.crm.adapters.bitrix import Bitrix24Adapter
    from apps.amocrm.models import Lead

    try:
        adapter = Bitrix24Adapter()
        status_map = _build_lead_status_map(adapter)

        since = None
        if not full:
            last = Lead.objects.filter(
                source="bitrix", amocrm_id__gte=2000000,
            ).aggregate(m=Max("updated_at"))["m"]
            since = _incremental_since(last)
        items = adapter.get_all_bitrix_leads(since=since)

        objs = []
        for item in items:
            st = status_map.get(item.get("status_id"))
            if st is None:
                st = {
                    "status_id": _stable_hash(item.get("status_id")),
                    "name": "",
                    "semantic": "progress",
                }
            objs.append(Lead(
                amocrm_id=2000000 + item["id"],
                source="bitrix",
                name=item.get("name") or "",
                price=item.get("price") or 0,
                status_id=st["status_id"],
                responsible_user_id=_offset_user_id(item.get("responsible_user_id")),
                loss_reason=(st["name"] if st["semantic"] == "lost" else ""),
                created_at=_parse_bitrix_date(item.get("created_at")),
                updated_at=_parse_bitrix_date(item.get("updated_at")),
                raw_data=item.get("raw", item),
            ))

        Lead.objects.bulk_create(
            objs,
            update_conflicts=True,
            unique_fields=["amocrm_id"],
            update_fields=[
                "source", "name", "price", "status_id",
                "responsible_user_id", "loss_reason",
                "created_at", "updated_at", "raw_data",
            ],
            batch_size=10000,
        )

        mode = "full" if full else "incremental"
        logger.info(f"Bitrix24: {len(objs)} lead sinxronlandi ({mode})")
        return {"synced": len(objs)}

    except Exception as exc:
        logger.error(f"Bitrix24 lead sinxronlashda xatolik: {exc}")
        self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def sync_bitrix_pipelines(self):
    from apps.crm.adapters.bitrix import Bitrix24Adapter
    from apps.amocrm.models import Pipeline, PipelineStatus

    try:
        adapter = Bitrix24Adapter()
        pipelines = adapter.get_pipelines()
        total = 0

        for p in pipelines:
            internal_pipeline_id = 1000000 + int(p["id"])

            pipeline, _ = Pipeline.objects.update_or_create(
                amocrm_id=internal_pipeline_id,
                defaults={
                    "name": f"[Bitrix] {p['name']}",
                    "sort": p.get("sort", 0),
                    "is_main": p.get("is_main", False),
                    "raw_data": p.get("raw", {}),
                }
            )

            for s in p.get("statuses", []):
                # Lead.status_id bilan mos kelishi uchun aynan shu mapping ishlatiladi.
                status_id = _status_id_for_semantic(s.get("semantic", "progress"), s.get("id", ""))
                PipelineStatus.objects.update_or_create(
                    amocrm_id=status_id,
                    pipeline=pipeline,
                    defaults={
                        "name": s.get("name", ""),
                        "sort": s.get("sort", 0),
                        "color": s.get("color", ""),
                        "raw_data": s,
                    }
                )

            total += 1

        logger.info(f"Bitrix24: {total} pipeline sinxronlandi")

    except Exception as exc:
        logger.error(f"Bitrix24 pipeline sinxronlashda xatolik: {exc}")
        self.retry(exc=exc, countdown=60)


@shared_task
def sync_bitrix_all():
    from django.conf import settings

    if not getattr(settings, 'BITRIX_WEBHOOK_URL', ''):
        logger.warning("BITRIX_WEBHOOK_URL sozlanmagan — sync o'tkazilmaydi")
        return

    # Userlar va pipelinelar avval (deal sync ulardan foydalanadi).
    sync_bitrix_users.delay()
    sync_bitrix_pipelines.delay()
    sync_bitrix_deals.delay()
    sync_bitrix_contacts.delay()
    sync_bitrix_leads.delay()
