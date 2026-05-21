from rest_framework import serializers
from apps.amocrm.models import Lead, Contact


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = [
            'id', 'amocrm_id', 'source', 'name', 'first_name', 'last_name',
            'company', 'phone', 'email', 'created_at', 'updated_at',
        ]


class LeadSerializer(serializers.ModelSerializer):
    pipeline_name = serializers.CharField(source='pipeline_ref.name', default='', read_only=True)
    status_name = serializers.CharField(source='status_ref.name', default='', read_only=True)

    class Meta:
        model = Lead
        fields = [
            'id', 'amocrm_id', 'source', 'name', 'price',
            'status_id', 'status_name',
            'pipeline_id', 'pipeline_name',
            'responsible_user_id', 'loss_reason',
            'created_at', 'updated_at', 'closed_at',
        ]


class LeadDetailSerializer(serializers.ModelSerializer):
    pipeline_name = serializers.CharField(source='pipeline_ref.name', default='', read_only=True)
    status_name = serializers.CharField(source='status_ref.name', default='', read_only=True)
    contacts = ContactSerializer(many=True, read_only=True)

    class Meta:
        model = Lead
        fields = [
            'id', 'amocrm_id', 'source', 'name', 'price',
            'status_id', 'status_name',
            'pipeline_id', 'pipeline_name',
            'responsible_user_id', 'loss_reason',
            'contacts', 'raw_data',
            'created_at', 'updated_at', 'closed_at',
        ]


class LeadCreateSerializer(serializers.Serializer):
    """CRM ga lead yaratish uchun serializer."""
    source = serializers.ChoiceField(
        choices=['amocrm', 'bitrix'],
        default='amocrm',
        help_text="Qaysi CRM ga yuborish: 'amocrm' yoki 'bitrix'"
    )
    name = serializers.CharField(max_length=255)
    price = serializers.DecimalField(max_digits=15, decimal_places=2, default=0)
    pipeline_id = serializers.IntegerField(required=False)
    stage_id = serializers.CharField(required=False)
    responsible_user_id = serializers.IntegerField(required=False)


class ContactCreateSerializer(serializers.Serializer):
    """CRM ga kontakt yaratish uchun serializer."""
    source = serializers.ChoiceField(
        choices=['amocrm', 'bitrix'],
        default='amocrm',
        help_text="Qaysi CRM ga yuborish: 'amocrm' yoki 'bitrix'"
    )
    name = serializers.CharField(max_length=255)
    phone = serializers.CharField(max_length=100, required=False, default='')
    email = serializers.EmailField(required=False, default='')
    company = serializers.CharField(max_length=255, required=False, default='')


class LeadUpdateSerializer(serializers.Serializer):
    """CRM da lead yangilash uchun serializer."""
    name = serializers.CharField(max_length=255, required=False)
    price = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    pipeline_id = serializers.IntegerField(required=False)
    stage_id = serializers.CharField(required=False)
    responsible_user_id = serializers.IntegerField(required=False)


class ContactUpdateSerializer(serializers.Serializer):
    """CRM da kontakt yangilash uchun serializer."""
    name = serializers.CharField(max_length=255, required=False)
    phone = serializers.CharField(max_length=100, required=False)
    email = serializers.EmailField(required=False)
    company = serializers.CharField(max_length=255, required=False)
