"""
Bitrix24 ma'lumotlarini sinxronlash management command.

Foydalanish:
    python manage.py sync_bitrix            # Barcha ma'lumotlarni sinxronlash
    python manage.py sync_bitrix --deals    # Faqat deallarni
    python manage.py sync_bitrix --contacts # Faqat kontaktlarni
    python manage.py sync_bitrix --leads    # Faqat Bitrix leadlarni
    python manage.py sync_bitrix --pipelines # Faqat pipelinelarni
"""
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Bitrix24 dan ma\'lumotlarni sinxronlash'

    def add_arguments(self, parser):
        parser.add_argument(
            '--deals', action='store_true',
            help='Faqat deallarni sinxronlash',
        )
        parser.add_argument(
            '--contacts', action='store_true',
            help='Faqat kontaktlarni sinxronlash',
        )
        parser.add_argument(
            '--leads', action='store_true',
            help='Faqat Bitrix leadlarni sinxronlash',
        )
        parser.add_argument(
            '--pipelines', action='store_true',
            help='Faqat pipelinelarni sinxronlash',
        )
        parser.add_argument(
            '--async', action='store_true', dest='run_async',
            help='Celery task sifatida asinxron ishga tushirish',
        )

    def handle(self, *args, **options):
        webhook_url = getattr(settings, 'BITRIX_WEBHOOK_URL', '')
        if not webhook_url or webhook_url == 'https://yourcompany.bitrix24.ru/rest/1/webhooktoken/':
            self.stderr.write(self.style.ERROR(
                "BITRIX_WEBHOOK_URL sozlanmagan! .env faylda to'g'ri URL kiriting."
            ))
            return

        specific = options['deals'] or options['contacts'] or options['leads'] or options['pipelines']

        if options['run_async']:
            self._run_async(options, specific)
        else:
            self._run_sync(options, specific)

    def _run_async(self, options, specific):
        """Celery task orqali asinxron ishga tushirish."""
        from apps.crm.tasks import (
            sync_bitrix_deals, sync_bitrix_contacts,
            sync_bitrix_leads, sync_bitrix_pipelines,
            sync_bitrix_all,
        )

        if not specific:
            sync_bitrix_all.delay()
            self.stdout.write(self.style.SUCCESS("Bitrix24 to'liq sync task yuborildi"))
            return

        if options['pipelines']:
            sync_bitrix_pipelines.delay()
            self.stdout.write("Pipeline sync task yuborildi")
        if options['deals']:
            sync_bitrix_deals.delay()
            self.stdout.write("Deal sync task yuborildi")
        if options['contacts']:
            sync_bitrix_contacts.delay()
            self.stdout.write("Contact sync task yuborildi")
        if options['leads']:
            sync_bitrix_leads.delay()
            self.stdout.write("Lead sync task yuborildi")

        self.stdout.write(self.style.SUCCESS("Tasklar yuborildi"))

    def _run_sync(self, options, specific):
        """Sinxron (to'g'ridan-to'g'ri) ishga tushirish."""
        from apps.crm.tasks import (
            sync_bitrix_deals, sync_bitrix_contacts,
            sync_bitrix_leads, sync_bitrix_pipelines,
        )

        if not specific or options['pipelines']:
            self.stdout.write("Pipelinelarni sinxronlash...")
            try:
                sync_bitrix_pipelines()
                self.stdout.write(self.style.SUCCESS("✓ Pipelinelar sinxronlandi"))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"✗ Pipeline xatolik: {e}"))

        if not specific or options['deals']:
            self.stdout.write("Deallarni sinxronlash...")
            try:
                result = sync_bitrix_deals()
                self.stdout.write(self.style.SUCCESS(f"✓ {result.get('synced', 0)} deal sinxronlandi"))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"✗ Deal xatolik: {e}"))

        if not specific or options['contacts']:
            self.stdout.write("Kontaktlarni sinxronlash...")
            try:
                result = sync_bitrix_contacts()
                self.stdout.write(self.style.SUCCESS(f"✓ {result.get('synced', 0)} kontakt sinxronlandi"))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"✗ Kontakt xatolik: {e}"))

        if not specific or options['leads']:
            self.stdout.write("Bitrix leadlarni sinxronlash...")
            try:
                result = sync_bitrix_leads()
                self.stdout.write(self.style.SUCCESS(f"✓ {result.get('synced', 0)} lead sinxronlandi"))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"✗ Lead xatolik: {e}"))

        self.stdout.write(self.style.SUCCESS("\nBitrix24 sinxronlash tugadi!"))
