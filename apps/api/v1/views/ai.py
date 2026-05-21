from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status

from apps.ai_analyst.services import analyze_data, generate_weekly_report, get_context_data


class AIChatView(APIView):
    """AI ga savol yuborish endpointi."""
    permission_classes = [AllowAny]

    def post(self, request):
        question = request.data.get('message', '').strip()
        source = request.data.get('source') or request.query_params.get('source')
        if source == 'all':
            source = None

        if not question:
            return Response(
                {"error": "Savol bo'sh bo'lmasligi kerak!"},
                status=status.HTTP_400_BAD_REQUEST
            )

        context_data = get_context_data(source=source)
        answer = analyze_data(question, context_data, source=source)

        return Response({
            "question": question,
            "answer": answer,
        })


class WeeklyReportView(APIView):
    """Haftalik AI hisobot endpointi."""
    permission_classes = [AllowAny]

    def get(self, request):
        source = request.query_params.get('source')
        if source == 'all':
            source = None
        report = generate_weekly_report(source=source)
        return Response({
            "report": report,
        })

