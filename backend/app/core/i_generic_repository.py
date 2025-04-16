from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from uuid import UUID

T = TypeVar("T")

class IGenericRepository(ABC, Generic[T]):
  @abstractmethod
  def add(self, entity: T) -> T:
    pass

  @abstractmethod
  def get(self, entity_id: UUID) -> T:
    pass
  
  @abstractmethod
  def update(self, entity: T) -> T:
    pass

  @abstractmethod
  def delete(self, entity: T) -> None:
    pass

  @abstractmethod
  def get_all(self) -> list[T]:
    pass
