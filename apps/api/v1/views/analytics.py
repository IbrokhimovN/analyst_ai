from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from apps.analytics.services import AnalyticsService

class SummaryView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        days = int(request.query_params.get('days', 30))
        source = request.query_params.get('source', None)
        service = AnalyticsService()
        data = service.get_summary(days=days, source=source)
        return Response(data)

class FunnelView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        pipeline_id = request.query_params.get('pipeline_id')
        source = request.query_params.get('source', None)
        service = AnalyticsService()
        data = service.get_funnel(pipeline_id=pipeline_id, source=source)
        return Response(data)

class ByManagerView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        days = int(request.query_params.get('days', 30))
        source = request.query_params.get('source', None)
        service = AnalyticsService()
        data = service.get_by_manager(days=days, source=source)
        return Response(data)

class LeadsTrendView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        days = int(request.query_params.get('days', 30))
        source = request.query_params.get('source', None)
        service = AnalyticsService()
        data = service.get_leads_trend(days=days, source=source)
        return Response(data)

class RevenueTrendView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        days = int(request.query_params.get('days', 30))
        source = request.query_params.get('source', None)
        service = AnalyticsService()
        data = service.get_revenue_trend(days=days, source=source)
        return Response(data)
