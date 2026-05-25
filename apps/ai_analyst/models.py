from django.db import models

class KnowledgeDocument(models.Model):

    STATUS_CHOICES = [
        ('processing', 'Qayta ishlanmoqda'),
        ('ready', 'Tayyor'),
        ('error', 'Xatolik'),
    ]

    title = models.CharField('Sarlavha', max_length=255)
    file = models.FileField('Fayl', upload_to='rag_docs/')
    file_type = models.CharField('Fayl turi', max_length=10)
    chunk_count = models.IntegerField('Bo\'laklar soni', default=0)
    status = models.CharField(
        'Holat', max_length=20, choices=STATUS_CHOICES, default='processing',
    )
    error = models.TextField('Xatolik matni', blank=True, default='')
    uploaded_at = models.DateTimeField('Yuklangan vaqt', auto_now_add=True)

    class Meta:
        verbose_name = 'Bilim hujjati'
        verbose_name_plural = 'Bilim hujjatlari'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f'{self.title} ({self.get_status_display()})'

class ChatMessage(models.Model):

    ROLE_CHOICES = [
        ('human', 'Foydalanuvchi'),
        ('ai', 'AI'),
    ]

    manager_id = models.IntegerField('Menejer ID', default=0, db_index=True)
    role = models.CharField('Rol', max_length=10, choices=ROLE_CHOICES)
    content = models.TextField('Matn')
    created_at = models.DateTimeField('Vaqt', auto_now_add=True)

    class Meta:
        verbose_name = 'Suhbat xabari'
        verbose_name_plural = 'Suhbat xabarlari'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['manager_id', 'created_at']),
        ]

    def __str__(self):
        return f'[{self.manager_id}] {self.role}: {self.content[:40]}'
