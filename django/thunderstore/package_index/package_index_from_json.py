"""
Script for experimenting with a new package index format.

This script is a work-in-progress experiment for converting the old
package index JSON file to a new format that is more suitable for
incremental updates and efficient storage.

The new format is split into two parts: package index and version index.
The package index contains information about packages and the version
index contains information about versions.

* The package index is split into shards based on the namespace (owner)
  of the package.  Number of chards is controlled by `SHARD_COUNT`.

* The version index is split into chunks of fixed size so older versions
  are stored to lower numbered chunks and when a chunk is full, a new
  chunk is started and the old full chunks are effectively immutable.
  Number of versions per chunk is controlled by `CHUNK_SIZE`.

Additionally the new index will be served as a Git repository via the
simple HTTP interface (i.e. static files via CDN) and the Git repository
will be updated with a new commit when the index is updated.  The commit
history can either be preserved or squashed into a single commit (see
`SQUASH_COMMITS`).

There is also a possibility to limit the output to only include packages
and versions that were created/updated before a given date (see the
`limit_to_date` parameter).  This is useful for testing how the index
will evolve over time.

The format of the input and output JSON files can be seen from the
examples at the end of the script.  A full package index file to be used
as input can downloaded e.g. from:
https://thunderstore.io/c/lethal-company/api/v1/package/
"""
import contextlib
import hashlib
import json
import os.path
import subprocess
from pathlib import Path

CHUNK_SIZE = 1000
SHARD_COUNT = 128  # Should be a power of 2
JSON_PRETTINESS = 0
COMPRESS_JSONS = True

CHUNK_IDX_FORMAT = "{:05d}"
CHUNK_FILENAME = "chunk-{}.json"
SHARD_FILENAME = "shard-{:02x}-{}.json"

SQUASH_COMMITS = False


# Note: There is example input/output data in the bottom of the file

PACKAGE_FIELDS_TO_DROP = {"rating_score", "versions", "date_updated"}
VERSION_FIELDS_TO_DROP = {"downloads", "is_active"}
VERSION_FIELD_MAPPINGS = {
    # "owner": "o",
    # "name": "n",
    # "version_number": "v",
    "full_name": "p",
    "file_size": "s",
    "dependencies": "d",
    "date_created": None,
    "uuid4": None,
}


def convert_package_index_file_to_dir_with_git(
    package_index_file,
    output_dir=None,
    limit_to_date=None,
):
    """
    Convert old package index JSON file to the new package index format.

    The input file should be a JSON file from ThunderStore API and the
    output is created as a new directory containing the new index files.
    """
    if output_dir is None:
        output_dir = Path(package_index_file).stem

    convert_package_index_file_to_dir(
        package_index_file,
        output_dir=output_dir,
        limit_to_date=limit_to_date,
    )

    with current_dir_as(output_dir):
        if not os.path.exists(".git"):
            subprocess.check_call("git init".split())
        git_configs = {
            # Set user info for the repository
            "user.email": "system@example.com",
            "user.name": "System",
            # After receiving a push, update server info and keep
            # maximum number of loose objects instead of packing them
            "receive.updateServerInfo": "true",
            "transfer.unpackLimit": "2147483647",
        }
        if COMPRESS_JSONS:
            # Don't compress loose objects, since the input files are
            # already compressed
            git_configs["core.looseCompression"] = "0"
        else:
            # Compress loose objects to save space
            git_configs["core.looseCompression"] = "9"

        for key, value in git_configs.items():
            subprocess.check_call(["git", "config", key, value])

        # Setup Git attributes to handle zstd files
        with Path(".git/info/attributes").open("wt") as fp:
            fp.write("*.zst diff=zstd\n")

        subprocess.check_call("git add --all".split())

        # Set limit_to_date as the GIT_AUTHOR_DATE and GIT_COMMITTER_DATE
        env = {"TZ": "UTC"}
        if limit_to_date:
            env["GIT_AUTHOR_DATE"] = limit_to_date
            env["GIT_COMMITTER_DATE"] = limit_to_date

        has_commits = bool(Path(".git/refs/heads").glob("*"))

        commit_flags = ["--quiet", "--allow-empty"]
        if SQUASH_COMMITS and has_commits:
            commit_flags += ["--amend", "--reset-author", "-C", "HEAD"]
        else:
            message = "Update" if has_commits else "Index"
            commit_flags += ["-m", message]

        subprocess.check_call(["git", "commit"] + commit_flags, env=env)


def convert_package_index_file_to_dir(
    package_index_file,
    output_dir,
    limit_to_date=None,
):
    """
    Convert old package index to new package index format.

    - `package_index_file` should be a path to a JSON file containing
      the package index in the old format.

    - `output_dir` should be a path to a directory where the new index
      files will be saved to.  If the directory does not exist, it will
      be created.  Default is the name of the input file without the
      extension.

    - `limit_to_date` is an optional datetime string that can be used to
      limit the output to only include packages and versions that were
      created/updated before the given date.
    """
    with open(package_index_file) as fp:
        package_index = json.load(fp)

    reduced_package_index = limit_old_package_index_to_date(
        package_index, limit_to_date
    )

    make_new_package_index_files(reduced_package_index, output_dir=output_dir)


