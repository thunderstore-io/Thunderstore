from django.urls import path

from thunderstore.usermedia.api.experimental.views.upload import (
    UserMediaAbortUploadApiView,
    UserMediaCreatePartUploadUrlsApiView,
    UserMediaFinishUploadApiView,
    UserMediaInitiateUploadApiView,
)

urls = [
    path(
        "usermedia/initiate-upload/",
        UserMediaInitiateUploadApiView.as_view(),
        name="usermedia.initiate-upload",
    ),
    path(
        "usermedia/<uuid:uuid>/create-part-upload-urls/",
        UserMediaCreatePartUploadUrlsApiView.as_view(),
        name="usermedia.create-part-upload-urls",
    ),
    path(
        "usermedia/<uuid:uuid>/finish-upload/",
        UserMediaFinishUploadApiView.as_view(),
        name="usermedia.finish-upload",
    ),
    path(
        "usermedia/<uuid:uuid>/abort-upload/",
        UserMediaAbortUploadApiView.as_view(),
        name="usermedia.abort-upload",
    ),
]
