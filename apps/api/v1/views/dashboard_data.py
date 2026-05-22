"""Dinamik dashboard endpointi.

Dashboard sahifasini to'liq qayta yuklamasdan yangilash uchun ishlatiladi.
``DashboardView`` bilan bir xil kontekstni quradi, lekin butun sahifa
o'rniga faqat yangilanadigan qismni — ``dashboard/_dash_body.html``
partial'ini — render qilib, HTML matn sifatida qaytaradi.

Frontend (``static/js/dashboard_dynamic.js``) bu HTML ni ``#dash-root``
ichiga joylashtiradi va grafiklarni qayta chizadi.

Endpoint:
  * ``GET /api/v1/dashboard/data/?period=&source=``
"""
import logging

from django.template.loader import render_to_string
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.dashboard.views import build_dashboard_context, clean_period, clean_source

logger = logging.getLogger(__name__)


class DashboardDataView(APIView):
    """Dashboard kartalarini AJAX bilan yangilash uchun HTML fragment qaytaradi."""
    permission_classes = [AllowAny]

    def get(self, request):
        # So'rov parametrlarini xavfsiz normallashtiramiz.
        source = clean_source(request.query_params.get('source'))
        period = clean_period(request.query_params.get('period'))

        try:
            ctx = build_dashboard_context(source, period)
            # Faqat yangilanadigan qism — _dash_body.html partial.
            html = render_to_string('dashboard/_dash_body.html', ctx,
                                    request=request)
        except Exception as exc:  # noqa: BLE001
            logger.error('Dashboard data render xatolik: %s', exc)
            return Response({'error': str(exc)}, status=500)

        return Response({
            'html': html,
            'period': period or 'all',
            'source': source or 'all',
            'updated_at': timezone.localtime().strftime('%H:%M:%S'),
        })
