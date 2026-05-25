from rest_framework import generics, filters, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend

from apps.amocrm.models import Lead, Contact
from apps.crm.factory import get_crm_adapter
from ..serializers.leads import (
    LeadSerializer, LeadDetailSerializer,
    ContactSerializer,
    LeadCreateSerializer, ContactCreateSerializer,
    LeadUpdateSerializer, ContactUpdateSerializer,
)

class LeadListView(generics.ListCreateAPIView):
    serializer_class = LeadSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['pipeline_id', 'status_id', 'responsible_user_id', 'source']
    search_fields = ['name']
    ordering_fields = ['price', 'created_at', 'updated_at']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = Lead.objects.select_related('pipeline_ref', 'status_ref').all()
        return qs

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return LeadCreateSerializer
        return LeadSerializer

    def create(self, request, *args, **kwargs):
        serializer = LeadCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        source = data.pop('source', settings.DEFAULT_CRM)
        adapter = get_crm_adapter(source)

        try:
            result = adapter.create_lead(data)
        except Exception as e:
            return Response(
                {"error": f"CRM xatolik: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        lead = Lead.objects.create(
            amocrm_id=result["crm_id"],
            source=source,
            name=data.get("name", ""),
            price=data.get("price", 0),
            pipeline_id=data.get("pipeline_id"),
            raw_data=result.get("raw", {}),
        )

        return Response(LeadSerializer(lead).data, status=status.HTTP_201_CREATED)

class LeadDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Lead.objects.select_related('pipeline_ref', 'status_ref').prefetch_related('contacts')
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return LeadUpdateSerializer
        return LeadDetailSerializer

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = LeadUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if not data:
            return Response(LeadDetailSerializer(instance).data)

        adapter = get_crm_adapter(instance.source)
        try:
            adapter.update_lead(instance.amocrm_id, data)
        except Exception as e:
            return Response(
                {"error": f"CRM xatolik: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if 'name' in data:
            instance.name = data['name']
        if 'price' in data:
            instance.price = data['price']
        if 'pipeline_id' in data:
            instance.pipeline_id = data['pipeline_id']
        instance.save()

        return Response(LeadDetailSerializer(instance).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        adapter = get_crm_adapter(instance.source)
        try:
            adapter.delete_lead(instance.amocrm_id)
        except Exception as e:
            return Response(
                {"error": f"CRM xatolik: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class ContactListView(generics.ListCreateAPIView):
    serializer_class = ContactSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['source']
    search_fields = ['name', 'phone', 'email']
    ordering_fields = ['name', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        return Contact.objects.all()

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ContactCreateSerializer
        return ContactSerializer

    def create(self, request, *args, **kwargs):
        serializer = ContactCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        source = data.pop('source', settings.DEFAULT_CRM)
        adapter = get_crm_adapter(source)

        try:
            result = adapter.create_contact(data)
        except Exception as e:
            return Response(
                {"error": f"CRM xatolik: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        contact = Contact.objects.create(
            amocrm_id=result["crm_id"],
            source=source,
            name=data.get("name", ""),
            phone=data.get("phone", ""),
            email=data.get("email", ""),
            company=data.get("company", ""),
            raw_data=result.get("raw", {}),
        )

        return Response(ContactSerializer(contact).data, status=status.HTTP_201_CREATED)

class ContactDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Contact.objects.all()
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ContactUpdateSerializer
        return ContactSerializer

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = ContactUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if not data:
            return Response(ContactSerializer(instance).data)

        adapter = get_crm_adapter(instance.source)
        try:
            adapter.update_contact(instance.amocrm_id, data)
        except Exception as e:
            return Response(
                {"error": f"CRM xatolik: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if 'name' in data:
            instance.name = data['name']
        if 'phone' in data:
            instance.phone = data['phone']
        if 'email' in data:
            instance.email = data['email']
        if 'company' in data:
            instance.company = data['company']
        instance.save()

        return Response(ContactSerializer(instance).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        adapter = get_crm_adapter(instance.source)
        try:
            adapter.delete_contact(instance.amocrm_id)
        except Exception as e:
            return Response(
                {"error": f"CRM xatolik: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