def limit_old_package_index_to_date(package_index, limit_to_date):
    """
    Filter out packages and versions that are newer than the given date.
    """
    if limit_to_date is None:
        return package_index

    # Convert limit_to_date to ISO formatted string if it is not already
    if not isinstance(limit_to_date, str):
        limit_to_date = limit_to_date.isoformat().replace("+00:00", "Z")

    def process_package(package):
        result = package.copy()
        versions = filter_versions(package["versions"])
        # if package["date_updated"] >= limit_to_date:
        #     if versions:
        #         result["date_updated"] = max(x["date_created"] for x in versions)
        #     else:
        #         result["date_updated"] = package["date_created"]
        result["versions"] = versions
        return result

    def filter_versions(versions):
        return [x for x in versions if x["date_created"] < limit_to_date]

    return [
        process_package(package)
        for package in package_index
        if package["date_created"] < limit_to_date
    ]


def make_new_package_index_files(package_index, output_dir):
    created_files = set()

    def post_process_file(filename):
        if COMPRESS_JSONS:
            if Path(str(filename) + ".zst").exists():
                # Don't recompress immutable files
                if "CURRENT" not in str(filename):
                    created_files.add(str(filename) + ".zst")
                    return

            compressed_filename = compress_file(filename)
            created_files.add(str(compressed_filename))
        else:
            created_files.add(str(filename))

    def delete_extra_files():
        for path in Path(".").rglob("*"):
            if path.is_file() and str(path) not in created_files:
                print(f"Deleting extra file: {path}")
                path.unlink()

    with create_dir_and_use_it_as_cwd(output_dir):
        print("Creating package files...")
        with create_dir_and_use_it_as_cwd("packages"):
            save_package_index_shards(package_index, post_process_file)
            delete_extra_files()

        print("Creating version files...")
        version_index = version_index_from_package_index(package_index)
        with create_dir_and_use_it_as_cwd("versions"):
            save_version_index_chunks(
                version_index,
                per_chunk=CHUNK_SIZE,
                post_process_file=post_process_file,
            )
            delete_extra_files()


def save_package_index_shards(package_index, post_process_file):
    print("Determining storage paths for each owner...")
    storage_path_by_owner = {}
    owners = {x["owner"] for x in package_index}
    for owner in owners:
        h = hashlib.sha1(owner.upper().encode("utf-8")).hexdigest()
        shard = int(h[:4], 16) % SHARD_COUNT
        filename = SHARD_FILENAME.format(shard, "HASH")
        storage_path_by_owner[owner] = Path(filename)

    print("Preparing packages for each storage path...")
    packages_by_storage_path = {}
    for package in package_index:
        package = package.copy()
        for field in PACKAGE_FIELDS_TO_DROP:
            package.pop(field)
        owner = package["owner"]
        path = storage_path_by_owner[owner]
        packages_by_storage_path.setdefault(path, []).append(package)

    print("Saving packages to files...")
    for storage_path in sorted(packages_by_storage_path):
        packages = packages_by_storage_path[storage_path]
        packages.sort(key=lambda x: x["date_created"])
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        with storage_path.open("wt") as fp:
            serialize_list_as_json(packages, fp)

        # Calculate hash of the contents and rename the file
        with storage_path.open("rb") as fp:
            content_hash = hashlib.sha1(fp.read()).hexdigest()[:8]
        new_filename = str(storage_path).replace("HASH", content_hash)
        os.rename(storage_path, new_filename)
        post_process_file(new_filename)


def save_version_index_chunks(
    version_index,
    per_chunk=1000,
    post_process_file=lambda filename: None,
    filename_template=CHUNK_FILENAME,
):
    """
    Save version index to files in chunks.
    """
    for n, chunk in enumerate(make_chunks(version_index, per_chunk)):
        chunk_name = CHUNK_IDX_FORMAT.format(n)
        if len(chunk) < per_chunk:
            chunk_name = "CURRENT"
        filename = filename_template.format(chunk_name)
        with open(filename, "w") as fileobj:
            serialize_list_as_json(chunk, fileobj)
        post_process_file(filename)


def version_index_from_package_index(package_index):
    """
    Convert old package index to version index.

    Note: Version index is sorted by date_created (and uuid4).
    """
    source_items = list(
        make_version_index_source_items_from_package_index(package_index)
    )
    source_items.sort(key=lambda x: (x["date_created"], x["uuid4"]))
    result = []
    for item in source_items:
        result.append(
            {
                new_field: item[old_field]
                for old_field, new_field in VERSION_FIELD_MAPPINGS.items()
                if new_field
            }
        )
    return result


