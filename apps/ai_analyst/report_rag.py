"""AI hisobotlarini RAG indeksiga qo'shish — tarixiy kontekst uchun.

Shu orqali keyinroq "o'tgan hafta nima degandik", "may oyida holat qanday edi"
kabi savollarga eski hisobotlardan javob berish mumkin.
"""
import logging

logger = logging.getLogger(__name__)


def index_report(report) -> int:
    from .rag import add_texts

    header = f"{report.title} — {report.created_at:%Y-%m-%d}"
    text = f"{header}\n\n{report.content}"
    metadata = {
        'source': header,
        'kind': 'report',
        'report_id': report.id,
        'report_kind': report.kind,
        'crm_source': report.source,
    }
    n = add_texts([text], [metadata])
    logger.info('AI hisobot #%s RAG indeksiga qo\'shildi', report.id)
    return n
