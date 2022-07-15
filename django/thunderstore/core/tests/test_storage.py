from thunderstore.core.storage import get_storage_class_or_stub


def test_get_storage_class_or_stub(mocker) -> None:
    assert get_storage_class_or_stub("non.stub.class") == "non.stub.class"
    mocker.patch("sys.argv", ["manage.py", "migrate"])
    assert (
        get_storage_class_or_stub("non.stub.class")
        == "thunderstore.utils.makemigrations.StubStorage"
    )