def make_version_index_source_items_from_package_index(package_index):
    """
    Convert old package index items to items of version index.
    """
    for package in package_index:
        for version in package["versions"]:
            new_version = {
                field: version.get(field, package.get(field))
                for field in VERSION_FIELD_MAPPINGS
            }
            yield new_version


########################################################################
# Utility functions
########################################################################

# - Iterator utilities -------------------------------------------------


def make_chunks(data, chunk_size):
    """
    Split data into chunks of given size.

    The input is assumed to be a list or any other container that
    supports splicing and len().  Returns an iterator of chunks, each
    chunk being a slice of the input data.  The last chunk may be
    shorter than chunk_size.
    """
    return (data[i : i + chunk_size] for i in range(0, len(data), chunk_size))


# - Serialization utilities --------------------------------------------


def serialize_list_as_json(items, fileobj, prettiness=JSON_PRETTINESS):
    assert isinstance(items, list)

    indent = {0: None, 1: None, 2: 0, 3: "\t"}[prettiness]
    separators = (",", ":") if prettiness <= 2 else None

    if prettiness <= 0 or prettiness >= 3:
        json.dump(items, fileobj, indent=indent, separators=separators)
    else:
        fileobj.write("[\n")
        for n, item in enumerate(items):
            if n > 0:
                fileobj.write(",")
            json.dump(item, fileobj, indent=indent, separators=separators)
            fileobj.write("\n")
        fileobj.write("]")


# - File system utilities ----------------------------------------------


def compress_file(filename, compressor="zstdmt", level=15):
    """
    Compress file and remove the original file.

    Currently supports only Zstandard compression and does it with the
    zstdmt binary using given level (default: 15).
    """
    assert compressor == "zstdmt"
    outfile = f"{filename}.zst"
    opts = [f"-{level}", "--rm", "-f", "--rsyncable"]
    zstd_cmd = [compressor] + opts + [filename, "-o", outfile]
    subprocess.check_call(zstd_cmd)
    return outfile


@contextlib.contextmanager
def create_dir_and_use_it_as_cwd(path):
    """
    Change cwd to path, execute function, then change back to old cwd.
    """
    print(f"Creating directory {path!r} into {os.getcwd()}")
    os.makedirs(path, exist_ok=True)
    with current_dir_as(path):
        yield


@contextlib.contextmanager
def current_dir_as(path):
    """
    Change cwd to path, execute function, then change back to old cwd.
    """
    old_cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old_cwd)


########################################################################
# Example input/output data
########################################################################

# Input data / Old package index format
EXAMPLE_1_OF_OLD_INDEX = [
    {
        "name": "BepInExPack",
        "full_name": "BepInEx-BepInExPack",
        "owner": "BepInEx",
        "package_url": "https://thunderstore.io/c/lethal-company/p/BepInEx/BepInExPack/",
        "date_created": "2023-01-17T16:24:38.370139Z",
        "date_updated": "2023-01-17T16:24:39.204947Z",
        "uuid4": "b9a5a1bd-81d8-4913-a46e-70ca7734628c",
        "rating_score": 659,
        "is_pinned": True,
        "is_deprecated": False,
        "has_nsfw_content": False,
        "categories": ["BepInEx"],
        "versions": [
            {
                "name": "BepInExPack",
                "full_name": "BepInEx-BepInExPack-5.4.2100",
                "description": "BepInEx pack for Mono Unity games. Preconfigured and ready to use.",
                "icon": "https://gcdn.thunderstore.io/live/repository/icons/BepInEx-BepInExPack-5.4.2100.png",
                "version_number": "5.4.2100",
                "dependencies": [],
                "download_url": "https://thunderstore.io/package/download/BepInEx/BepInExPack/5.4.2100/",
                "downloads": 14811269,
                "date_created": "2023-01-17T16:24:38.784605Z",
                "website_url": "https://github.com/BepInEx/BepInEx",
                "is_active": True,
                "uuid4": "fa43c8b1-94dc-4df1-bd06-9fe607d4c7ff",
                "file_size": 649108,
            }
        ],
    },
]

# Output data / New index format
#
# Has separate lists for package data and version data
EXAMPLE_1_OF_NEW_INDEX_PACKAGES = [
    {
        "name": "BepInExPack",
        "full_name": "BepInEx-BepInExPack",
        "owner": "BepInEx",
        "package_url": "https://thunderstore.io/c/lethal-company/p/BepInEx/BepInExPack/",
        "date_created": "2023-01-17T16:24:38.370139Z",
        # Update date was left out to reduce unnecessary changes
        # "date_updated": "2023-01-17T16:24:39.204947Z",
        "uuid4": "b9a5a1bd-81d8-4913-a46e-70ca7734628c",
        "is_pinned": True,
        "is_deprecated": False,
        "has_nsfw_content": False,
        "categories_by_community": {  # TODO: Not implemented
            "lethal-company": ["BepInEx"],
        },
    },
]
EXAMPLE_1_OF_NEW_INDEX_VERSIONS = [
    {
        "p": "BepInEx-BepInExPack-5.4.2100",
        "s": 649108,
        "d": [],
    }
]
