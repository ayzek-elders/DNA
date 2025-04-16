import uuid
from app.core.container import Container
from app.core.config import settings
from dependency_injector.wiring import Provide, inject

from app.domain.models.project import Project
from app.infra.repository.project_repository import ProjectRepository



@inject
def main(repo: ProjectRepository = Provide[Container.project_repository]):
    project = Project(name="merhaba", description="hi")
    print(repo.add(project))

if __name__ == "__main__":
    container = Container()
    print(settings.model_dump())
    container.config.from_dict(settings.model_dump())

    container.wire(modules=[__name__])
    main()
