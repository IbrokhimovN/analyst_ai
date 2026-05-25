from abc import ABC, abstractmethod
from typing import Optional

class BaseCRMAdapter(ABC):

    @abstractmethod
    def create_lead(self, data: dict) -> dict:
        ...

    @abstractmethod
    def update_lead(self, crm_id: int, data: dict) -> dict:
        ...

    @abstractmethod
    def delete_lead(self, crm_id: int) -> bool:
        ...

    @abstractmethod
    def create_contact(self, data: dict) -> dict:
        ...

    @abstractmethod
    def update_contact(self, crm_id: int, data: dict) -> dict:
        ...

    @abstractmethod
    def delete_contact(self, crm_id: int) -> bool:
        ...

    @abstractmethod
    def get_leads(self, page: int = 1, limit: int = 50) -> dict:
        ...

    @abstractmethod
    def get_contacts(self, page: int = 1, limit: int = 50) -> dict:
        ...

    @abstractmethod
    def get_pipelines(self) -> list:
        ...

    @abstractmethod
    def get_users(self) -> list:
        ...
