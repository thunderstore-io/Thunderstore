# Package Index (v3)

This app implements another version of the ThunderStore package index
(in contrast to the v1 API as implemented with `PackageViewSet` in
`repository.api.v1` or the "v2" API as implemented with
`PackageIndexApiView` in `repository.api.experimental`).

Package index has two parts: **package data** and **package version
data**. In this Package Index v3 format that data is stored as a Git
repo so that the Git checkout has the following structure:

- Package data is a list of package entries which is divided to shards
  by taking a hash of the name of the package's namespace. Each shard
  is stored as a separate JSON file. E.g. the data of package
  `CoolTeam-FoobarExtension` would be stored to `packages/shard-4b.json`
  if `4b` is the hash value of the namespace name `CoolTeam`.

- Package version data is organized as immutable append-only list, which
  is chunked to `CHUNK_SIZE` items per chunk. The items are sorted by
  the creation date (`date_created`) of the package version and
  therefore when a new package version is added, it is appended to the
  last incomplete chunk and if the chunk is full, a new chunk is
  created. This effectively means that the full chunks are immutable.
  Each chunk is stored as a separate JSON file to a path like
  `versions/chunk-00123.json` for complete chunks and
  `versions/chunk-CURRENT.json` for the incomplete last chunk.

More details of the exact structure of the package index data can be
found from the PoC implementation in
[`package_index_from_json.py`](./package_index_from_json.py).

**NOTE:** The current state of the implementation is that there is just
a PoC of the package index data generation from the JSON file. The next
step is to create code for exporting the package index data from the
*database* to the filesystem and add supporting tools which would share
the generated package index Git repo as static files and put that behind
the CDN.

## To-Do

- DONE: PoC of package index data from the JSON file

    Use the downloaded `lethal-company-package.json` file as the source
    data and generate a file hierarchy which contains the package data.

    - Implemented in
      [`package_index_from_json.py`](./package_index_from_json.py)

- DONE: Test how package index data can be stored to Git

- DONE: Test sharing the Git repo as static files via nginx

- DONE: Test how package data changes affect the sharing of the Git repo

    Simulate changes over time by reading the input data and filtering it
    by limiting the packages to a certain date range. Then generate the
    package index data for each date range and see how the Git repo size
    changes and how the data is shared between the different versions.

    - Can git fetch do incremental updates?

        - Yes it can if the data is stored to loose objects and no pack
          files are created.

    - Will large number of commits slow down the git fetch?

        - Yes, the fetch is slower if there are many commits. It's
          probably a good idea to squash the commits to a single commit
          either every time or at least periodically.

    - Can the commits be squashed to single commit or will that make the
      incremental updates impossible?

        - Yes, the commits can be squashed to a single commit. The
          incremental updates are still possible, but of course the
          client needs to do a hard reset to the new HEAD.

- DONE: Data scraper to get package data to the DB for testing

    Implement a management command which scrapes the package data from
    ThunderStore public API and stores it to the database.

    - Implemented in [`data_scraper.py`](./data_scraper.py)

- TODO: Implement exporting package index from DB to FS

    Implement a management command which exports the package index data
    from the database to the filesystem.

    This can be based on the `package_index_from_json.py` script.

    Note: The idea is to implement a single index for all communities.
    See the next TODO item for the community separation.

- TODO: Add categories_by_community to the package index data

    Add a new field to the package index data which contains the
    categories by community. This field is a dictionary where the key is
    the community name and the value is a list of categories in that
    community.   The presence of the community name in this field would
    indicate that the package belongs to that community.  The category
    list can be empty, but it still allows the community to be listed as
    a key in the dictionary (with `[]` as value).
