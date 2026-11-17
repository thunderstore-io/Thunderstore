from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from thunderstore.repository.filetree import create_file_tree_from_zip_data


def _build_zip(files: dict) -> BytesIO:
    zip_data = BytesIO()
    with ZipFile(zip_data, "w", compression=ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    zip_data.seek(0)
    return zip_data


@pytest.mark.django_db
def test_create_file_tree_from_zip_data():
    files = {
        "README.md": b"# Test readme",
        "plugins/": b"",
        "plugins/mod.dll": b"binary content",
    }

    group = create_file_tree_from_zip_data("Test tree", _build_zip(files))

    assert group.name == "Test tree"
    assert group.is_complete is True
    entries = {entry.name: entry for entry in group.entries.all()}
    assert set(entries) == {"README.md", "plugins/mod.dll"}
    for name, entry in entries.items():
        assert entry.data == files[name]
        assert entry.data_size == len(files[name])


@pytest.mark.django_db
def test_create_file_tree_from_zip_data_does_not_read_entries_whole(mocker):
    mocker.patch.object(
        ZipFile, "read", side_effect=AssertionError("Whole entry was read at once")
    )
    # Small limit so the entry spills to disk without a large fixture.
    mocker.patch("thunderstore.utils.contexts.SPOOLED_COPY_MAX_MEMORY_SIZE", 1024)
    content = b"0123456789abcdef" * 1024

    group = create_file_tree_from_zip_data("Test tree", _build_zip({"big": content}))

    entry = group.entries.get()
    assert entry.data_size == len(content)
    assert entry.data == content
