import pytest

from thunderstore.community.factories import CommunityFactory
from thunderstore.repository.tasks import update_chunked_community_package_caches


@pytest.mark.django_db
def test_update_chunked_community_package_caches_in_parallel():
    """
    Test that the celery tasks creates sub-tasks for each community and they
    run successfully.
    """

    size = 5
    CommunityFactory.create_batch(size=size)
    result = update_chunked_community_package_caches.apply_async()
    result = result.get()
    sub_task_results = result.children

    assert result.successful()
    for sub_task in sub_task_results:
        assert sub_task.successful()

    assert len(sub_task_results) == size
