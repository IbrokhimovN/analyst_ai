"""
CRM Adapter Factory — sozlamaga qarab kerakli adapterni tanlash.

Foydalanish:
    from apps.crm.factory import get_crm_adapter

    adapter = get_crm_adapter()           # DEFAULT_CRM dan
    adapter = get_crm_adapter('amocrm')   # AmoCRM
    adapter = get_crm_adapter('bitrix')   # Bitrix24
"""
from django.conf import settings

from .base import BaseCRMAdapter


def get_crm_adapter(source: str = None) -> BaseCRMAdapter:
    """Sozlamaga qarab CRM adapter qaytarish.

    Args:
        source: 'amocrm' yoki 'bitrix'. None bo'lsa DEFAULT_CRM ishlatiladi.

    Returns:
        BaseCRMAdapter instance

    Raises:
        ValueError: noma'lum CRM source berilsa
    """
    from .adapters.amocrm import AmoCRMAdapter
    from .adapters.bitrix import Bitrix24Adapter

    s = (source or getattr(settings, 'DEFAULT_CRM', 'amocrm')).lower().strip()

    adapters = {
        'amocrm': AmoCRMAdapter,
        'bitrix': Bitrix24Adapter,
        'bitrix24': Bitrix24Adapter,
    }

    adapter_class = adapters.get(s)
    if not adapter_class:
        raise ValueError(
            f"Noma'lum CRM: '{s}'. Mavjud variantlar: {', '.join(adapters.keys())}"
        )

    return adapter_class()
