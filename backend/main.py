import uuid
from app.core.models.project import Project
from app.core.config import settings


def main():
    print(settings.POSTGRES_CONNECTION_STRING)

if __name__ == "__main__":
    main()
