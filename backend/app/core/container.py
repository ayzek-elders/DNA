from dependency_injector import containers, providers
from sqlmodel import Session, create_engine
from ..infra.repository.project_repository import ProjectRepository

class Container(containers.DeclarativeContainer):
  config = providers.Configuration()
  db_engine = providers.Singleton(
    create_engine,
    config.POSTGRES_CONNECTION_STRING,
    echo=config.ENVIRONMENT == "local"
  )

  db_session = providers.Factory(
    Session,
    bind=db_engine
  )

  project_repository = providers.Factory(
    ProjectRepository,
    db=db_session
  )