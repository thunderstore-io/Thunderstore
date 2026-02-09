## Celery usage

### Celery task module location

Celery tasks should reside in a Django application's `tasks` module, whether
it's a single file (e.g. `myapp/tasks.py`) or a directory module such as

```
myapp/
  tasks/
    __init__.py
    foo.py
    bar.py
```

**Important:** The Django Celery integration auto-discovers tasks by enumerating
applications defined in the Django `installed_apps` setting and importing the
`tasks` module.

### Celery task definition

Rules of thumb to follow unless you have an explicit reason not to:

-   Use the `@shared_task` decorator
    -   **Reasoning:** The alternative requires importing the celery instance,
        which can more easily lead to complications.
        -   This reasoning doesn't apply if multiple celery applications with explicit
            scoping in the same codebase are desired.
-   Explicitly define a queue for the task (decorator argument)
    -   Import the queue name from `thunderstore.core.settings.CeleryQueues`
    -   If a new queue is desired, add an entry to that class
    -   **Reasoning:** This makes it easier to keep track of all the queues in use
        in the project, both to follow references (what tasks are using a queue) and
        for infrastructure configuration (what queues do we need to listen to)
-   Explicitly define a name for the task (decorator argument)
    -   Good practice is to also define the name of the task in a variable which can
        be imported for easy referring to (e.g. dynamic task calls/chains)
        -   This isn't really necessary, but useful if the name is needed elsewhere.
        -   Definitely **do not** double-define the literal in multiple locations
            as that breaks follow-reference capability from IDEs
    -   Generally the name of the task should follow the python module path / fully
        qualified name of the task function at the time of the task's first creation.
    -   **Reasoning**: By default celery tasks receive the task's function's import
        path as the task name, so if e.g. due to refactoring the function is moved or
        renamed, the task name would change and potentially break backwards
        compatibility. Using an explicit constant for task names avoids this accident
        from happening.

#### Example from the codebase

```python
from celery import shared_task

from thunderstore.core.settings import CeleryQueues
from thunderstore.repository.api.v1.tasks import update_api_v1_caches

@shared_task(
    name="thunderstore.repository.tasks.update_api_caches",
    queue=CeleryQueues.BackgroundCache,
)
def update_api_caches():
    update_api_v1_caches()
```

### Celery task inline imports

_This is not always necessary, but worth keeping in mind_

It's fairly easy to accidentally create circular imports with celery tasks,
causing the project to fail to start up entirely. As such, it might be necessary
to inline import (within the function) any resources a task might need for
completion.

This is especially common if a task requires a model to be imported, but the
model also wants to import the task (because code in the model calls the task).

#### Example from the codebase

```python
# This example doesn't work due to a circular dependency between the code
# modules, but it will work if the dependency is one-directional

from ts_scanners.tasks.scan import scan_decompilation

@shared_task(
    queue=CeleryQueues.BackgroundTask,
    name="ts_scanners.tasks.decompile.decompile_file",
)
def decompile_file(decompilation_id: str) -> str:
    scan_decompilation(decompilation_id)
```

```python
# This example works even if there is a circular dependency between code modules

@shared_task(
    queue=CeleryQueues.BackgroundTask,
    name="ts_scanners.tasks.decompile.decompile_file",
)
def decompile_file(decompilation_id: str) -> str:
    from ts_scanners.tasks.scan import scan_decompilation

    scan_decompilation(decompilation_id)
```
