from thunderstore.core import celery_app


def test_celery_setup():
    @celery_app.task
    def test_task():
        return "Hello"

    taskrun = test_task.delay()
    result = taskrun.get(timeout=1)
    assert taskrun.successful()
    assert result == "Hello"
