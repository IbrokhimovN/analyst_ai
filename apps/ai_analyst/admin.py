from django.contrib import admin

from .models import (ChatMessage, KnowledgeDocument, GeneratedReport,
                     MetricAlert)

@admin.register(KnowledgeDocument)
class KnowledgeDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'file_type', 'chunk_count', 'status', 'uploaded_at')
    list_filter = ('status', 'file_type')
    search_fields = ('title',)
    readonly_fields = ('chunk_count', 'uploaded_at')

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('manager_id', 'role', 'content', 'feedback', 'created_at')
    list_filter = ('role', 'feedback', 'manager_id')
    search_fields = ('content',)
    readonly_fields = ('created_at',)

@admin.register(GeneratedReport)
class GeneratedReportAdmin(admin.ModelAdmin):
    list_display = ('kind', 'source', 'title', 'created_at')
    list_filter = ('kind', 'source')
    readonly_fields = ('created_at',)

@admin.register(MetricAlert)
class MetricAlertAdmin(admin.ModelAdmin):
    list_display = ('severity', 'metric', 'source', 'message', 'is_read',
                    'created_at')
    list_filter = ('severity', 'metric', 'source', 'is_read')
    readonly_fields = ('created_at',)
