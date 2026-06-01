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
            '--users', action='store_true',
            help='Faqat foydalanuvchilarni (menejerlarni) sinxronlash',
        )
        parser.add_argument(
            '--async', action='store_true', dest='run_async',
            help='Celery task sifatida asinxron ishga tushirish',
        )
        parser.add_argument(
            '--full', action='store_true', dest='full',
            help="To'liq qayta yuklash (default: faqat o'zgargan yozuvlar — incremental)",
        )

    def handle(self, *args, **options):
        webhook_url = getattr(settings, 'BITRIX_WEBHOOK_URL', '')
        if not webhook_url or webhook_url == 'https://yourcompany.bitrix24.ru/rest/1/webhooktoken/':
            self.stderr.write(self.style.ERROR(
                "BITRIX_WEBHOOK_URL sozlanmagan! .env faylda to'g'ri URL kiriting."
            ))
            return

        specific = (options['deals'] or options['contacts'] or options['leads']
                    or options['pipelines'] or options['users'])

        if options['run_async']:
            self._run_async(options, specific)
        else:
            self._run_sync(options, specific)

    def _run_async(self, options, specific):
        from apps.crm.tasks import (
            sync_bitrix_deals, sync_bitrix_contacts,
            sync_bitrix_leads, sync_bitrix_pipelines,
            sync_bitrix_users, sync_bitrix_all,
        )

        full = options['full']
        if not specific:
            if full:
                sync_bitrix_users.delay()
                sync_bitrix_pipelines.delay()
                sync_bitrix_deals.delay(full=True)
                sync_bitrix_contacts.delay(full=True)
                sync_bitrix_leads.delay(full=True)
                self.stdout.write(self.style.SUCCESS("Bitrix24 to'liq (full) sync tasklari yuborildi"))
            else:
                sync_bitrix_all.delay()
                self.stdout.write(self.style.SUCCESS("Bitrix24 incremental sync task yuborildi"))
            return

        if options['users']:
            sync_bitrix_users.delay()
            self.stdout.write("User sync task yuborildi")
        if options['pipelines']:
            sync_bitrix_pipelines.delay()
            self.stdout.write("Pipeline sync task yuborildi")
        if options['deals']:
            sync_bitrix_deals.delay(full=full)
            self.stdout.write("Deal sync task yuborildi")
        if options['contacts']:
            sync_bitrix_contacts.delay(full=full)
            self.stdout.write("Contact sync task yuborildi")
        if options['leads']:
            sync_bitrix_leads.delay(full=full)
            self.stdout.write("Lead sync task yuborildi")

        self.stdout.write(self.style.SUCCESS("Tasklar yuborildi"))

    def _run_sync(self, options, specific):
        from apps.crm.tasks import (
            sync_bitrix_deals, sync_bitrix_contacts,
            sync_bitrix_leads, sync_bitrix_pipelines,
            sync_bitrix_users,
        )

        full = options['full']
        mode = "to'liq (full)" if full else "incremental"
        self.stdout.write(f"Rejim: {mode}")

        if not specific or options['users']:
            self.stdout.write("Foydalanuvchilarni sinxronlash...")
            try:
                result = sync_bitrix_users()
                self.stdout.write(self.style.SUCCESS(f"✓ {result.get('synced', 0)} foydalanuvchi sinxronlandi"))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"✗ User xatolik: {e}"))

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
                result = sync_bitrix_deals(full=full)
                self.stdout.write(self.style.SUCCESS(f"✓ {result.get('synced', 0)} deal sinxronlandi"))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"✗ Deal xatolik: {e}"))

        if not specific or options['contacts']:
            self.stdout.write("Kontaktlarni sinxronlash...")
            try:
                result = sync_bitrix_contacts(full=full)
                self.stdout.write(self.style.SUCCESS(f"✓ {result.get('synced', 0)} kontakt sinxronlandi"))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"✗ Kontakt xatolik: {e}"))

        if not specific or options['leads']:
            self.stdout.write("Bitrix leadlarni sinxronlash...")
            try:
                result = sync_bitrix_leads(full=full)
                self.stdout.write(self.style.SUCCESS(f"✓ {result.get('synced', 0)} lead sinxronlandi"))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"✗ Lead xatolik: {e}"))

        self.stdout.write(self.style.SUCCESS("\nBitrix24 sinxronlash tugadi!"))
