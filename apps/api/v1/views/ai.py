import logging
import os
import re

from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from django.http import HttpResponse

from apps.ai_analyst import agent as agent_mod
from apps.ai_analyst import memory as memory_mod
from apps.ai_analyst import rag as rag_mod
from apps.ai_analyst import tts as tts_mod
from apps.ai_analyst.models import ChatMessage, KnowledgeDocument
from apps.ai_analyst.services import generate_weekly_report
from apps.amocrm.models import User as AmoCRMUser

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'.pdf', '.xlsx', '.xls', '.csv'}

def _clean_source(value):
    if value in ('amocrm', 'bitrix'):
        return value
    return None

_PERIOD_RANGE_RE = re.compile(r'^range:\d{4}-\d{2}-\d{2}:\d{4}-\d{2}-\d{2}$')

def _clean_period(value):
    if value in ('day', 'week', 'month'):
        return value
    if value and _PERIOD_RANGE_RE.match(value):
        return value
    return None

class RAGUploadView(APIView):
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
        except Exception as exc:
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
    permission_classes = [AllowAny]

    def delete(self, request, pk):
        try:
            doc = KnowledgeDocument.objects.get(pk=pk)
        except KnowledgeDocument.DoesNotExist:
            return Response({'error': 'Hujjat topilmadi.'},
                            status=status.HTTP_404_NOT_FOUND)

        doc.file.delete(save=False)
        doc.delete()
        rag_mod.rebuild_index()
        return Response({'status': 'deleted'})

class AIChatView(APIView):
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

        source = _clean_source(request.data.get('source') or
                               request.query_params.get('source'))
        period = _clean_period(request.data.get('period') or
                               request.query_params.get('period'))

        try:
            if rag_mod.index_exists():
                result = rag_mod.answer_question(question, manager_id=manager_id)
                return Response({
                    'question': question,
                    'answer': result['answer'],
                    'sources': result['sources'],
                    'used_rag': result['used_rag'],
                })
            is_voice = bool(request.data.get('is_voice'))
            result = agent_mod.chat_with_agent(
                question, manager_id=manager_id,
                source=source, period=period, is_voice=is_voice,
            )
        except Exception as exc:
            logger.error('AI chat xatolik: %s', exc)
            return Response({'error': str(exc)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            'question': question,
            'answer': result['answer'],
            'sources': result.get('sources', []),
            'used_rag': result.get('used_rag', False),
            'steps': result.get('steps', []),
            'charts': result.get('charts', []),
            'commands': result.get('commands', []),
        })

class ChatHistoryView(APIView):
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

class AgentAnalyzeView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        source = _clean_source(request.data.get('source') or
                               request.query_params.get('source'))
        try:
            result = agent_mod.run_agent_analysis(source=source)
        except Exception as exc:
            logger.error('Agent tahlil xatolik: %s', exc)
            return Response({'error': str(exc)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            'analysis': result['analysis'],
            'steps': result['steps'],
        })

class CardAnalyzeView(APIView):
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
        except Exception as exc:
            logger.error('Karta tahlil xatolik (%s): %s', card, exc)
            return Response({'error': str(exc)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            'card': card,
            'analysis': result['analysis'],
            'steps': result['steps'],
        })

class CardRenderView(APIView):
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
        except Exception as exc:
            logger.error('Karta view-spec xatolik (%s): %s', card, exc)
            return Response({'error': str(exc)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'card': card, 'spec': spec})

class ManagersListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        managers = [
            {'id': u.amocrm_id, 'name': u.name}
            for u in AmoCRMUser.objects.all().order_by('name')
        ]
        return Response({'managers': managers})

class WeeklyReportView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        source = _clean_source(request.query_params.get('source'))
        report = generate_weekly_report(source=source)
        return Response({'report': report})


class TTSView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'tts'

    def post(self, request):
        text = (request.data.get('text') or '').strip()
        if not text:
            return Response({'error': 'Matn kiritilmagan.'},
                            status=status.HTTP_400_BAD_REQUEST)
        voice = request.data.get('voice') or tts_mod.DEFAULT_VOICE
        audio = tts_mod.synthesize(text, voice=voice)
        if not audio:
            return Response({'error': 'TTS yaratib bo\'lmadi.'},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)
        response = HttpResponse(audio, content_type='audio/mpeg')
        response['Content-Length'] = str(len(audio))
        response['Cache-Control'] = 'private, max-age=604800'
        return response


class GeneratedReportsView(APIView):
    """Avto-tuzilgan AI hisobotlar ro'yxati (kunlik/haftalik)."""
    permission_classes = [AllowAny]

    def get(self, request):
        from apps.ai_analyst.models import GeneratedReport
        qs = GeneratedReport.objects.all()
        kind = request.query_params.get('kind')
        if kind in ('daily', 'weekly'):
            qs = qs.filter(kind=kind)
        source = _clean_source(request.query_params.get('source'))
        if source:
            qs = qs.filter(source=source)
        rows = list(qs[:20].values('id', 'kind', 'source', 'title',
                                    'content', 'created_at'))
        return Response({'reports': rows})


class MetricAlertsView(APIView):
    """Metrik alertlar ro'yxati; PATCH bilan o'qilgan deb belgilash."""
    permission_classes = [AllowAny]

    def get(self, request):
        from apps.ai_analyst.models import MetricAlert
        qs = MetricAlert.objects.all()
        if request.query_params.get('unread') == '1':
            qs = qs.filter(is_read=False)
        rows = list(qs[:50].values('id', 'metric', 'source', 'severity',
                                   'message', 'value', 'threshold',
                                   'is_read', 'created_at'))
        return Response({'alerts': rows,
                         'unread': MetricAlert.objects.filter(
                             is_read=False).count()})

    def patch(self, request):
        from apps.ai_analyst.models import MetricAlert
        alert_id = request.data.get('id')
        if alert_id:
            MetricAlert.objects.filter(id=alert_id).update(is_read=True)
        else:
            MetricAlert.objects.filter(is_read=False).update(is_read=True)
        return Response({'status': 'ok'})


class ChatFeedbackView(APIView):
    """AI javobiga 👍/👎 baho berish."""
    permission_classes = [AllowAny]

    def post(self, request):
        msg_id = request.data.get('message_id')
        value = (request.data.get('feedback') or '').strip()
        if value not in ('up', 'down', ''):
            return Response({'error': 'feedback up|down bo\'lishi kerak.'},
                            status=status.HTTP_400_BAD_REQUEST)
        updated = ChatMessage.objects.filter(id=msg_id, role='ai').update(
            feedback=value)
        if not updated:
            return Response({'error': 'Xabar topilmadi.'},
                            status=status.HTTP_404_NOT_FOUND)
        return Response({'status': 'ok', 'feedback': value})


class AnalyticsExportView(APIView):
    """Analitikani Excel (.xlsx) faylga eksport qiladi."""
    permission_classes = [AllowAny]

    def get(self, request):
        from apps.ai_analyst.export import build_analytics_workbook
        source = _clean_source(request.query_params.get('source'))
        period = _clean_period(request.query_params.get('period'))
        data = build_analytics_workbook(source=source, period=period)
        fname = f'analitika_{source or "all"}.xlsx'
        response = HttpResponse(
            data,
            content_type=('application/vnd.openxmlformats-officedocument'
                          '.spreadsheetml.sheet'))
        response['Content-Disposition'] = f'attachment; filename="{fname}"'
        return response
