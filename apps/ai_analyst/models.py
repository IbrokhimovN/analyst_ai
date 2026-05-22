"""AI tahlilchi ma'lumotlar bazasi modellari.

Bu yerda LangChain funksiyalari uchun ikkita model saqlanadi:

  * ``KnowledgeDocument`` — RAG uchun foydalanuvchi yuklagan hujjatlar
    (PDF / Excel). Har bir hujjat bo'laklarga bo'linib FAISS vektor
    omboriga qo'shiladi.
  * ``ChatMessage`` — har bir menejer uchun alohida suhbat tarixi
    (Memory). LangChain ``ConversationBufferWindowMemory`` har so'rovda
    shu jadvaldan oxirgi xabarlar bilan to'ldiriladi.
"""
from django.db import models


class KnowledgeDocument(models.Model):
    """RAG bilim bazasiga yuklangan bitta hujjat (PDF yoki Excel).

    Hujjat yuklangач ``rag.py`` uni matn bo'laklariga ajratadi va
    FAISS vektor omboriga qo'shadi. ``status`` maydoni qayta ishlash
    holatini kuzatadi.
    """

    STATUS_CHOICES = [
        ('processing', 'Qayta ishlanmoqda'),
        ('ready', 'Tayyor'),
        ('error', 'Xatolik'),
    ]

    title = models.CharField('Sarlavha', max_length=255)
    file = models.FileField('Fayl', upload_to='rag_docs/')
    file_type = models.CharField('Fayl turi', max_length=10)  # pdf / xlsx / csv
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
    """Menejer bo'yicha suhbat tarixining bitta xabari (Memory uchun).

    ``manager_id`` — AmoCRM ``User.amocrm_id``. Umumiy (menejerga
    bog'lanmagan) suhbat uchun ``0`` ishlatiladi. ``role`` xabar kimdan
    kelganini bildiradi: ``human`` (foydalanuvchi) yoki ``ai`` (Claude).
    """

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
