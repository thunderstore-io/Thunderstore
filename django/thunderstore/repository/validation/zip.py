from typing import List
from zipfile import ZipInfo

from django.conf import settings

from thunderstore.repository.models import Team


def check_unsafe_paths(infolist: List[ZipInfo]) -> bool:
    for entry in infolist:
        if (
            entry.filename.startswith("..")
            or entry.filename.startswith("/")
            or entry.filename.startswith("\\")
            or "/.." in entry.filename
            or "//" in entry.filename
            or "./" in entry.filename
            or "\\.." in entry.filename
            or "\\\\" in entry.filename
            or ".\\" in entry.filename
            or "/\\" in entry.filename
            or "\\/" in entry.filename
        ):
            return True
    return False


def check_zero_offset(infolist: List[ZipInfo]) -> bool:
    for entry in infolist:
        if entry.header_offset == 0:
            return True
    return False


def check_duplicate_filenames(infolist: List[ZipInfo]) -> bool:
    filenames = set()
    for entry in infolist:
        if entry.filename.lower() in filenames:
            return True
        filenames.add(entry.filename.lower())
    return False


def check_exceeds_max_file_count_per_zip(infolist: List[ZipInfo], team: Team) -> bool:
    # We assume team-specific limits aren't going to be used for downgrades,
    # only upgrades, meaning if the global limit is increased later on it can
    # trump team-specific limits.
    effective_maximum = max(
        team.max_file_count_per_zip or 0, settings.REPOSITORY_MAX_FILE_COUNT_PER_ZIP
    )
    return len(infolist) > effective_maximum
