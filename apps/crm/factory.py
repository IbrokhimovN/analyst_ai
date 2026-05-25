from django.conf import settings

from .base import BaseCRMAdapter

def get_crm_adapter(source: str = None) -> BaseCRMAdapter:
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
