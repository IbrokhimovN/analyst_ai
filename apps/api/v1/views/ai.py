"""AI API endpointlari — LangChain RAG, Agent va Memory.

Endpointlar:

  * ``POST   /api/v1/ai/rag/upload/``      — PDF/Excel hujjat yuklash (RAG).
  * ``GET    /api/v1/ai/rag/documents/``   — yuklangan hujjatlar ro'yxati.
  * ``DELETE /api/v1/ai/rag/documents/<id>/`` — hujjatni o'chirish.
  * ``POST   /api/v1/ai/chat/``            — RAG + Memory bilan savol-javob.
  * ``GET    /api/v1/ai/chat/history/``    — menejer suhbat tarixi.
  * ``DELETE /api/v1/ai/chat/history/``    — menejer suhbat tarixini tozalash.
  * ``POST   /api/v1/ai/agent/analyze/``   — Agent orqali avtomatik tahlil.
  * ``GET    /api/v1/ai/managers/``        — menejerlar ro'yxati (selector uchun).
  * ``GET    /api/v1/ai/report/weekly/``   — haftalik AI hisobot (eski).
"""
import logging
import os
import re

from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai_analyst import agent as agent_mod
from apps.ai_analyst import memory as memory_mod
from apps.ai_analyst import rag as rag_mod
from apps.ai_analyst.models import ChatMessage, KnowledgeDocument
from apps.ai_analyst.services import generate_weekly_report
from apps.amocrm.models import User as AmoCRMUser

logger = logging.getLogger(__name__)

# RAG uchun ruxsat etilgan fayl kengaytmalari.
ALLOWED_EXTENSIONS = {'.pdf', '.xlsx', '.xls', '.csv'}


def _clean_source(value):
    """``source`` query/body qiymatini normallashtiradi ('all' → None)."""
    if value in ('amocrm', 'bitrix'):
        return value
    return None


# Maxsus sana oralig'i: "range:YYYY-MM-DD:YYYY-MM-DD".
_PERIOD_RANGE_RE = re.compile(r'^range:\d{4}-\d{2}-\d{2}:\d{4}-\d{2}-\d{2}$')


def _clean_period(value):
    """``period`` query/body qiymatini normallashtiradi (yaroqsiz → None).

    Ruxsat etilgan: 'day' | 'week' | 'month' yoki maxsus sana oralig'i
    "range:YYYY-MM-DD:YYYY-MM-DD".
    """
    if value in ('day', 'week', 'month'):
        return value
    if value and _PERIOD_RANGE_RE.match(value):
        return value
    return None


# =============================================================================
# RAG — hujjat yuklash va boshqarish
# =============================================================================

