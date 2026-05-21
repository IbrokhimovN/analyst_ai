"""
AmoCRM dan ma'lumotlarni bir martalik tortib olish uchun management command.

Foydalanish:
  1. Avval AmoCRM integratsiyadan authorization code oling
  2. python manage.py sync_amocrm --code YOUR_AUTH_CODE
  
  Yoki agar token allaqachon mavjud bo'lsa:
  3. python manage.py sync_amocrm
"""
import logging

from django.core.management.base import BaseCommand, CommandError

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "AmoCRM dan barcha ma'lumotlarni sinxronlash"

    def add_arguments(self, parser):
        parser.add_argument(
            '--code',
            type=str,
            help='AmoCRM OAuth authorization code (birinchi marta ulanganda)',
        )

    def handle(self, *args, **options):
        from apps.amocrm.models import AmoCRMToken
        from apps.amocrm.services import AmoCRMService
        from apps.amocrm.sync import sync_all_now

        code = options.get('code')

        # Agar code berilgan bo'lsa — avval token olish
        if code:
            self.stdout.write(self.style.WARNING("Authorization code bilan token olish..."))
            try:
                service = AmoCRMService()
                token_data = service.exchange_code(code)

                AmoCRMToken.objects.all().delete()
                AmoCRMToken.objects.create(
                    access_token=token_data["access_token"],
                    refresh_token=token_data["refresh_token"],
                )
                self.stdout.write(self.style.SUCCESS("✅ Token muvaffaqiyatli saqlandi!"))

            except Exception as e:
                raise CommandError(f"Token olishda xatolik: {e}")

        # Token borligini tekshirish
        if not AmoCRMToken.objects.exists():
            self.stdout.write(self.style.ERROR(
                "\n❌ AmoCRM token topilmadi!\n"
                "\n"
                "Quyidagi usullardan birini ishlating:\n"
                "\n"
                "1️⃣  Authorization code bilan:\n"
                f"   python manage.py sync_amocrm --code YOUR_CODE\n"
                "\n"
                "2️⃣  Brauzerda OAuth orqali:\n"
                f"   http://localhost:8001/amocrm/auth/\n"
            ))
            return

        # Sinxronlash
        self.stdout.write(self.style.WARNING("\n🔄 Ma'lumotlar sinxronlash boshlandi...\n"))

        try:
            result = sync_all_now()

            self.stdout.write(self.style.SUCCESS(
                f"\n✅ Sinxronlash muvaffaqiyatli tugadi!\n"
                f"   📊 Pipelinelar: {result['pipelines']}\n"
                f"   👤 Foydalanuvchilar: {result['users']}\n"
                f"   📋 Leadlar: {result['leads']}\n"
                f"   📞 Kontaktlar: {result['contacts']}\n"
            ))

        except Exception as e:
            raise CommandError(f"Sinxronlashda xatolik: {e}")
