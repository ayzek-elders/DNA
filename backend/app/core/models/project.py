import uuid 
from sqlmodel import Field, SQLModel
from .auditable_entity import AuditableEntity

#TODO : In future add user relationship
class Project(AuditableEntity, SQLModel, table=True):
    name: str = Field(default=None, unique=True, index=True)
    description: str = Field(default=None)
    