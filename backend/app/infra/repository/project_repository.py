from uuid import UUID
from sqlmodel import Session
from app.domain.models.project import Project
from app.infra.repository.generic_repository import GenericRepository

class ProjectRepository(GenericRepository[Project]):
    def __init__(self, db: Session):
        super().__init__(db)

    def get_by_name(self, name: str) -> Project | None:
        return self.db.query(Project).filter(Project.name == name).first()