class RAGUploadView(APIView):
    """PDF yoki Excel hujjatni yuklab, FAISS vektor omboriga qo'shadi."""
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        upload = request.FILES.get('file')
        if not upload:
            return Response({'error': 'Fayl yuborilmadi.'},
                            status=status.HTTP_400_BAD_REQUEST)

        ext = os.path.splitext(upload.name)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            return Response(
                {'error': f'Qo\'llab-quvvatlanmaydigan format: {ext}. '
                          f'Ruxsat: PDF, Excel, CSV.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Hujjatni saqlaymiz va darhol qayta ishlaymiz.
        doc = KnowledgeDocument.objects.create(
            title=request.data.get('title') or upload.name,
            file=upload,
            file_type=ext.lstrip('.'),
            status='processing',
        )
        try:
            chunk_count = rag_mod.add_document(doc)
            doc.chunk_count = chunk_count
            doc.status = 'ready'
            doc.save(update_fields=['chunk_count', 'status'])
        except Exception as exc:  # noqa: BLE001
            logger.error('RAG hujjat qayta ishlashda xatolik: %s', exc)
            doc.status = 'error'
            doc.error = str(exc)
            doc.save(update_fields=['status', 'error'])
            return Response({'error': f'Hujjatni qayta ishlashda xatolik: {exc}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            'id': doc.id,
            'title': doc.title,
            'file_type': doc.file_type,
            'chunk_count': doc.chunk_count,
            'status': doc.status,
        }, status=status.HTTP_201_CREATED)


class RAGDocumentsView(APIView):
    """Yuklangan RAG hujjatlari ro'yxati."""
    permission_classes = [AllowAny]

    def get(self, request):
        docs = [
            {
                'id': d.id,
                'title': d.title,
                'file_type': d.file_type,
                'chunk_count': d.chunk_count,
                'status': d.status,
                'error': d.error,
                'uploaded_at': d.uploaded_at.isoformat(),
            }
            for d in KnowledgeDocument.objects.all()
        ]
        return Response({'documents': docs, 'count': len(docs)})


class RAGDocumentDetailView(APIView):
    """Bitta RAG hujjatini o'chirish (indeks qayta quriladi)."""
    permission_classes = [AllowAny]

    def delete(self, request, pk):
        try:
            doc = KnowledgeDocument.objects.get(pk=pk)
        except KnowledgeDocument.DoesNotExist:
            return Response({'error': 'Hujjat topilmadi.'},
                            status=status.HTTP_404_NOT_FOUND)

        doc.file.delete(save=False)  # diskdagi faylni o'chirish
        doc.delete()
        # FAISS indeksini qolgan hujjatlardan qayta quramiz.
        rag_mod.rebuild_index()
        return Response({'status': 'deleted'})


# =============================================================================
# Chat — RAG + Memory
# =============================================================================

class AIChatView(APIView):
    """RAG va Memory bilan savol-javob.

    Hujjatlar yuklangan bo'lsa javob ularga asoslanadi, aks holda oddiy
    Claude suhbati. Har ikkala holatda menejerning suhbat tarixi hisobga
    olinadi (``manager_id`` bo'yicha).
    """
    permission_classes = [AllowAny]

    def post(self, request):
        question = (request.data.get('message') or
                    request.data.get('question') or '').strip()
        if not question:
            return Response({'error': 'Savol bo\'sh bo\'lmasligi kerak!'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            manager_id = int(request.data.get('manager_id') or 0)
        except (TypeError, ValueError):
            manager_id = 0

        try:
            result = rag_mod.answer_question(question, manager_id=manager_id)
        except Exception as exc:  # noqa: BLE001
            logger.error('AI chat xatolik: %s', exc)
            return Response({'error': str(exc)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            'question': question,
            'answer': result['answer'],
            'sources': result['sources'],
            'used_rag': result['used_rag'],
        })


class ChatHistoryView(APIView):
    """Menejer suhbat tarixini olish yoki tozalash (Memory)."""
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            manager_id = int(request.query_params.get('manager_id') or 0)
        except (TypeError, ValueError):
            manager_id = 0
        return Response({
            'manager_id': manager_id,
            'messages': memory_mod.history_messages(manager_id),
        })

    def delete(self, request):
        try:
            manager_id = int(request.query_params.get('manager_id') or 0)
        except (TypeError, ValueError):
            manager_id = 0
        deleted = memory_mod.clear_history(manager_id)
        return Response({'status': 'cleared', 'deleted': deleted})


# =============================================================================
# Agent — avtomatik tahlil
# =============================================================================

class AgentAnalyzeView(APIView):
    """AgentExecutor orqali dashboard ma'lumotlarini avtomatik tahlil qiladi."""
    permission_classes = [AllowAny]

    def post(self, request):
        source = _clean_source(request.data.get('source') or
                               request.query_params.get('source'))
        try:
            result = agent_mod.run_agent_analysis(source=source)
        except Exception as exc:  # noqa: BLE001
            logger.error('Agent tahlil xatolik: %s', exc)
            return Response({'error': str(exc)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            'analysis': result['analysis'],
            'steps': result['steps'],
        })


# =============================================================================
# Har-karta AI — dashboard kartalarini tahlil qilish va ko'rinishini
# foydalanuvchi istagiga moslab o'zgartirish (dinamik dashboard).
# =============================================================================

class CardAnalyzeView(APIView):
    """Bitta dashboard kartasini LangChain agenti orqali tahlil qiladi.

    POST body: ``{card, source, period}``.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        card = (request.data.get('card') or '').strip()
        if card not in agent_mod.CARD_KEYS:
            return Response({'error': f'Noma\'lum karta: {card}'},
                            status=status.HTTP_400_BAD_REQUEST)
        source = _clean_source(request.data.get('source'))
        period = _clean_period(request.data.get('period'))

        try:
            result = agent_mod.run_card_analysis(card, source=source, period=period)
        except Exception as exc:  # noqa: BLE001
            logger.error('Karta tahlil xatolik (%s): %s', card, exc)
            return Response({'error': str(exc)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            'card': card,
            'analysis': result['analysis'],
            'steps': result['steps'],
        })


class CardRenderView(APIView):
    """Foydalanuvchi istagiga ko'ra kartaning AI view-spec'ini qaytaradi.

    AI HTML yozmaydi — faqat xavfsiz JSON konfiguratsiya (chart turi,
    metrik, saralash, limit) qaytaradi, frontend shu asosda chizadi.

    POST body: ``{card, instruction, source, period}``.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        card = (request.data.get('card') or '').strip()
        if card not in agent_mod.CARD_KEYS:
            return Response({'error': f'Noma\'lum karta: {card}'},
                            status=status.HTTP_400_BAD_REQUEST)

        instruction = (request.data.get('instruction') or '').strip()
        if not instruction:
            return Response({'error': 'Istak matni bo\'sh bo\'lmasligi kerak.'},
                            status=status.HTTP_400_BAD_REQUEST)

        source = _clean_source(request.data.get('source'))
        period = _clean_period(request.data.get('period'))

        try:
            spec = agent_mod.build_card_view_spec(
                card, instruction, source=source, period=period)
        except Exception as exc:  # noqa: BLE001
            logger.error('Karta view-spec xatolik (%s): %s', card, exc)
            return Response({'error': str(exc)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'card': card, 'spec': spec})


# =============================================================================
# Yordamchi endpointlar
# =============================================================================

class ManagersListView(APIView):
    """Menejerlar ro'yxati — chat'da suhbat egasini tanlash uchun."""
    permission_classes = [AllowAny]

    def get(self, request):
        managers = [
            {'id': u.amocrm_id, 'name': u.name}
            for u in AmoCRMUser.objects.all().order_by('name')
        ]
        return Response({'managers': managers})


class WeeklyReportView(APIView):
    """Haftalik AI hisobot endpointi (dashboard'dagi "AI tahlil" tugmasi)."""
    permission_classes = [AllowAny]

    def get(self, request):
        source = _clean_source(request.query_params.get('source'))
        report = generate_weekly_report(source=source)
        return Response({'report': report})
