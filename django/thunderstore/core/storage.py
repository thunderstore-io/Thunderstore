from thunderstore.utils.makemigrations import is_migrate_check

# These are required as a placeholder stub for migrations, otherwise Django thinks
# something keeps changing due to settings being different.


def get_storage_class_or_stub(storage_class: str) -> str:
    if is_migrate_check():
        return "thunderstore.utils.makemigrations.StubStorage"
    return storage_class
