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

    FEEDBACK_CHOICES = [
        ('', '—'),
        ('up', 'Foydali'),
        ('down', 'Foydasiz'),
    ]

    manager_id = models.IntegerField('Menejer ID', default=0, db_index=True)
    role = models.CharField('Rol', max_length=10, choices=ROLE_CHOICES)
    content = models.TextField('Matn')
    feedback = models.CharField('Baho', max_length=4,
                                choices=FEEDBACK_CHOICES, blank=True, default='')
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

class GeneratedReport(models.Model):
    """Celery tomonidan avtomatik tuziladigan AI hisobotlari."""

    KIND_CHOICES = [
        ('daily', 'Kunlik'),
        ('weekly', 'Haftalik'),
    ]

    kind = models.CharField('Tur', max_length=10, choices=KIND_CHOICES,
                            db_index=True)
    source = models.CharField('Manba', max_length=20, blank=True, default='')
    title = models.CharField('Sarlavha', max_length=255)
    content = models.TextField('Matn (Markdown)')
    metrics = models.JSONField('Ko\'rsatkichlar', default=dict, blank=True)
    created_at = models.DateTimeField('Vaqt', auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'AI hisobot'
        verbose_name_plural = 'AI hisobotlar'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_kind_display()} — {self.created_at:%Y-%m-%d}'

class MetricAlert(models.Model):
    """Belgilangan chegaralar buzilganda yaratiladigan ogohlantirishlar."""

    SEVERITY_CHOICES = [
        ('info', 'Ma\'lumot'),
        ('warning', 'Ogohlantirish'),
        ('critical', 'Jiddiy'),
    ]

    metric = models.CharField('Ko\'rsatkich', max_length=50)
    source = models.CharField('Manba', max_length=20, blank=True, default='')
    severity = models.CharField('Darajasi', max_length=10,
                                choices=SEVERITY_CHOICES, default='warning')
    message = models.CharField('Xabar', max_length=500)
    value = models.FloatField('Qiymat', null=True, blank=True)
    threshold = models.FloatField('Chegara', null=True, blank=True)
    is_read = models.BooleanField('O\'qilgan', default=False, db_index=True)
    created_at = models.DateTimeField('Vaqt', auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Metrik alert'
        verbose_name_plural = 'Metrik alertlar'
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.severity}] {self.message[:50]}'
