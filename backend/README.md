## How to write test

### Unit Tests

- Use `@pytest.mark.unit` decorator
- Test individual components in isolation
- No database or external service dependencies
- Fast execution

Example:

```python
@pytest.mark.unit
def test_create_project():
    project = Project(
        name="Test Project",
        description="Test Description",
        user_id=uuid.uuid4()
    )
    assert project.name == "Test Project"
    assert isinstance(project.id, uuid.UUID)
```

## Running Tests

1. Run all tests:

```bash
pytest
```

## Writing Tests

### Naming Conventions

- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`

### Best Practices

1. **Arrange-Act-Assert Pattern**

```python
def test_something():
    # Arrange
    project = Project(name="Test")

    # Act
    result = project.some_method()

    # Assert
    assert result == expected_value
```
