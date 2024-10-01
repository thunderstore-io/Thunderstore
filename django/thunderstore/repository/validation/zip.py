from typing import List
from zipfile import ZipInfo


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
