import uuid
from app.core.models.project import Project


def main():
    project = Project(name="Test Project", description="Test Description", user_id=uuid.uuid4())
    print(project)

if __name__ == "__main__":
    main()
