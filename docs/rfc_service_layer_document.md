# 1. Introduction

## 1.1 Purpose

-   **Goal**: Introduce a new pattern for separating business logic from views and placing it into a service layer.
-   **Objective**: Ensure that views are simple, focusing solely on handling requests, responses, authentication, and serialization/deserialization, while delegating business logic to a separate service layer.
-   **Reasoning**: These changes are necessary to maintain both the APIs and the old website. Introducing reusable code that can be used in both contexts is crucial.

## 1.2 Scope

-   **Scope of Refactoring**: This document covers changes to views and business logic, focusing on extracting logic from views and placing it in a service layer.
-   **Exclusions**: This document does not cover changes to the database layer or any other components. The database layer remains unchanged, and the service layer will interact with it as needed.

# 2. Problem Statement

## 2.1 Current State

-   **Views**: Many views contain business logic that could be delegated elsewhere. This makes the views complex, difficult to maintain, and hard to test in isolation.

-   **Example of Current View for Disbanding (Deleting) a Team**:

    ```python
    class DisbandTeamAPIView(TeamPermissionsMixin, DestroyAPIView):
        queryset = Team.objects.all()
        lookup_url_kwarg = "team_name"
        lookup_field = "name"

        def check_permissions(self, request):
            super().check_permissions(request)
            team = self.get_object()
            if not team.can_user_disband(request.user):
                raise PermissionDenied("You do not have permission to disband this team.")

        @conditional_swagger_auto_schema(
            operation_id="cyberstorm.team.disband",
            tags=["cyberstorm"],
            responses={status.HTTP_204_NO_CONTENT: ""},
        )
        def delete(self, request, *args, **kwargs):
            return super().delete(request, *args, **kwargs)
    ```

    The issue with this view is that it contains business logic related to deleting a team directly from the database. The view inherits from two other classes and performs permissions checking. The deletion logic and permissions checking could be moved elsewhere.

## 2.2 Proposed Solution

Move business logic from views to a separate service layer in each app with a clear domain. This will simplify views, making them easier to maintain, and will facilitate testing views and services in isolation.

-   **Example of File Structure**:

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

# 3. Architecture Overview

-   **Service Layer**: A new `services` module in each app will house files with functions containing core business logic (e.g., permissions checks, object manipulation). These functions will be small, focused on a single task, and will raise appropriate exceptions when necessary.

-   **Views**: Views will be simplified to handle requests, responses, serialization, and the delegation of tasks.

-   **Tests**: Tests will be updated to test the service layer in isolation, and views will be tested to ensure they handle requests and responses correctly.

-   **Data Flow**:

    1. The view receives a request.
    2. The view delegates the business logic to the service layer.
    3. The service layer performs the business logic, accesses the database, and returns a response.
    4. The view handles the response and returns it to the client.

    **Example**:

    -   Request → View Layer (delegates) → Service Layer (accesses) → Database
    -   Database → Service Layer (returns) → View Layer (returns) → Response

# 4. Design Details

## 4.1 Service Layer Design

-   **Structure**:

    -   Each app will have a new `services` directory.
    -   Each service directory will contain files with functions that encapsulate core business logic (e.g., permissions checks, object manipulation).
    -   Functions will be small, focused on a single task, and will raise appropriate exceptions when necessary.

-   **Example**:

    ```python
    # file: services/team.py
    def disband_team(team_name: str, user: User) -> None:
        team = get_object_or_404(Team, name=team_name)
        if not team.can_user_access(user):
            raise PermissionDenied(...)
        if not team.can_user_disband(user):
            raise PermissionDenied(...)
        team.delete()
    ```

## 4.2 View Layer Design

With the business logic extracted into a service layer function, the view can be simplified:

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

# 5. Testing Strategy

## 5.1 Unit Testing Service Layer

Each service layer function will be unit tested in isolation. The tests will cover:

-   **Happy Path**: The function should return the expected result when given valid input.
-   **Edge Cases**: The function should handle edge cases correctly.
-   **Error Cases**: The function should raise appropriate exceptions when given invalid input.

**Example**:

```python
# file: my_app/tests/test_services/test_team.py
def test_disband_team(team, user):
    team.add_member(user)
    disband_team(team.name, user)
    assert not Team.objects.filter(name=team.name).exists()

def test_disband_team_permission_denied(team):
    user = User.objects.create_user(username="testuser", password="testpass")
    with pytest.raises(PermissionDenied):
        disband_team(team.name, user)

def test_disband_team_not_found(user):
    with pytest.raises(Http404):
        disband_team("non_existent_team", user)
```

## 5.2 Integration Testing Views

Integration tests will ensure that views handle requests and responses correctly. The tests will cover:

-   **Happy Path**: The view should return the expected response when given valid input.
-   **Error Cases**: The view should return appropriate error responses when given invalid input, including authentication and authorization errors, serialization/deserialization errors, and valid payloads.
-   **Correct Delegation to Services**.

**Simple Basic Example**:

```python
# file: my_app/tests/test_views/test_some_view.py
def test_some_view(api_client):
    client.force_login(user)
    url = reverse("some_view")
    data = {"key": "value"}
    response = api_client.post(url, data=data)
    assert response.status_code == 200
    assert response.data == {"key": "value"}

def test_some_view_auth_denied(api_client):
    url = reverse("some_view")
    data = {"key": "value"}
    response = api_client.post(url, data=data)
    assert response.status_code == 401

def test_some_view_invalid_payload(api_client):
    client.force_login(user)
    url = reverse("some_view")
    data = {"key": "invalid_value"}
    response = api_client.post(url, data=data)
    assert response.status_code == 400
```

# 6. Benefits

-   **Separation of Concerns**: Views handle requests and responses, while services handle business logic.
-   **Improved Testability**: The service layer can be tested in isolation, making it easier to write and maintain tests.
-   **Improved Maintainability**: Simplified views and reusable business logic.
-   **Easier to Annotate**: The service layer can be annotated with type hints, making the code easier to understand and catch errors early.

# 7. Trade-offs and Considerations

-   **Tight Coupling**: Services are tightly coupled to Django models and exceptions, which may reduce reusability outside of Django.
-   **Disciplined Approach**: Developers need to avoid leaking business logic back into views.
-   **Boilerplate Code**: There may be a slight increase in boilerplate code due to function delegation, though this is offset by gains in clarity and testability.
