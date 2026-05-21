from django.db import models


# CRM manba tanlov
CRM_SOURCE_CHOICES = [
    ('amocrm', 'AmoCRM'),
    ('bitrix', 'Bitrix24'),
]


class AmoCRMToken(models.Model):
    """AmoCRM OAuth tokenlarini saqlash."""
    access_token = models.TextField()
    refresh_token = models.TextField()
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'AmoCRM Token'
        verbose_name_plural = 'AmoCRM Tokenlar'

    def __str__(self):
        return f"AmoCRM Token (updated: {self.updated_at})"


class Pipeline(models.Model):
    """AmoCRM sotuv pipeline (voronka)."""
    amocrm_id = models.IntegerField(unique=True, db_index=True)
    name = models.CharField(max_length=255)
    sort = models.IntegerField(default=0)
    is_main = models.BooleanField(default=False)
    raw_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Pipeline'
        verbose_name_plural = 'Pipelinelar'
        ordering = ['sort']

    def __str__(self):
        return self.name


class PipelineStatus(models.Model):
    """Pipeline ichidagi bosqich (status)."""
    amocrm_id = models.IntegerField(db_index=True)
    pipeline = models.ForeignKey(Pipeline, on_delete=models.CASCADE, related_name='statuses')
    name = models.CharField(max_length=255)
    sort = models.IntegerField(default=0)
    color = models.CharField(max_length=50, blank=True, default='')
    is_editable = models.BooleanField(default=True)
    raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = 'Pipeline Status'
        verbose_name_plural = 'Pipeline Statuslar'
        ordering = ['sort']
        unique_together = ['amocrm_id', 'pipeline']

    def __str__(self):
        return f"{self.pipeline.name} → {self.name}"


class Contact(models.Model):
    """CRM kontakt (AmoCRM yoki Bitrix24)."""
    amocrm_id = models.IntegerField(unique=True, db_index=True)
    source = models.CharField(
        max_length=20, choices=CRM_SOURCE_CHOICES,
        default='amocrm', db_index=True,
    )
    name = models.CharField(max_length=255, blank=True, default='')
    first_name = models.CharField(max_length=255, blank=True, default='')
    last_name = models.CharField(max_length=255, blank=True, default='')
    company = models.CharField(max_length=255, blank=True, default='')
    phone = models.CharField(max_length=100, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    responsible_user_id = models.IntegerField(null=True, blank=True)
    raw_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Kontakt'
        verbose_name_plural = 'Kontaktlar'
        ordering = ['-created_at']

    def __str__(self):
        return self.name or f"Contact #{self.amocrm_id}"


class Lead(models.Model):
    """CRM lead/deal (AmoCRM yoki Bitrix24)."""
    amocrm_id = models.IntegerField(unique=True, db_index=True)
    source = models.CharField(
        max_length=20, choices=CRM_SOURCE_CHOICES,
        default='amocrm', db_index=True,
    )
    name = models.CharField(max_length=255, blank=True, default='')
    price = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    status_id = models.IntegerField(null=True, blank=True)
    pipeline_id = models.IntegerField(null=True, blank=True)
    responsible_user_id = models.IntegerField(null=True, blank=True)
    loss_reason = models.CharField(max_length=500, blank=True, default='')
    contacts = models.ManyToManyField(Contact, blank=True, related_name='leads')
    pipeline_ref = models.ForeignKey(
        Pipeline, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='leads',
        db_column='pipeline_ref_id'
    )
    status_ref = models.ForeignKey(
        PipelineStatus, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='leads',
        db_column='status_ref_id'
    )
    raw_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Lead'
        verbose_name_plural = 'Leadlar'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status_id', 'pipeline_id']),
            models.Index(fields=['responsible_user_id']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.name} — {self.price:,.0f} so'm"


class User(models.Model):
    """AmoCRM foydalanuvchi (menejer)."""
    amocrm_id = models.IntegerField(unique=True, db_index=True)
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, default='')
    role = models.CharField(max_length=100, blank=True, default='')
    raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = 'AmoCRM Foydalanuvchi'
        verbose_name_plural = 'AmoCRM Foydalanuvchilar'

    def __str__(self):
        return self.name
