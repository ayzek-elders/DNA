from typing import Generic, TypeVar
from sqlmodel import UUID, Session
from app.core.i_generic_repository import IGenericRepository
T = TypeVar("T")

class GenericRepository(IGenericRepository,Generic[T]):
  def __init__(self, db: Session):
    self.db = db

  def add(self, entity: T) -> T:
    self.db.add(entity)
    self.db.commit()
    self.db.refresh(entity)
    return entity

  def get(self, entity_id: UUID) -> T:
    return self.db.get(T, entity_id)

  def update(self, entity: T) -> T:
    self.db.merge(entity)
    self.db.commit()
    return entity

  def delete(self, entity: T) -> None:
    self.db.delete(entity)
    self.db.commit()

  def get_all(self) -> list[T]:
    return self.db.query(T).all()
