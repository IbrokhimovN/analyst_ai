"""AI tahlilchi modellari uchun Django admin sozlamalari."""
from django.contrib import admin

from .models import ChatMessage, KnowledgeDocument


@admin.register(KnowledgeDocument)
class KnowledgeDocumentAdmin(admin.ModelAdmin):
    """RAG bilim hujjatlari admin paneli."""
    list_display = ('title', 'file_type', 'chunk_count', 'status', 'uploaded_at')
    list_filter = ('status', 'file_type')
    search_fields = ('title',)
    readonly_fields = ('chunk_count', 'uploaded_at')


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    """Menejer suhbat tarixi (Memory) admin paneli."""
    list_display = ('manager_id', 'role', 'content', 'created_at')
    list_filter = ('role', 'manager_id')
    search_fields = ('content',)
    readonly_fields = ('created_at',)
