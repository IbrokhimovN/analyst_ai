"""
BaseCRMAdapter — barcha CRM adapterlar uchun abstract interfeys.

Har bir adapter (AmoCRM, Bitrix24) shu classni inherit qiladi va
barcha methodlarni implement qilishi shart.
"""
from abc import ABC, abstractmethod
from typing import Optional


class BaseCRMAdapter(ABC):
    """Abstract base class for CRM adapters."""

    # -------------------------------------------------------------------------
    # Lead / Deal CRUD
    # -------------------------------------------------------------------------

    @abstractmethod
    def create_lead(self, data: dict) -> dict:
        """Yangi lead/deal yaratish.
        Returns: {'crm_id': int, 'raw': dict}
        """
        ...

    @abstractmethod
    def update_lead(self, crm_id: int, data: dict) -> dict:
        """Lead/deal yangilash."""
        ...

    @abstractmethod
    def delete_lead(self, crm_id: int) -> bool:
        """Lead/deal o'chirish."""
        ...

    # -------------------------------------------------------------------------
    # Contact CRUD
    # -------------------------------------------------------------------------

    @abstractmethod
    def create_contact(self, data: dict) -> dict:
        """Yangi kontakt yaratish.
        Returns: {'crm_id': int, 'raw': dict}
        """
        ...

    @abstractmethod
    def update_contact(self, crm_id: int, data: dict) -> dict:
        """Kontakt yangilash."""
        ...

    @abstractmethod
    def delete_contact(self, crm_id: int) -> bool:
        """Kontakt o'chirish."""
        ...

    # -------------------------------------------------------------------------
    # Data fetching (sync uchun)
    # -------------------------------------------------------------------------

    @abstractmethod
    def get_leads(self, page: int = 1, limit: int = 50) -> dict:
        """Leadlar ro'yxatini olish (pagination bilan).
        Returns: {'items': list[dict], 'total': int, 'has_more': bool}
        """
        ...

    @abstractmethod
    def get_contacts(self, page: int = 1, limit: int = 50) -> dict:
        """Kontaktlar ro'yxatini olish.
        Returns: {'items': list[dict], 'total': int, 'has_more': bool}
        """
        ...

    @abstractmethod
    def get_pipelines(self) -> list:
        """Pipeline/statuslar ro'yxatini olish.
        Returns: list[dict] — har biri {id, name, statuses: [...]}
        """
        ...

    @abstractmethod
    def get_users(self) -> list:
        """CRM foydalanuvchilarini olish.
        Returns: list[dict] — har biri {id, name, email}
        """
        ...
