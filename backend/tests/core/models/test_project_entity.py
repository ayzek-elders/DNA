import uuid
from datetime import datetime
from app.core.models.project import Project
import pytest

@pytest.mark.unit
def test_create_project():
    # Test project creation with basic attributes
    project = Project(
        name="Test Project",
        description="Test Description",
    )
    
    assert project.name == "Test Project"
    assert project.description == "Test Description"
    assert isinstance(project.created_at, datetime)
    assert isinstance(project.updated_at, datetime)