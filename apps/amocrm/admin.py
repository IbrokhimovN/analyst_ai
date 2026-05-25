from django.contrib import admin
from .models import AmoCRMToken, Pipeline, PipelineStatus, Contact, Lead, User

@admin.register(AmoCRMToken)
class AmoCRMTokenAdmin(admin.ModelAdmin):
    list_display = ['id', 'updated_at', 'expires_at']
    readonly_fields = ['access_token', 'refresh_token', 'created_at', 'updated_at']

@admin.register(Pipeline)
class PipelineAdmin(admin.ModelAdmin):
    list_display = ['name', 'amocrm_id', 'sort', 'is_main']
    list_filter = ['is_main']
    search_fields = ['name']

@admin.register(PipelineStatus)
class PipelineStatusAdmin(admin.ModelAdmin):
    list_display = ['name', 'pipeline', 'amocrm_id', 'sort', 'color']
    list_filter = ['pipeline']
    search_fields = ['name']

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'email', 'amocrm_id', 'created_at']
    search_fields = ['name', 'phone', 'email']
    list_filter = ['created_at']

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'status_id', 'pipeline_id', 'amocrm_id', 'created_at']
    list_filter = ['pipeline_id', 'status_id', 'created_at']
    search_fields = ['name']
    readonly_fields = ['raw_data']

@admin.register(User)
class AmoCRMUserAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'role', 'amocrm_id']
    search_fields = ['name', 'email']
