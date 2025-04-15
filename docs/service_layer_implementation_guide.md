# Service Layer Pattern Implementation Guide

## Introduction

This guide outlines the current implementation of the service layer pattern in our codebase. The goal is to separate business logic from views, making the codebase more maintainable, testable, and reusable.

## Architecture Overview

### Service Layer

The service layer contains the core business logic of the application. Each app has a `services` directory where business logic is implemented in small, focused functions. These functions handle tasks such as permissions checks and object manipulation.

### Views

Views are simplified to handle requests, responses, serialization, and delegation of tasks to the service layer. They do not contain business logic.

### Data Flow

1. The view receives a request.
2. The view delegates the business logic to the service layer.
3. The service layer performs the business logic, accesses the database, and returns a response.
4. The view handles the response and returns it to the client.

## Directory Structure

Each app should have the following structure:

```
my_app/
    ├── services/
    │   ├── __init__.py
    │   ├── team.py
    ├── views/
    │   ├── __init__.py
    │   ├── team.py
    └── tests/
        ├── __init__.py
        ├── test_services/
        │   ├── __init__.py
        │   ├── test_team.py
        └── test_views/
            ├── __init__.py
            ├── test_team.py
```

## Service Layer Design

### Example

```python
# file: services/team.py
def disband_team(team_name: str, user: User) -> None:
    team = get_object_or_404(Team, name=team_name)
    team.ensure_user_can_access(user)
    team.ensure_user_can_disband(user)
    team.delete()
```

## View Layer Design

### Example of REST API view

```python
# file: views/team.py
class DisbandTeamAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @conditional_swagger_auto_schema(
        operation_id="cyberstorm.team.disband",
        tags=["cyberstorm"],
        responses={status.HTTP_204_NO_CONTENT: ""},
    )
    def delete(self, request, *args, **kwargs):
        team_name = kwargs["team_name"]
        disband_team(team_name, request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
```

### Example of Form view

```python
def form_valid(self, request, form):
    try:
        team_name = form.cleaned_data["team_name"]
        team_services.create_team(team_name=team_name, user=request.user)
    except ValidationError as e:
        form.add_error(None, e)  # Attach error manually to form
        return self.form_invalid(form)
    return redirect(self.get_success_url())
```

## Testing Strategy

### Unit Testing Service Layer

Each service layer function should be unit tested in isolation. Tests should cover happy paths, edge cases, and error cases.

### Integration Testing Views

Integration tests should ensure that views handle requests and responses correctly and delegate tasks to the service layer appropriately.

## Exception Handling

The service layer should raise exceptions for error cases. Views should handle these exceptions and return appropriate HTTP responses.

Exceptions from django.core.exceptions are to be used in the service layer. Django Rest Framework provides a way to handle ValidationErrors, PermissionDenied, and NotFound exceptions automatically(when using django.core.exceptions).

Exceptions need to be manually handled in Form views(depending on where they are raised).

## Benefits

-   **Separation of Concerns**: Views handle requests and responses, while services handle business logic.
-   **Improved Testability**: The service layer can be tested in isolation.
-   **Improved Maintainability**: Simplified views and reusable business logic.
-   **Easier to Annotate**: The service layer can be annotated with type hints.

## Considerations

-   Services are tightly coupled to Django models and exceptions.
-   Developers must avoid leaking business logic back into views.
-   There may be a slight increase in boilerplate code due to function delegation.
